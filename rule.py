"""지금 쓰는 규칙 하나와, 오늘 그 규칙에 걸리는 종목.

조사에서 나온 것 가운데 가장 단단했던 조합을 여기 한 군데에 적어 둡니다.

한때 실적 조건을 넣었다가 뺐습니다. 실적이 붙은 관측은 2017년 이후뿐인데,
그 구간이 원래 좋은 구간이었습니다. 같은 구간 안에서 견주니 영업이익 조건은
중앙값을 오히려 0.42%p 깎았습니다. 좋아 보였던 것은 실적의 힘이 아니라
시기의 힘이었습니다.

지금 쓰는 것은 이십일 이동평균선에서 얼마나 아래로 벌어졌는지 하나입니다.
1997·2000·2008·2020·2026 다섯 번의 위기에서 모두 나타났습니다.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import lab

NAME = "중기선에서 이례적으로 벌어진 종목"
GAP = -15.0         # 20일(중기) 이동평균선보다 이만큼 아래
BAND = -2.0         # 그 종목의 지난 이격과 견줘 이만큼 밖으로
TAKE, STOP = 10.0, 7.0   # 익절·손절
LIMIT = 60          # 이 거래일이 지나면 그냥 정리
OUT = Path("study") / "rule.json"

WHY = (
    "종가가 중기선(20거래일 이동평균)보다 15% 넘게 아래로 벌어지고, 그 벌어짐이 "
    "그 종목의 지난 120거래일 이격과 견줘도 이례적인 날입니다. 같은 −15%라도 "
    "늘 출렁이는 종목에는 흔한 일이고 조용한 종목에는 큰 일이라, 종목마다 제 "
    "잣대로 잽니다. 그 뒤 스무 거래일 중앙값이 +7.09%였고, 아무 날이나 고른 "
    "경우는 −0.01%입니다. 실적·목표가·정배열·가속도를 더해 보았지만 표본만 "
    "줄거나 특정 폭락에 몰려 쓰지 않았습니다."
)
CAVEAT = (
    "크게 밀린 종목을 사는 규칙이라 더 밀릴 수 있습니다. 가장 나빴던 열에 "
    "하나는 −29.9%였습니다. 손절 없이 쓰면 안 됩니다. 지나간 자료로 확인한 "
    "것이며 앞날을 약속하지 않습니다. 매수·매도 신호가 아닙니다."
)


def holds(row):
    return ((row.get("중기 이격") or 99) <= GAP
            and (row.get("중기 이격밴드") or 99) <= BAND)


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
                      "중기 이격": row.get("중기 이격"),
                      "중기 이격밴드": row.get("중기 이격밴드"),
                      "60일 전 대비": row.get("60일 전 대비"),
                      "영업이익성장": row.get("영업이익성장"),
                      "매출성장": row.get("매출성장"),
                      "목표가괴리": row.get("목표가괴리")})
    found.sort(key=lambda r: (not r["해당"], r.get("중기 이격") or 0))
    return found


def report(rows, prices):
    picked = [r for r in rows if holds(r)]
    body = {
        "name": NAME, "why": WHY, "caveat": CAVEAT,
        "gap": GAP, "band": BAND, "take": TAKE, "stop": STOP, "limit": LIMIT,
        "made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M"),
        "기준": lab.score(rows), "규칙": lab.score(picked),
        "매매": lab.trade(picked, prices, TAKE, STOP, limit=LIMIT),
        "오늘": today(rows),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    return body
