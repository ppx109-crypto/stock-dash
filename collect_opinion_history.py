"""증권사 목표가(투자의견)를 2017년까지 거슬러 모읍니다(새 RL 재료).

증권사 종목투자의견 API는 기간을 주면 그 사이 의견을 주지만, 한 번에 100줄까지만 줍니다. 그래서 한 해씩 묻고,
100줄에 닿은 기간은 반으로 나눠 다시 묻습니다(하루짜리가 될 때까지). 받은 것은 collect_opinions.merge로 opinion-data의
지금 파일과 합치므로, 매일 모으는 최근 한 해치와 같은 파일에 쌓입니다. 끝까지 받은 종목은 '과거까지'에 시작일을 적어
다시 묻지 않습니다. 대상은 수급과 같은 study/flow_universe.json. 조회 전용이며 주문과 무관합니다.
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
from collect_opinions import merge

OUT = Path("opinion-data")
START = os.getenv("OPINION_START", "20170101")
LANES = int(os.getenv("OPINION_LANES", "4"))
STOP_AFTER = 5
MAX_ASKS = 400


def _day(text):
    return date(int(text[:4]), int(text[4:6]), int(text[6:8]))


def spans(start, end):
    """start~end를 한 해씩 자른 기간들(오래된 것부터)."""
    found, a = [], _day(start)
    last = _day(end)
    while a <= last:
        b = min(date(a.year, 12, 31), last)
        found.append((a.strftime("%Y%m%d"), b.strftime("%Y%m%d")))
        a = b + timedelta(days=1)
    return found


def gather(ask, start, end, page=broker_kis.KIS.OPINION_PAGE, budget=None):
    """start~end를 다 받을 때까지 묻습니다. 100줄에 닿으면 반으로 쪼갭니다. (줄들, 물은 횟수)."""
    budget = budget if budget is not None else [MAX_ASKS]
    rows, asks = [], 0
    todo = [(start, end)]
    while todo:
        if budget[0] <= 0:
            raise broker_kis.BrokerError("한 종목에 물을 수 있는 횟수를 넘었습니다.")
        a, b = todo.pop()
        got, raw = ask(a, b)
        asks += 1
        budget[0] -= 1
        if raw >= page and a < b:
            mid = _day(a) + (_day(b) - _day(a)) // 2
            todo.append((a, mid.strftime("%Y%m%d")))
            todo.append(((mid + timedelta(days=1)).strftime("%Y%m%d"), b))
            continue
        rows.extend(got)
    return rows, asks


def fill(client, code, today):
    path = OUT / f"{code}.json"
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        body = {"code": code, "rows": []}
    if body.get("과거까지") and body["과거까지"] <= START:
        return 0, 0
    budget = [MAX_ASKS]
    fresh, asks = [], 0
    for a, b in spans(START, today):
        got, n = gather(lambda x, y: client.opinions_between(code, x, y), a, b, budget=budget)
        fresh += got
        asks += n
    before = len(body.get("rows") or [])
    body["rows"] = merge(body.get("rows"), fresh)
    body["code"] = code
    body["과거까지"] = START
    body["fetched"] = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    OUT.mkdir(exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return len(body["rows"]) - before, asks


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
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
    lock = threading.Lock()
    state = {"done": 0, "failed": 0, "in_a_row": 0, "stop": False}

    def one(code):
        if state["stop"]:
            return
        try:
            added, asks = _patiently(lambda: fill(client, code, today))
            with lock:
                state["done"] += 1
                state["in_a_row"] = 0
                print(f"{code} · 새 줄 {added} · 물음 {asks}", flush=True)
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
