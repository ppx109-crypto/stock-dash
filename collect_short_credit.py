"""공매도와 신용잔고를 과거까지 거슬러 모읍니다(새 RL 재료).

- 공매도 일별추이: 기간을 주면 그 사이 날마다 공매도 수량 · 거래량 대비 비중(%) · 거래량을 줍니다.
  120일씩 거슬러 물어 2017년까지 갑니다. 공매도 금지 기간(2020-03~2021-05, 2023-11~2025-03)에도
  시장조성 물량이 조금 잡혀 있으니 분석에서 나눠 봅니다.
- 신용잔고 일별추이: 결제일을 주면 그날까지 서른 거래일(매매일 기준)을 줍니다. 가장 옛날 날의 하루
  앞을 다시 물어 거슬러 갑니다.

대상은 수급과 같은 study/flow_universe.json(+ 그날 A·B그룹). 종목마다 저장하고, 다시 돌리면 이어 받으며,
끝에 닿은 종목은 새 날만 붙입니다. 네 갈래로 겹쳐 묻고 호출 간격은 broker_kis가 지킵니다. 조회 전용입니다.
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
from collect_investor_history import _before, _patiently, codes_to_collect

START = os.getenv("SHORT_START", "20170101")
LANES = int(os.getenv("SHORT_LANES", "4"))
STOP_AFTER = 5
MAX_ASKS = 200
KINDS = {
    "short": (Path("short-data"), ("date", "공매도량", "공매도비중", "거래량", "종가")),
    "credit": (Path("credit-data"), ("date", "잔고율", "잔고주수", "공여율", "신규주수", "상환주수")),
}


def _load(kind, code):
    folder, cols = KINDS[kind]
    try:
        return json.loads((folder / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"code": code, "cols": list(cols), "rows": [], "처음까지": False}


def _save(kind, body):
    folder, cols = KINDS[kind]
    folder.mkdir(exist_ok=True)
    body["cols"] = list(cols)
    body["rows"].sort(key=lambda r: r[0])
    lines = ",\n".join(json.dumps(r, ensure_ascii=False) for r in body["rows"])
    head = {k: v for k, v in body.items() if k != "rows"}
    (folder / f"{body['code']}.json").write_text(
        json.dumps(head, ensure_ascii=False)[:-1] + ', "rows": [\n' + lines + "\n]}\n", encoding="utf-8")


def _row(kind, got):
    return [got["date"]] + [got.get(name) for name in KINDS[kind][1][1:]]


def _days_back(day, n):
    d = date(int(day[:4]), int(day[4:6]), int(day[6:8])) - timedelta(days=n)
    return d.strftime("%Y%m%d")


def fill_short(client, code, today):
    body = _load("short", code)
    have = {r[0]: r for r in body["rows"]}
    asks = added = 0
    # 앞쪽: 마지막 날 다음부터 오늘까지
    if have:
        newest = max(have)
        if newest < today:
            got = client.short_daily(code, _days_back(newest, -1), today)
            asks += 1
            for g in got:
                if g["date"] not in have:
                    have[g["date"]] = _row("short", g)
                    added += 1
    # 뒤쪽: 120일씩 거슬러
    end = _before(min(have)) if have else today
    empty = 0
    while not body.get("처음까지") and end >= START and asks < MAX_ASKS:
        start = max(_days_back(end, 119), START)
        got = client.short_daily(code, start, end)
        asks += 1
        fresh = [g for g in got if g["date"] not in have]
        for g in fresh:
            have[g["date"]] = _row("short", g)
        added += len(fresh)
        if not fresh:
            empty += 1
            if empty >= 2:                     # 두 번 잇달아 비면 상장 앞으로 봅니다
                body["처음까지"] = True
                break
        else:
            empty = 0
        end = _before(start)
    if end < START:
        body["처음까지"] = True
    body["rows"] = [have[d] for d in sorted(have) if d >= START]
    _save("short", body)
    return added, asks


def fill_credit(client, code, today):
    body = _load("credit", code)
    have = {r[0]: r for r in body["rows"]}
    asks = added = 0
    if have:
        cursor, newest = today, max(have)
        while cursor > newest and asks < MAX_ASKS:
            got = client.credit_daily(code, cursor)
            asks += 1
            fresh = [g for g in got if g["date"] not in have]
            for g in fresh:
                have[g["date"]] = _row("credit", g)
            added += len(fresh)
            if not got or got[0]["date"] <= newest or not fresh:
                break
            cursor = _before(got[0]["date"])
    cursor = _before(min(have)) if have else today
    while not body.get("처음까지") and cursor >= START and asks < MAX_ASKS:
        got = client.credit_daily(code, cursor)
        asks += 1
        fresh = [g for g in got if g["date"] not in have]
        for g in fresh:
            have[g["date"]] = _row("credit", g)
        added += len(fresh)
        if not fresh:
            body["처음까지"] = True
            break
        cursor = _before(got[0]["date"])
    if cursor < START:
        body["처음까지"] = True
    body["rows"] = [have[d] for d in sorted(have) if d >= START]
    _save("credit", body)
    return added, asks


def main():
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다.")
        return 1
    try:
        client = broker_kis.market()
    except broker_kis.BrokerError as error:
        print("증권사 연결을 만들지 못했습니다 ·", error)
        return 1
    today = _before(datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d"))
    lock = threading.Lock()
    state = {"done": 0, "failed": 0, "in_a_row": 0, "stop": False}

    def one(code):
        if state["stop"]:
            return
        try:
            a1, q1 = _patiently(lambda: fill_short(client, code, today))
            a2, q2 = _patiently(lambda: fill_credit(client, code, today))
            with lock:
                state["done"] += 1
                state["in_a_row"] = 0
                print(f"{code} · 공매도 새 줄 {a1} (물음 {q1}) · 신용 새 줄 {a2} (물음 {q2})", flush=True)
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
    print(f"끝 · 받은 종목 {state['done']} · 실패 {state['failed']}")
    return 2 if state["stop"] else 0


if __name__ == "__main__":
    sys.exit(main())
