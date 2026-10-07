"""그날 상장돼 있던 모든 종목의 종가 · 시가총액(공공데이터포털 금융위원회 주식시세정보) — 상장폐지 종목까지 담은 '그날의 상위 종목'
(사용자 2026-10-07 "상장폐지 종목까지 넣은 대상으로 다시 재서, 살아남은 종목만 본 치우침을 줄여" · 한투는 상폐 종목 일봉을 안 줌:
probe_delisted 2026-09-24 '시세는 없는데 일봉은 있음 0').

날짜(basDt)로 물으면 그날 상장된 종목이 모두 옴 → 뒤에 상장폐지된 회사도 그날 줄에 있음.
저장: public-daily/{해}.csv — "날,코드,이름,종가,시가총액(억),거래량" · 날마다 시가총액 위 TOP(기본 400)만(대상 200 + 여유).
이어 받기: 이미 있는 날은 건너뜀 · 한 번에 MAX_DAYS일까지(호출 한도). 조회 전용 · 키는 찍지 않음.
python collect_public_daily.py [시작날 YYYYMMDD]
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from pathlib import Path

from market import MARKETS, _number, board

HOME = Path("public-daily")
TOP = int(os.getenv("PUB_TOP", "400"))
MAX_DAYS = int(os.getenv("PUB_MAX_DAYS", "400"))


def have_days():
    got = set()
    for f in HOME.glob("*.csv"):
        for line in f.read_text(encoding="utf-8").splitlines()[1:]:
            got.add(line.split(",", 1)[0])
    return got


def trading_days(since):
    rows = json.loads(Path("price-data/005930.json").read_text(encoding="utf-8"))["closes"]
    return [str(d) for d, _ in rows if str(d) >= since]


def one_day(day, key):
    rows = []
    for market in MARKETS:
        for it in board(market, day, key):
            code = str(it.get("srtnCd") or "").strip()
            cap, close = _number(it.get("mrktTotAmt")), _number(it.get("clpr"))
            if len(code) != 6 or not cap or not close:
                continue
            rows.append((day, code, str(it.get("itmsNm") or "").replace(",", " ").strip(), close, round(cap / 1e8), _number(it.get("trqu")) or 0))
    rows.sort(key=lambda r: -r[4])
    return rows[:TOP]


def save(rows):
    by_year = {}
    for r in rows:
        by_year.setdefault(r[0][:4], []).append(r)
    HOME.mkdir(exist_ok=True)
    for y, new in by_year.items():
        f = HOME / f"{y}.csv"
        old = f.read_text(encoding="utf-8").splitlines()[1:] if f.exists() else []
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["날", "코드", "이름", "종가", "시가총액(억)", "거래량"])
        lines = sorted(set(old) | {",".join(str(x) for x in (r[0], r[1], r[2], int(r[3]) if float(r[3]).is_integer() else r[3], r[4], int(r[5]))) for r in new})
        buf.write("\n".join(lines) + "\n")
        f.write_text(buf.getvalue(), encoding="utf-8")


def main(since="20170102"):
    if not (len(since) == 8 and since.isdigit()):
        print("시작날은 YYYYMMDD")
        return 1
    key = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
    if not key:
        print("DATA_GO_KR_SERVICE_KEY가 없습니다.")
        return 1
    have = have_days()
    todo = [d for d in trading_days(since) if d not in have][:MAX_DAYS]
    print(f"받을 날 {len(todo)}일(이미 {len(have)}일)")
    got, empty, fail = [], [], 0
    for i, day in enumerate(todo, 1):
        try:
            rows = one_day(day, key)
        except Exception as e:                       # 응답 본문 · 키는 찍지 않음
            fail += 1
            print(f"{day} 실패 · {type(e).__name__}")
            if fail >= 5:
                break
            continue
        (got.extend(rows) if rows else empty.append(day))
        if i % 50 == 0:
            save(got)
            got = []
            print(f"  {i}/{len(todo)} · 빈 날 {len(empty)}", flush=True)
    save(got)
    print(f"끝 · 받은 날 {len(todo) - len(empty) - fail} · 빈 날 {len(empty)}(예 {empty[:5]}) · 실패 {fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2])))
