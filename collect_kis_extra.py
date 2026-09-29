"""한국투자증권에서 과거까지 주는 자료를 더 모읍니다(새 RL 재료, 조회 전용).

종목마다(study/flow_universe.json + 그날 A·B그룹):
- program: 종목별 프로그램매매(일별) — 순매수량 · 순매수대금 · 매수량 · 매도량. 날짜를 주면 서른 거래일씩.
- loan:    종목별 대차거래(일별) — 신규 · 상환 · 잔고 주수와 잔고 금액. 기간(90일씩)으로.
- side:    종목별 매수·매도 체결량(일별) — 사는 쪽이 먼저 부른 체결량과 파는 쪽 체결량. 기간(90일씩)으로.
시장 전체(market-data/):
- index_KOSPI · index_KOSDAQ(지수 일별), investor_KSP · investor_KSQ(시장별 투자자 순매수 대금),
  program_K · program_Q(시장 프로그램매매), funds(고객예탁금 · 신용융자잔고 · 미수금 등).
종목마다 재무비율(ratio-data/, 연간 2004~ · 분기 2019~)도 한 번씩.

모두 2017년까지 거슬러 가며, 받은 데서 이어 받고, 끝에 닿으면 '처음까지'로 적고 뒤로는 새 날만 붙입니다.
python collect_kis_extra.py program|loan|side|market|ratio
"""
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis
from collect_investor_history import _patiently, codes_to_collect

START = os.getenv("EXTRA_START", "20170101")
LANES = int(os.getenv("EXTRA_LANES", "4"))
STOP_AFTER = 5
MAX_ASKS = 300
FOLDERS = {"program": Path("program-data"), "loan": Path("loan-data"), "side": Path("side-data"),
           "market": Path("market-data"), "ratio": Path("ratio-data")}


def _day(text):
    return date(int(text[:4]), int(text[4:6]), int(text[6:8]))


def _shift(text, days):
    return (_day(text) + timedelta(days=days)).strftime("%Y%m%d")


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"rows": [], "처음까지": False}


def save(path, body):
    path = Path(path)
    path.parent.mkdir(exist_ok=True)
    rows = sorted(body.get("rows") or [], key=lambda r: r.get("date") or r.get("결산월") or "")
    lines = ",\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    head = {k: v for k, v in body.items() if k != "rows"}
    path.write_text(json.dumps(head, ensure_ascii=False)[:-1] + ', "rows": [\n' + lines + "\n]}\n", encoding="utf-8")


def by_cursor(fetch, have, today, start=START, asks=MAX_ASKS):
    """fetch(day) → day까지 몇 줄(오래된 것 먼저). 앞쪽(새 날)과 뒤쪽(옛날)을 채웁니다. (새 줄 수, 물은 수, 처음까지)."""
    added = n = 0
    if have:
        cursor, newest = today, max(have)
        while cursor > newest and n < asks:
            got = fetch(cursor); n += 1
            fresh = [g for g in got if g["date"] not in have]
            for g in fresh:
                have[g["date"]] = g
            added += len(fresh)
            if not got or got[0]["date"] <= newest or not fresh:
                break
            cursor = _shift(got[0]["date"], -1)
    cursor = _shift(min(have), -1) if have else today
    done = False
    while cursor >= start and n < asks:
        got = fetch(cursor); n += 1
        fresh = [g for g in got if g["date"] not in have]
        for g in fresh:
            have[g["date"]] = g
        added += len(fresh)
        if not fresh:
            done = True
            break
        cursor = _shift(min(g["date"] for g in got), -1)
    return added, n, done or cursor < start


def by_window(fetch, have, today, start=START, width=90, asks=MAX_ASKS):
    """fetch(a, b) → 그 사이 줄들. 앞쪽은 마지막 날 뒤부터 오늘까지, 뒤쪽은 width일씩 거슬러. 두 번 잇달아 비면 멈춤."""
    added = n = 0
    if have:
        newest = max(have)
        if newest < today:
            got = fetch(_shift(newest, 1), today); n += 1
            for g in got:
                if g["date"] not in have:
                    have[g["date"]] = g; added += 1
    end = _shift(min(have), -1) if have else today
    empty = 0
    done = False
    while end >= start and n < asks:
        a = max(_shift(end, -(width - 1)), start)
        got = fetch(a, end); n += 1
        fresh = [g for g in got if g["date"] not in have]
        for g in fresh:
            have[g["date"]] = g
        added += len(fresh)
        empty = 0 if fresh else empty + 1
        if empty >= 2:
            done = True
            break
        end = _shift(a, -1)
    return added, n, done or end < start


def fill_stock(kind, client, code, today):
    path = FOLDERS[kind] / f"{code}.json"
    body = load(path)
    if body.get("처음까지") and body.get("rows") and max(r["date"] for r in body["rows"]) >= today:
        return 0, 0
    have = {r["date"]: r for r in body.get("rows") or []}
    if kind == "program":
        added, n, done = by_cursor(lambda d: client.program_daily(code, d), have, today)
    elif kind == "loan":
        added, n, done = by_window(lambda a, b: client.loan_daily(code, a, b), have, today)
    else:
        added, n, done = by_window(lambda a, b: client.trade_side_daily(code, a, b), have, today)
    body.update({"code": code, "rows": [have[d] for d in sorted(have) if d >= START],
                 "처음까지": bool(body.get("처음까지") or done)})
    save(path, body)
    return added, n


def fill_ratio(client, code, today):
    path = FOLDERS["ratio"] / f"{code}.json"
    body = {"code": code, "fetched": today,
            "연간": client.financial_ratio(code), "분기": client.financial_ratio(code, quarterly=True)}
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return len(body["연간"]) + len(body["분기"]), 2


def fill_market(client, today):
    jobs = {
        "index_KOSPI": lambda h: by_window(lambda a, b: client.index_daily("0001", a, b), h, today, width=60),
        "index_KOSDAQ": lambda h: by_window(lambda a, b: client.index_daily("1001", a, b), h, today, width=60),
        "investor_KSP": lambda h: by_cursor(lambda d: client.market_investor_daily("KSP", d), h, today),
        "investor_KSQ": lambda h: by_cursor(lambda d: client.market_investor_daily("KSQ", d), h, today),
        "program_K": lambda h: by_window(lambda a, b: client.market_program_daily("K", a, b), h, today),
        "program_Q": lambda h: by_window(lambda a, b: client.market_program_daily("Q", a, b), h, today),
        "funds": lambda h: by_cursor(lambda d: client.market_funds(d), h, today),
    }
    for name, job in jobs.items():
        path = FOLDERS["market"] / f"{name}.json"
        body = load(path)
        have = {r["date"]: r for r in body.get("rows") or []}
        try:
            added, n, done = _patiently(lambda: job(have))
        except broker_kis.BrokerError as error:
            print(f"{name} · 실패 · {str(error)[:80]}", flush=True)
            continue
        body.update({"name": name, "rows": [have[d] for d in sorted(have) if d >= START],
                     "처음까지": bool(body.get("처음까지") or done)})
        save(path, body)
        rows = body["rows"]
        print(f"{name} · 새 줄 {added} · 물음 {n} · {rows[0]['date'] if rows else '-'}~{rows[-1]['date'] if rows else '-'}", flush=True)


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    if kind not in FOLDERS:
        print("program · loan · side · market · ratio 가운데 하나를 주세요.")
        return 1
    try:
        client = broker_kis.market()
    except broker_kis.BrokerError as error:
        print("증권사 연결을 만들지 못했습니다 ·", error)
        return 1
    today = (datetime.now(ZoneInfo("Asia/Seoul")).date() - timedelta(days=1)).strftime("%Y%m%d")
    if kind == "market":
        fill_market(client, today)
        return 0
    codes = codes_to_collect()
    lock = threading.Lock()
    state = {"done": 0, "failed": 0, "in_a_row": 0, "stop": False}

    def one(code):
        if state["stop"]:
            return
        try:
            if kind == "ratio":
                added, n = _patiently(lambda: fill_ratio(client, code, today))
            else:
                added, n = _patiently(lambda: fill_stock(kind, client, code, today))
            with lock:
                state["done"] += 1
                state["in_a_row"] = 0
                print(f"{code} · 새 줄 {added} · 물음 {n}", flush=True)
        except broker_kis.BrokerError as error:
            with lock:
                state["failed"] += 1
                state["in_a_row"] += 1
                print(f"{code} · 실패 · {str(error)[:80]}", flush=True)
                if state["in_a_row"] >= STOP_AFTER:
                    state["stop"] = True

    with ThreadPoolExecutor(max_workers=LANES) as pool:
        for job in as_completed([pool.submit(one, c) for c in codes]):
            job.result()
    print(f"끝 · {kind} · 받은 종목 {state['done']} · 실패 {state['failed']}")
    return 2 if state["stop"] else 0


if __name__ == "__main__":
    sys.exit(main())
