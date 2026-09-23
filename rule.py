"""지금 쓰는 규칙과, 오늘 그 규칙에 걸리는 종목.

**살 때 코스피 100등 안**의 기업만 봅니다. 그날의 시가총액으로 가립니다 —
오늘의 순위로 과거를 고르면 '앞으로 커질 회사만 골라 산' 셈이 되어, 어떤
규칙이든 좋아 보입니다(25회차).

그 안에서 **조용한데 길게 오르고 있는 종목**을 삽니다. 23회차에서 변동성으로
그룹을 가르니 정반대의 규칙이 필요했습니다. 출렁이는 종목은 떨어진 것이
되돌아오고(평균회귀), 조용한 종목은 오르던 것이 더 오릅니다(추세). 100등
안은 조용한 쪽입니다. 그래서 여기서는 추세를 삽니다.

스물네 회차 동안 다듬었던 평균회귀 규칙은 **여기서 돈을 잃습니다**
(2015~2020 −6.59%). 그 규칙은 작고 출렁이고 거래가 적은 종목 위에 서
있었습니다 — 유동성 문턱을 얹자 수익의 절반이 사라졌습니다(27회차).
아쉽지만 조건이 바뀌면 규칙도 바뀝니다.

추세는 **180일선**으로 봅니다. 35회차에 축 길이 자체를 처음 바꿔 보았습니다.
긴 축을 120에서 180·240·300·360으로 늦추니 두 구간이 한 방향으로 좋아지다가
300에서 꺾였습니다. 꼭대기가 180입니다. 반대로 정배열폭을 재는 짝(20/60)은
늘릴수록 나빠졌으므로 그대로 둡니다.

고르는 잣대는 35회차에 바뀌었습니다. **먼저 연수익을 최대로 올리고, 그다음
파이는 자리들의 공통된 원인을 찾아 낙폭을 줄입니다.** 골을 먼저 깎으려고
수익을 미리 포기하지 않습니다. 다만 낙폭은 언제나 함께 적습니다. 문턱은
꼭짓점이 아니라 비탈 한가운데로 고릅니다.

자리가 셋이어도 하루에 담는 것은 둘까지이고, 이미 든 종목과 요즘 같이
움직이던 종목은 담지 않습니다. 셋이 한꺼번에 물리는 것을 줄이려는 것입니다
(20·21회차). 상한가에 붙은 날은 사지 않고 하한가에 붙은 날은 팔지 않습니다 —
실제로 할 수 없는 매매입니다(22회차).

**아직 임시입니다.** 조사 대상이 243종목이고 주식수가 2015년부터라, 매매가
한쪽 구간에 여든 번씩뿐입니다. 500종목 자료가 채워지면 전부 다시 잽니다.
방향은 믿되 자릿수는 믿지 마십시오.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import caps
import events
import lab

NAME = "코스피 100등 안에서 조용히 길게 오르는 종목"
SINCE = "20150629"       # 주식수 자료가 덮는 첫날. 그 앞은 순위를 모릅니다.
MID = "20210101"         # 앞뒤로 나눠 보는 자리

TOP = 100                # 살 때 그날 시가총액 순위가 이 안이어야 합니다
CALM = 0.4               # 변동성이 아래 40% 안. 절벽 위라 늦추면 안 됩니다
SLOPE = 1.46             # 추세선(180일)이 닷새 사이 이만큼 올라 있을 것
WIDTH = 6.18             # 정배열폭
SIXTY = 24.8             # 60일 전보다 이만큼 올라 있을 것
TAKE, STOP = 10.0, 5.0   # 익절·손절
LIMIT = 10               # 열 거래일. 이 날이 지나면 그냥 정리
SLOTS = 3                # 자리. 자금을 셋으로 나눕니다.
PER_DAY = 2              # 하루에 새로 담는 수. 셋을 한날에 몰아 담지 않습니다.
KIN = 0.6                # 이미 든 것과 이만큼 넘게 같이 움직이면 담지 않습니다.
OUT = Path("study") / "rule.json"

WHY = (
    "그날 시가총액이 100등 안이고, 그 종목이 평소 조용한 편이며(변동성 아래 "
    "40%), 180일 추세선이 닷새 사이 1.46% 올라 있고, 단기선이 장기선 위로 6% "
    "넘게 벌어져 있으며, 60일 전보다 25% 넘게 올라 있는 날입니다. "
    "한마디로 큰 회사가 조용히, 그러나 오래 오르고 있는 자리입니다. "
    "순위는 그날까지 접수된 주식수로 그날 매긴 것이라, 오늘의 순위로 과거를 "
    "고르지 않습니다. "
    "하루에 새로 담는 것은 둘까지이고, 이미 든 종목과 요즘 같이 움직이던 "
    "종목은 담지 않습니다. 셋이 함께 물리는 것을 줄이려는 것입니다."
)
CAVEAT = (
    "**이 수치는 임시입니다.** 조사 대상이 243종목이고 그날 순위를 매길 수 "
    "있는 자료가 2015년 6월부터라, 한쪽 구간의 매매가 여든 번씩뿐입니다. "
    "한 해 스무 번입니다. 27회차에 종목을 3분의 1 덜어 내 보았더니 뒤쪽 "
    "수익이 반토막 났습니다. 그 정도로 흔들리는 표본입니다. "
    "게다가 243종목은 **오늘의** 시가총액으로 고른 것이라, 2016년에 100등 "
    "안이었다가 지금 작아진 회사는 아예 들어 있지 않습니다. 살아남은 것만 "
    "보는 쪽이라 성적이 실제보다 좋게 나옵니다. "
    "골은 앞쪽(2015~2020) −11.5%, 뒤쪽(2021~) −11.2%였습니다. 연수익은 "
    "+7.89%와 +13.29%입니다. 열 번에 다섯 번은 집니다. "
    "오르고 있는 종목을 사는 규칙이라, 오르던 것이 멈추는 자리에서 삽니다. "
    "손절을 5%로 두어도 하루 사이에 그보다 더 빠지면 그대로 잃습니다. "
    "지나간 자료로 확인한 것이며 앞날을 약속하지 않습니다. "
    "매수·매도 신호가 아닙니다."
)


_calm = None


def calm_edge(rows):
    """'조용하다'의 문턱. 전체 종목의 변동성 아래 CALM 자리입니다.

    절댓값(예: 2.13%)을 박아 두지 않는 것은, 시장 전체가 조용해지거나
    출렁여도 '상대적으로 조용한 쪽'을 가리키게 하려는 것입니다.
    """
    global _calm
    if _calm is None:
        vals = sorted(row["변동성"] for row in rows
                      if row.get("변동성") is not None)
        _calm = vals[int(len(vals) * CALM)] if vals else 0.0
    return _calm


def holds(row):
    """살 자리인지. 다섯 조건을 모두 넘어야 합니다."""
    if not caps.inside(row, TOP):
        return False
    if _calm is None or (row.get("변동성") or 99) > _calm:
        return False
    return ((row.get("추세 기울기") or -99) >= SLOPE
            and (row.get("정배열폭") or -99) >= WIDTH
            and (row.get("60일 전 대비") or -99) >= SIXTY)


def order(row):
    """더 가파르게 오르고 있는 것부터 담습니다."""
    return -(row.get("추세 기울기") or 0)


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
        found.append({"code": code, "name": row.get("name") or code,
                      "date": row["date"], "해당": holds(row),
                      "시총순위": row.get(caps.RANK),
                      "추세 기울기": row.get("추세 기울기"),
                      "정배열폭": row.get("정배열폭"),
                      "60일 전 대비": row.get("60일 전 대비"),
                      "변동성": row.get("변동성"),
                      "영업이익성장": row.get("영업이익성장"),
                      "매출성장": row.get("매출성장"),
                      "최근 공시": _filings(code, row["date"])})
    found.sort(key=lambda r: (not r["해당"], -(r.get("추세 기울기") or -99)))
    return found


def each_condition(rows, since=SINCE):
    """조건을 하나씩 빼 보면 무엇이 일을 하고 있는지 보입니다.

    다섯 조건을 한 덩어리로 보면 '이 규칙은 이렇다'로만 읽힙니다. 하나씩
    빼 보면 어느 것이 실제로 거르고 있고 어느 것이 장식인지 드러납니다.
    """
    calm_edge(rows)
    picks = [row for row in rows if row["date"] >= since]

    def count(test):
        got = [row for row in picks if test(row)]
        vals = sorted(row["ahead"][lab.HORIZON] - lab.COST for row in got
                      if row.get("ahead", {}).get(lab.HORIZON) is not None)
        if len(vals) < 60:
            return None
        cut = max(1, len(vals) // 10)
        return {"건수": len(vals), "날": len({row["date"] for row in got}),
                "종목": len({row["code"] for row in got}),
                "평균": round(sum(vals) / len(vals), 2),
                "중앙": round(vals[len(vals) // 2], 2),
                "하위10%": round(sum(vals[:cut]) / cut, 1)}

    parts = {
        "다섯 조건 모두": holds,
        "100등 조건만 뺌": lambda r: holds_without(r, "top"),
        "조용함 조건만 뺌": lambda r: holds_without(r, "calm"),
        "기울기 조건만 뺌": lambda r: holds_without(r, "slope"),
        "정배열폭 조건만 뺌": lambda r: holds_without(r, "width"),
        "60일 조건만 뺌": lambda r: holds_without(r, "sixty"),
        "아무 조건 없음": lambda r: True,
    }
    found = []
    for tag, test in parts.items():
        got = count(test)
        if got:
            found.append({"무엇": tag, **got})
    return found


def holds_without(row, skip):
    """조건 하나를 빼고 봅니다. 어느 것이 일하는지 재는 데 씁니다."""
    if skip != "top" and not caps.inside(row, TOP):
        return False
    if skip != "calm" and (_calm is None or (row.get("변동성") or 99) > _calm):
        return False
    if skip != "slope" and (row.get("추세 기울기") or -99) < SLOPE:
        return False
    if skip != "width" and (row.get("정배열폭") or -99) < WIDTH:
        return False
    if skip != "sixty" and (row.get("60일 전 대비") or -99) < SIXTY:
        return False
    return True


# 자리를 꽉 채워 굴릴 때와, 한 번에 한 종목만 들 때는 답이 다릅니다.
# 앞은 하루라도 자리를 비우면 손해라 빨리 끊는 편이 낫고, 뒤는 자리 다툼이
# 없으니 벌어진 것이 메워질 때까지 들고 가는 편이 낫습니다. 둘 다 보여 줍니다.
EXITS = {
    "고정 익절·손절 (자리를 꽉 채워 굴릴 때)": lambda: lab.exit_fixed(TAKE, STOP, LIMIT),
    "익절10 손절5 되돌림3 발동2": lambda: lab.exit_mixed(TAKE, STOP, 3.0, 2.0, LIMIT),
}


def apart(prices):
    """같이 물릴 것을 함께 담지 않게 하는 잣대. 그날까지의 수익률만 씁니다."""
    return lab.unlike(lab.moves(prices), edge=KIN)


def exit_stats(rows, prices, since=SINCE):
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


def risk_stats(rows, prices, since=SINCE):
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


def halves(rows, prices):
    """앞뒤로 나눠 나란히 냅니다. 한쪽에서만 좋은 것은 믿지 않으려는 것입니다."""
    kin = apart(prices)
    found = {}
    for tag, use, since in (("앞쪽 2015~2020",
                             [r for r in rows if r["date"] < MID], SINCE),
                            ("뒤쪽 2021~", rows, MID)):
        got = lab.run(use, prices, holds, lab.exit_fixed(TAKE, STOP, LIMIT),
                      slots=SLOTS, rank=order, since=since, per_day=PER_DAY,
                      apart=kin, realistic=True)
        if got:
            found[tag] = {k: got[k] for k in
                          ("매매", "승률", "평균", "중앙", "하위10%",
                           "최대낙폭", "연패", "가동률", "연수익")}
    return found


def report(rows, prices):
    caps.tag(rows, TOP)
    calm_edge(rows)
    picked = [r for r in rows if holds(r)]
    body = {
        "name": NAME, "why": WHY, "caveat": CAVEAT, "임시": True,
        "조건": {"등수": TOP, "조용함": f"변동성 아래 {CALM*100:.0f}%",
               "조용함 문턱": round(_calm, 2) if _calm else None,
               "추세 기울기": SLOPE, "정배열폭": WIDTH, "60일 전 대비": SIXTY},
        "take": TAKE, "stop": STOP, "limit": LIMIT, "slots": SLOTS,
        "made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M"),
        "기준": lab.score(rows), "규칙": lab.score(picked),
        "굴림": lab.portfolio(rows, prices, holds, slots=SLOTS, take=TAKE,
                            stop=STOP, limit=LIMIT, since=SINCE, rank=order,
                            per_day=PER_DAY, apart=apart(prices), realistic=True),
        "앞뒤": halves(rows, prices),
        "조건마다": each_condition(rows),
        "청산 견주기": exit_stats(rows, prices),
        "골": risk_stats(rows, prices),
        "오늘": today(rows),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    return body
