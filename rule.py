"""지금 쓰는 규칙 하나와, 오늘 그 규칙에 걸리는 종목.

조사에서 나온 것 가운데 가장 단단했던 조합을 여기 한 군데에 적어 둡니다.
조건을 늘릴수록 좋아질 것 같지만 그렇지 않았습니다. 매출과 영업이익률을
더 얹으면 표본만 줄고 성적은 그대로이거나 나빠졌습니다. 그래서 둘만 둡니다.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import lab

NAME = "급락 뒤 이익 늘어난 종목"
DROP = -30.0        # 60거래일 전보다 이만큼 아래
PROFIT = 50.0       # 직전 공시의 영업이익 성장률이 이만큼 위
TAKE, STOP = 10.0, 7.0   # 익절·손절
LIMIT = 60          # 이 거래일이 지나면 그냥 정리
OUT = Path("study") / "rule.json"

WHY = (
    "예순 거래일 전보다 30% 아래로 빠진 날 가운데, 그날까지 공시된 영업이익이 "
    "전년 같은 기간보다 50% 넘게 늘어난 종목입니다. 크게 빠졌지만 벌이는 늘고 "
    "있는 자리입니다. 조건을 더 얹으면 표본만 줄고 나아지지 않았습니다."
)
CAVEAT = (
    "지나간 자료로 확인한 것이며 앞날을 약속하지 않습니다. 열 번 중 너덧 번은 "
    "집니다. 한 종목에 몰지 말고 손절을 반드시 함께 두십시오. 매수·매도 "
    "신호가 아닙니다."
)


def holds(row):
    return ((row.get("60일 전 대비") or 99) <= DROP
            and (row.get("영업이익성장") or -99) >= PROFIT)


def today(rows):
    """종목마다 가장 마지막 날을 보고, 오늘 걸리는지 봅니다."""
    latest = {}
    for row in rows:
        code = row["code"]
        if code not in latest or row["date"] > latest[code]["date"]:
            latest[code] = row
    found = []
    for code, row in latest.items():
        found.append({"code": code, "name": row.get("name") or code,
                      "date": row["date"], "해당": holds(row),
                      "60일 전 대비": row.get("60일 전 대비"),
                      "영업이익성장": row.get("영업이익성장"),
                      "매출성장": row.get("매출성장"),
                      "목표가괴리": row.get("목표가괴리")})
    found.sort(key=lambda r: (not r["해당"], r.get("60일 전 대비") or 0))
    return found


def report(rows, prices):
    picked = [r for r in rows if holds(r)]
    body = {
        "name": NAME, "why": WHY, "caveat": CAVEAT,
        "drop": DROP, "profit": PROFIT, "take": TAKE, "stop": STOP, "limit": LIMIT,
        "made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M"),
        "기준": lab.score(rows), "규칙": lab.score(picked),
        "매매": lab.trade(picked, prices, TAKE, STOP, limit=LIMIT),
        "오늘": today(rows),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    return body
