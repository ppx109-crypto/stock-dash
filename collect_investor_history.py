"""누가 샀고 누가 팔았는지(개인·외국인·기관·투신·연기금·사모)를 과거까지 거슬러 모읍니다.

스승님 조건(외국인과 투신이 사고 개인이 판다)을 2017년부터 검증하려고 모읍니다. 증권사
'종목별 투자자매매동향(일별)'은 날짜를 주면 그날까지 서른 거래일을 주므로, 가장 옛날 날의
하루 앞을 다시 물어 가며 거슬러 올라갑니다. 대상은 study/flow_universe.json(2017년 이후
시가총액 120위 안에 든 적이 있는 종목)입니다.

한 종목을 다 받으면 그 자리에서 저장합니다. 도중에 멈춰도 다시 돌리면 받은 데서 이어 갑니다.
끝에 닿은 종목(2017년에 닿았거나 상장일에 닿음)은 '처음까지'로 적어 다시 묻지 않고, 그 뒤로는
새로 생긴 날만 앞쪽에 붙입니다. 조회 전용이며 주문과 무관합니다.
"""
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis

# INVESTOR_SET=full: 증권사가 주는 모든 투자자 칸(금융투자 · 은행 · 보험 · 기타법인 · 외국인 등록/비등록 …)을
# 가장 옛날까지 investor-full/에 따로 모읍니다(수급 갈래 연구 · 사용자 2026-10-02). 기본은 지금 그대로입니다.
FULL = os.getenv("INVESTOR_SET", "").strip() == "full"
OUT = Path("investor-full" if FULL else "investor-data")
UNIVERSE = Path("study") / "flow_universe.json"
START = os.getenv("INVESTOR_START", "20060101" if FULL else "20170101")   # 찔러보기(2026-10-02): 2008-06은 값 있음 · 2005-06 앞은 칸만 있고 빔
COLS = (("date",) + tuple(n for n, _ in broker_kis.KIS.INVESTORS_ALL) + ("종가",) if FULL
        else ("date", "개인", "외국인", "기관", "투신", "연기금", "사모", "종가"))
MAX_ASKS = 400 if FULL else 200   # 한 종목에 물을 수 있는 가장 많은 횟수(서른 거래일씩). 막힌 응답이 끝없이 돌지 않게.


def codes_to_collect():
    picked = [c.strip() for c in os.getenv("INVESTOR_CODES", "").split(",") if c.strip()]
    if not picked:
        try:
            picked = json.loads(UNIVERSE.read_text(encoding="utf-8")).get("codes", [])
        except (OSError, ValueError):
            picked = []
        # 오늘 A·B그룹에 새로 들어온 종목도 받습니다(목록 밖에서 새로 커진 종목).
        try:
            found = json.loads(Path("study/a_group.json").read_text(encoding="utf-8"))
            picked = list(dict.fromkeys(list(picked) + [one["code"] for one in
                                                       found.get("picks", []) + found.get("b_group", [])]))
        except (OSError, ValueError, KeyError, TypeError):
            pass
    return [str(c) for c in picked if re.fullmatch(r"[0-9]{6}", str(c))]


def load(code):
    try:
        body = json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"code": code, "cols": list(COLS), "rows": [], "처음까지": False}
    return body


def save(body):
    OUT.mkdir(exist_ok=True)
    body["rows"].sort(key=lambda r: r[0])
    # 줄마다 한 줄씩 적어, 날이 늘 때 바뀐 곳만 커밋에 남게 합니다.
    lines = ",\n".join(json.dumps(r, ensure_ascii=False) for r in body["rows"])
    head = {k: v for k, v in body.items() if k != "rows"}
    text = json.dumps(head, ensure_ascii=False)[:-1] + ', "rows": [\n' + lines + "\n]}\n"
    (OUT / f"{body['code']}.json").write_text(text, encoding="utf-8")


def as_row(got):
    return [got["date"]] + [got.get(name) for name in COLS[1:]]


def _ask(client, code, day):
    return client.investor_daily(code, day, full=True) if FULL else client.investor_daily(code, day)


def _before(day):
    d = date(int(day[:4]), int(day[4:6]), int(day[6:8])) - timedelta(days=1)
    return d.strftime("%Y%m%d")


def fill(client, code, today):
    """한 종목을 채웁니다. (새로 붙인 줄 수, 물은 횟수)."""
    body = load(code)
    have = {r[0]: r for r in body["rows"]}
    added = asks = 0
    # 1) 앞쪽: 마지막으로 받은 날 뒤에 생긴 날을 붙입니다.
    if have:
        cursor = today
        newest = max(have)
        while cursor > newest and asks < MAX_ASKS:
            got = _ask(client, code, cursor)
            asks += 1
            fresh = [g for g in got if g["date"] not in have]
            for g in fresh:
                have[g["date"]] = as_row(g)
            added += len(fresh)
            if not got or got[0]["date"] <= newest or not fresh:
                break
            cursor = _before(got[0]["date"])
    # 2) 뒤쪽: 아직 처음까지 닿지 않았으면 가장 옛날 날의 하루 앞을 물어 거슬러 갑니다.
    cursor = _before(min(have)) if have else today
    while not body.get("처음까지") and cursor >= START and asks < MAX_ASKS:
        got = _ask(client, code, cursor)
        asks += 1
        fresh = [g for g in got if g["date"] not in have]
        for g in fresh:
            have[g["date"]] = as_row(g)
        added += len(fresh)
        if not fresh:                      # 상장일보다 앞이거나 더 줄 것이 없음
            body["처음까지"] = True
            break
        cursor = _before(got[0]["date"])
    if cursor < START:
        body["처음까지"] = True
    body["rows"] = [have[d] for d in sorted(have) if d >= START]
    body["cols"] = list(COLS)
    save(body)
    return added, asks


LANES = int(os.getenv("INVESTOR_LANES", "4"))
STOP_AFTER = 5         # 잇달아 이만큼 실패하면 멈춥니다.
TOKEN_WAIT = 65         # 접근토큰은 1분에 한 번만 발급됩니다(EGW00133).


def _patiently(job, tries=5, sleep=time.sleep):
    """토큰 발급 제한에 걸리면 1분 남짓 쉬고 다시 합니다. 다른 거절은 그대로 올립니다."""
    for turn in range(tries):
        try:
            return job()
        except broker_kis.BrokerError as error:
            if broker_kis.KIS.REFUSALS["EGW00133"] not in str(error) or turn == tries - 1:
                raise
            print(f"  토큰 발급 제한 · {TOKEN_WAIT}초 쉬고 다시", flush=True)
            sleep(TOKEN_WAIT)


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
    # 오늘 날짜로 물으면 장중에는 거절됩니다(확인할 때 지난날로 물은 것은 됐습니다). 어제까지만 묻습니다.
    today = _before(datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d"))
    # 한 번 묻는 데 1초 남짓 걸려(대부분 기다림) 한 줄로는 274종목에 아홉 시간이 넘습니다. 네 갈래로
    # 겹쳐 묻습니다. 호출 사이 간격은 broker_kis가 프로세스 전체로 지키므로 초당 호출 수는 늘지 않습니다.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    lock = threading.Lock()
    state = {"done": 0, "failed": 0, "in_a_row": 0, "stop": False}

    def one(code):
        if state["stop"]:
            return
        try:
            added, asks = _patiently(lambda: fill(client, code, today))
            body = load(code)
            rows = body["rows"]
            with lock:
                state["done"] += 1
                state["in_a_row"] = 0
                print(f"{code} · 새 줄 {added} · 물음 {asks} · "
                      f"{rows[0][0] if rows else '-'}~{rows[-1][0] if rows else '-'} · "
                      f"{'처음까지' if body.get('처음까지') else '이어 받을 것 있음'}", flush=True)
        except broker_kis.BrokerError as error:
            with lock:
                state["failed"] += 1
                state["in_a_row"] += 1
                print(f"{code} · 실패 · {str(error)[:80]}", flush=True)
                if state["in_a_row"] >= STOP_AFTER:
                    # 같은 거절이 이어지면 더 물어도 소용없고 증권사에 짐만 됩니다.
                    state["stop"] = True

    with ThreadPoolExecutor(max_workers=LANES) as pool:
        for job in as_completed([pool.submit(one, code) for code in codes]):
            job.result()
    done, failed = state["done"], state["failed"]
    if state["stop"]:
        print(f"잇달아 {STOP_AFTER}번 실패해 멈춥니다.", flush=True)
        print(f"끝 · 받은 종목 {done} · 실패 {failed}")
        return 2
    print(f"끝 · 받은 종목 {done} · 실패 {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
