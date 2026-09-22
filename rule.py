"""지금 쓰는 규칙과, 오늘 그 규칙에 걸리는 종목.

한 가지 문턱만 두면 강한 신호가 없는 날에는 자금이 놉니다. 가동률이 56%면
절반이 쉬는 것이고, 그만큼 한 해 수익이 깎입니다. 그래서 강도를 층으로 두고
센 것부터 자리를 채웁니다. 센 후보가 없는 날은 그다음 층으로 채웁니다.

실제로 할 수 없는 매매는 세지 않습니다. 상한가에 붙은 날은 사려는 사람만
있어 종가에 살 수 없고, 하한가에 붙은 날은 팔 수 없습니다. 그런 날은 사는
쪽을 건너뛰고 파는 쪽을 미룹니다. 서른 해 일봉의 0.26%가 상한가, 0.09%가
하한가에 붙은 날입니다.

같이 물릴 것을 함께 담지 않습니다. 이미 든 종목과 지난 예순 날 동안 0.6
넘게 같이 움직인 종목은 그날 담지 않습니다. 21회차에 재어 보니 연패가
열다섯에서 열셋으로 줄고, 2020년·2011년·2000년의 골이 서너 %p씩 얕아졌으며,
연수익은 그대로였습니다. 문턱은 0.5부터 0.7까지 모두 같은 방향이라 가운데인
0.6을 씁니다. 다만 2008년은 꿈쩍도 하지 않았습니다. 그때는 **닮지 않은
종목이 없었습니다.**

자리가 셋이어도 하루에 담는 것은 둘까지입니다. 셋을 한날에 몰아 담으면
그날 시장이 밀린 날일 때 셋이 함께 물립니다. 20회차에 재어 보니 그것만
막아도 가장 깊은 골이 −50.8%에서 −47.2%로(전체 구간 −52.1% → −49.9%)
얕아지고, 연수익은 그대로였습니다.

한때 실적 조건을 넣었다가 뺐습니다. 실적이 붙은 관측은 2017년 이후뿐인데
그 구간이 원래 좋은 구간이었습니다. 같은 구간에서 견주니 오히려 깎였습니다.
정배열도 네 번 재어 보았지만 매번 덧셈이 0이었습니다.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import events
import lab

NAME = "중기선에서 이례적으로 벌어진 종목"

# 센 것부터 약한 것 순서입니다. 앞자리가 (이격 %, 이격밴드 σ)입니다.
TIERS = ((-20.0, -2.5), (-15.0, -2.0), (-12.0, -2.0), (-10.0, -2.0))
TAKE, STOP = 15.0, 7.0   # 익절·손절
LIMIT = 15               # 세 주. 이 거래일이 지나면 그냥 정리
SLOTS = 3                # 자리. 자금을 셋으로 나눕니다.
PER_DAY = 2              # 하루에 새로 담는 수. 셋을 한날에 몰아 담지 않습니다.
KIN = 0.6                # 이미 든 것과 이만큼 넘게 같이 움직이면 담지 않습니다.
OUT = Path("study") / "rule.json"

WHY = (
    "종가가 중기선(20거래일 이동평균)에서 아래로 크게 벌어지고, 그 벌어짐이 "
    "그 종목의 지난 120거래일 이격과 견줘도 이례적인 날입니다. 같은 −15%라도 "
    "늘 출렁이는 종목에는 흔한 일이고 조용한 종목에는 큰 일이라, 종목마다 제 "
    "잣대로 잽니다. 벌어진 정도에 따라 네 층으로 나누고, 센 층부터 자리를 "
    "채웁니다. 센 후보가 없는 날은 다음 층으로 채워 자금이 놀지 않게 합니다. "
    "다만 하루에 새로 담는 것은 둘까지이고, 이미 든 종목과 요즘 같이 움직이던 "
    "종목은 담지 않습니다. 셋이 함께 물리는 것을 줄이려는 것입니다."
)
CAVEAT = (
    "크게 밀린 종목을 사는 규칙이라 더 밀릴 수 있습니다. 손절을 7%로 두어도 "
    "하루 사이에 그보다 더 빠지면 그대로 잃습니다. 가장 나빴던 한 번은 "
    "−30.2%였고, 가장 나빴던 열에 하나는 −14.7%였습니다. 열 번 중 다섯 번은 "
    "집니다. "
    "무엇보다, 한 번의 손실보다 이어지는 손실이 큽니다. 자리 셋으로 굴렸다면 "
    "지갑이 가장 깊게 파였을 때 −39.9%였고(2020년 2월 꼭대기 → 3월 바닥), "
    "본전으로 돌아오는 데 그 꼭대기에서 여덟 달이 걸렸습니다. "
    "열세 번을 내리 졌던 적도 있습니다. 해마다 한 번씩은 −8%에서 −40% "
    "사이로 파였습니다. 한 해도 예외가 없었습니다. "
    "더 옛날까지 넣어 세면 2008년에 −44%, 1997년에 −43%가 나옵니다. 그때는 "
    "닮지 않은 종목이 없어, 함께 담지 않는 잣대가 아무 일도 하지 못했습니다. "
    "지나간 자료로 확인한 것이며 앞날을 약속하지 않습니다. "
    "매수·매도 신호가 아닙니다."
)


def tier_of(row):
    """몇 층인지. 센 층일수록 작은 수입니다. 걸리지 않으면 None입니다."""
    gap, band = row.get("중기 이격"), row.get("중기 이격밴드")
    if gap is None or band is None:
        return None
    for rank, (edge, sigma) in enumerate(TIERS):
        if gap <= edge and band <= sigma:
            return rank
    return None


def holds(row):
    return tier_of(row) is not None


def order(row):
    """센 층부터, 같은 층에서는 더 이례적인 것부터 담습니다."""
    return (tier_of(row) if tier_of(row) is not None else 9,
            row.get("중기 이격밴드") or 0)


def today(rows):
    """종목마다 가장 마지막 날을 보고, 오늘 걸리는지 봅니다.

    최근 공시도 함께 붙입니다. 18회차에 재어 보니 공시로 후보를 거르면
    오히려 나빠졌습니다(순서가 이미 뽑고 있고, 거르면 자리가 놉니다).
    그래서 조건으로는 쓰지 않고, 사람이 읽을 것으로만 둡니다. 같은 −20%라도
    유상증자가 사흘 전이었는지 아닌지는 알고 보는 편이 낫습니다.
    """
    latest = {}
    for row in rows:
        code = row["code"]
        if code not in latest or row["date"] > latest[code]["date"]:
            latest[code] = row
    found = []
    for code, row in latest.items():
        rank = tier_of(row)
        found.append({"code": code, "name": row.get("name") or code,
                      "date": row["date"], "해당": rank is not None,
                      "층": (rank + 1) if rank is not None else None,
                      "중기 이격": row.get("중기 이격"),
                      "중기 이격밴드": row.get("중기 이격밴드"),
                      "60일 전 대비": row.get("60일 전 대비"),
                      "영업이익성장": row.get("영업이익성장"),
                      "매출성장": row.get("매출성장"),
                      "목표가괴리": row.get("목표가괴리"),
                      "최근 공시": _filings(code, row["date"])})
    found.sort(key=lambda r: (not r["해당"], r.get("층") or 9,
                              r.get("중기 이격밴드") or 0))
    return found


def tier_stats(rows, since=lab.SPLIT):
    """층마다 재료가 얼마나 다른지. 화면에 그대로 보여 줍니다.

    네 층을 한 덩어리로 보면 '이 규칙은 40% 남짓 맞는다'로 보입니다. 실제로는
    1층이 2주 중앙 +14%이고 4층은 기준선과 거의 같습니다. 4층은 좋아서가
    아니라 자리를 비워 두는 것보다 나아서 담습니다. 그 차이를 감추지 않습니다.
    """
    found = []
    for rank in range(len(TIERS)):
        group = [r for r in rows
                 if r["date"] >= since and tier_of(r) == rank
                 and r.get("ahead", {}).get(lab.HORIZON) is not None]
        if len(group) < 60:        # 60건 미만이면 숫자를 내지 않습니다.
            continue
        gains = sorted(r["ahead"][lab.HORIZON] - lab.COST for r in group)
        cut = max(1, len(gains) // 10)
        found.append({
            "층": rank + 1, "이격": TIERS[rank][0], "밴드": TIERS[rank][1],
            "건수": len(gains), "종목": len({r["code"] for r in group}),
            "날": len({r["date"] for r in group}),
            "5%↑": round(sum(1 for g in gains if g >= lab.RISE) / len(gains) * 100, 1),
            "평균": round(sum(gains) / len(gains), 2),
            "중앙": round(gains[len(gains) // 2], 2),
            "하위10%": round(sum(gains[:cut]) / cut, 1)})
    return found


# 자리를 꽉 채워 굴릴 때와, 한 번에 한 종목만 들 때는 답이 다릅니다.
# 앞은 하루라도 자리를 비우면 손해라 빨리 끊는 편이 낫고, 뒤는 자리 다툼이
# 없으니 벌어진 것이 메워질 때까지 들고 가는 편이 낫습니다. 둘 다 보여 줍니다.
EXITS = {
    "고정 익절·손절 (자리를 꽉 채워 굴릴 때)": lambda: lab.exit_fixed(TAKE, STOP, LIMIT),
    "중기선으로 돌아오면 (한 종목만 들 때)": lambda: lab.exit_back_to_line(40),
}


def apart(prices):
    """같이 물릴 것을 함께 담지 않게 하는 잣대. 그날까지의 수익률만 씁니다."""
    return lab.unlike(lab.moves(prices), edge=KIN)


def exit_stats(rows, prices, since=lab.SPLIT):
    """실제로 사는 신호만 놓고 두 청산을 나란히 견줍니다.

    걸린 것 전부가 아니라 '자리가 있어 실제로 산 것'으로 재야 합니다.
    모집단이 다르면 답도 다릅니다.
    """
    out = lab.run(rows, prices, holds, lab.exit_fixed(TAKE, STOP, LIMIT),
                  slots=SLOTS, rank=order, since=since, detail=True,
                  per_day=PER_DAY, apart=apart(prices), realistic=True)
    if not out:
        return {}
    bought = [got["행"] for got in out["매매목록"]]
    return lab.paired(bought, prices,
                      {tag: make() for tag, make in EXITS.items()})


def _filings(code, day):
    """그날까지 접수된 공시만 봅니다. 뒷날 것은 애초에 오지 않습니다."""
    if not events.covered(code):
        return None
    kinds, age = events.recent(code, day, events.WINDOW)
    if not kinds:
        return []
    return [{"갈래": kind, "며칠 전": age} for kind in sorted(kinds)]


def risk_stats(rows, prices, since=lab.SPLIT):
    """얼마나 깊이, 얼마나 오래 파였는지.

    연수익과 승률만 보면 이 규칙은 순해 보입니다. 실제로 겪는 것은 지갑이
    반으로 줄고 이 년 걸려 돌아오는 일입니다. 그것을 적어 둡니다.
    """
    out = lab.run(rows, prices, holds, lab.exit_fixed(TAKE, STOP, LIMIT),
                  slots=SLOTS, rank=order, since=since, detail=True,
                  per_day=PER_DAY, apart=apart(prices), realistic=True)
    if not out:
        return {}
    led = sorted(out["매매목록"], key=lambda got: got["판 날"])
    purse = top = 1.0
    when_top = led[0]["판 날"]
    worst, peak_day, low_day = 0.0, None, None
    path = []
    for got in led:
        purse *= 1 + got["손익"] / 100 / SLOTS
        if purse > top:
            top, when_top = purse, got["판 날"]
        dip = purse / top - 1
        path.append((got["판 날"], dip))
        if dip < worst:
            worst, peak_day, low_day = dip, when_top, got["판 날"]
    back = next((day for day, dip in path if low_day and day > low_day
                 and dip >= -0.001), None)
    yearly = {}
    for year in sorted({got["판 날"][:4] for got in led}):
        gains = [got["손익"] for got in led if got["판 날"][:4] == year]
        if len(gains) >= 5:
            yearly[year] = round(lab.deepest(gains, SLOTS), 1)
    return {"최대낙폭": round(worst * 100, 1), "꼭대기": peak_day, "바닥": low_day,
            "회복": back, "연패": out["연패"], "매매": out["매매"],
            "해마다 골": yearly}


def report(rows, prices):
    picked = [r for r in rows if holds(r)]
    body = {
        "name": NAME, "why": WHY, "caveat": CAVEAT,
        "tiers": [list(t) for t in TIERS],
        "take": TAKE, "stop": STOP, "limit": LIMIT, "slots": SLOTS,
        "made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M"),
        "기준": lab.score(rows), "규칙": lab.score(picked),
        "굴림": lab.portfolio(rows, prices, holds, slots=SLOTS, take=TAKE,
                            stop=STOP, limit=LIMIT, since="20160101", rank=order,
                            per_day=PER_DAY, apart=apart(prices), realistic=True),
        "층별": tier_stats(rows),
        "청산 견주기": exit_stats(rows, prices),
        "골": risk_stats(rows, prices),
        "오늘": today(rows),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    return body
