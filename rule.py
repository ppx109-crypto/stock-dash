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

문턱 1.46의 근거는 41회차에 바뀌었습니다. 28회차에는 "골이 한 방향으로
얕아지는 비탈이라 믿을 만하다"였는데, 424종목에서 여덟 번씩 돌려 보니
비탈이 아니라 **고원**입니다 — 1.38·1.46·1.54가 앞 구간에서 +4.25·+5.37·
+4.45%로 평평하고 양쪽으로 다 내려갑니다(1.1에서 +1.94, 1.7에서 +0.14).
뒤 구간은 더 느슨한 1.3을 좋아합니다(+15.20). 1.46은 고원 한가운데이고 앞
구간에서 골이 가장 얕아(−13.3%) 그대로 둡니다. **값이 아니라 근거가
바뀌었습니다.**

60일 문턱은 43회차에 24.8에서 20으로 낮췄습니다. 조건을 하나씩 쌓아 재
보니 앞 구간 수익은 문턱이 없든 30이든 5.3~5.7%로 평평했습니다 — 이 조건은
앞쪽 수익에 아무것도 보태지 않고, **앞쪽 골을 줄이는 일만** 합니다
(−16.8% → −11.9%). 그런데 뒤 구간은 20과 24.8 사이에서 +17.50%에서
+13.65%로 단이 집니다. 없음~20 다섯 칸이 모두 17~20%대이므로 한 칸의
흔들림이 아닙니다. 수익을 먼저 보는 잣대대로 고원의 끝인 20을 씁니다.
꼭짓점인 15(+19.91%)는 피합니다.

정배열폭 조건은 36회차에 덜어 냈습니다. 문턱을 4 아래로 내리면 걸리는 것이
하나도 없었습니다 — 기울기와 60일 조건을 지난 종목은 이미 전부 정배열폭이
4를 넘습니다. 그러니 그 조건은 좋은 매매를 잘라내는 쪽으로만 일하고 있었고,
빼니 두 구간 모두에서 수익과 골이 함께 나아졌습니다.

고르는 잣대는 35회차에 바뀌었습니다. **먼저 연수익을 최대로 올리고, 그다음
파이는 자리들의 공통된 원인을 찾아 낙폭을 줄입니다.** 골을 먼저 깎으려고
수익을 미리 포기하지 않습니다. 다만 낙폭은 언제나 함께 적습니다. 문턱은
꼭짓점이 아니라 비탈 한가운데로 고릅니다.

자리가 셋이어도 하루에 담는 것은 둘까지이고, 이미 든 종목과 요즘 같이
움직이던 종목은 담지 않습니다. 셋이 한꺼번에 물리는 것을 줄이려는 것입니다
(20·21회차). 상한가에 붙은 날은 사지 않고 하한가에 붙은 날은 팔지 않습니다 —
실제로 할 수 없는 매매입니다(22회차).

**57회차에 둘째 문을 뗐습니다.** 아래 문단은 52회차에 붙일 때의 기록이고,
그 근거가 된 수치는 주식수 자료가 절반뿐이던 때의 것이라 무효입니다.
제대로 줄을 세우니 문 둘이 앞 +0.63%·뒤 +18.91%에 골 −29.2%/−44.4%이고,
추세 문 혼자가 앞 +3.81%·뒤 +18.63%에 골 −14.4%/−10.5%였습니다.

52회차에 **문을 하나 더 냈었습니다.** 네 이동평균선이 정배열인데 그날 거래량이
지난 한 달 가운데값의 5배를 넘으면, 조용하지 않아도 삽니다. 51회차에 재어
보니 이 문의 후보(1,363줄)와 추세 문의 후보(1,325줄)가 거의 안 겹쳐서, 함께
걸면 자리가 노는 날이 줄어듭니다(가동률 56% → 70%). 두 구간 다 수익이 두 배
가까이 올랐고 골도 두 배가 되었습니다. 문턱 5배의 근거는 고원입니다 — 터짐
문을 혼자 굴리면 이웃 문턱끼리 12%p씩 튀는 톱니인데, 추세 문과 함께 걸면
앞 구간이 문턱 2.5~8배 범위에서 11.4~14.1%로 평평해지고 뒤 구간은 4~6배가
고원입니다. 5배가 그 한가운데입니다.

**아직 임시입니다.** 501종목을 다 채워 42회차에 전부 다시 쟀습니다. 조용함·
정배열폭·문턱·보유 기간은 버텼지만, **앞 구간 성적이 내려갔습니다** —
243종목에서 +6.38%였던 것이 424종목에서 +5.37%, 501종목에서 +3.82%입니다.
종목을 늘릴수록 내려간다는 것은 앞선 수치가 살아남은 회사만 본 덕을 보고
있었다는 뜻입니다. 그리고 501종목도 **오늘의** 시가총액으로 고른 것이라
그 치우침이 다 없어진 것은 아닙니다. 방향은 믿되 자릿수는 믿지 마십시오.
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
# 59회차에 2015-06-29에서 옮겼습니다. 주식수 자료가 덮기 시작하는 날은
# 그때가 맞지만, **덮는다고 다 채워진 것이 아니었습니다** — 100등 자리 가운데
# 순위를 못 받은 몫이 2015년 96%, 2016년 41%였습니다. 삼성전자가 2017-03-31,
# 현대차가 2022년에야 첫 순위를 받습니다. 그 두 해로 잰 것은 '100등 안'이
# 아니라 '남은 것 중 100등 안'이라 수치가 아닙니다. 2017년부터 새는 몫이
# 10% 아래로 떨어져 어림이나마 잴 수 있습니다.
SINCE = "20170101"       # 순위를 어림이나마 믿을 수 있는 첫 해.
MID = "20210101"         # 앞뒤로 나눠 보는 자리. 뒤쪽은 새는 몫이 1% 아래입니다.

TOP = 100                # 살 때 그날 시가총액 순위가 이 안이어야 합니다
CALM = 0.4               # 변동성이 아래 40% 안. 절벽 위라 늦추면 안 됩니다
SLOPE = 1.46             # 추세선(180일)이 닷새 사이 이만큼 올라 있을 것
SIXTY = 20.0             # 60일 전보다 이만큼 올라 있을 것
BURST = 5.0              # 둘째 문. 그날 거래량이 지난 한 달 가운데값의 이 배수
TAKE, STOP = 10.0, 5.0   # 익절·손절
LIMIT = 10               # 열 거래일. 이 날이 지나면 그냥 정리
SLOTS = 3                # 자리. 자금을 셋으로 나눕니다.
PER_DAY = 2              # 하루에 새로 담는 수. 셋을 한날에 몰아 담지 않습니다.
KIN = 0.6                # 이미 든 것과 이만큼 넘게 같이 움직이면 담지 않습니다.
OUT = Path("study") / "rule.json"

WHY = (
    "그날 시가총액이 100등 안이고, 그 종목이 평소 조용한 편이며(변동성 아래 "
    "40%), 180일 추세선이 닷새 사이 1.46% 올라 있고, 60일 전보다 20% 넘게 "
    "올라 있는 날입니다. "
    "한마디로 큰 회사가 조용히, 그러나 오래 오르고 있는 자리입니다. "
    "52회차에 '거래량이 터진 정배열'을 둘째 문으로 붙였다가 57회차에 "
    "뗐습니다 — 주식수 자료가 절반뿐이라 순위가 헐겁던 때만 좋아 보였습니다. "
    "순위는 그날까지 접수된 주식수로 그날 매긴 것이라, 오늘의 순위로 과거를 "
    "고르지 않습니다. "

    "하루에 새로 담는 것은 둘까지이고, 이미 든 종목과 요즘 같이 움직이던 "
    "종목은 담지 않습니다. 셋이 함께 물리는 것을 줄이려는 것입니다."
)
CAVEAT = (
    "**이 수치는 임시입니다.** 조사 대상이 507종목이고 그날 순위를 믿을 수 "
    "있는 것이 2017년부터라, 앞쪽 구간의 매매가 94번입니다. "
    "한 해 스물세 번 남짓입니다. 27회차에 종목을 3분의 1 덜어 내 보았더니 뒤쪽 "
    "수익이 반토막 났습니다. 그 정도로 흔들리는 표본입니다. "
    "게다가 501종목은 **오늘의** 시가총액으로 고른 것이라, 2016년에 100등 "
    "안이었다가 지금 작아진 회사는 아예 들어 있지 않습니다. 살아남은 것만 "
    "보는 쪽이라 성적이 실제보다 좋게 나옵니다. "
    "507종목에서 여덟 번 돌린 가운데값으로 연수익은 앞쪽(2017~2020) "
    "**+4.23%**(폭 3.6)·뒤쪽(2021~) **+19.08%**(폭 1.1)이고, 골은 "
    "**−18.5%와 −10.5%**, 연패는 5와 6입니다. "
    "86회차에 모의 매매가 신호 난 날만 걸어 보유가 달력보다 길게 잡히던 "
    "것을 고쳤고, 이 수치는 고친 뒤의 값입니다. 돈이 실제로 들어가 있는 "
    "날은 전체의 5분의 1 남짓입니다. "
    "**두 구간은 믿을 만한 정도가 다릅니다.** 뒤쪽은 그날 100등을 매길 "
    "자료가 거의 다 차 있어(빠진 자리 1% 아래) 곧이곧대로 읽어도 됩니다. "
    "앞쪽은 7~10%가 비어 있어 어림입니다. **2015·2016년은 96%와 41%가 "
    "비어 있어 아예 뺐습니다**(59회차) — 그 두 해로 잰 것은 '100등 안'이 "
    "아니라 '남은 것 중 100등 안'이었습니다. "
    "47회차까지 적혀 있던 '앞 +7.54%'는 두 겹으로 틀린 값이었습니다. "
    "한 번만 돌린 "
    "수치는 여러 번 중 좋은 쪽일 수 있습니다 — 40회차에 그런 수치 하나에 "
    "속아 결론을 냈다가 거뒀습니다. 열 번에 다섯 번은 집니다. "
    "앞쪽 구간은 한 해 스물세 번 남짓 매매해서 +4.23%입니다. 비용과 "
    "미끄러짐을 더 얹으면 남는 것이 거의 없을 수도 있습니다. "
        "오르고 있는 종목을 사는 규칙이라, 오르던 것이 멈추는 자리에서 삽니다. "
    "손절을 5%로 두어도 하루 사이에 그보다 더 빠지면 그대로 잃습니다. "
    "49회차에 재어 보니 장중에 −5% 지정가 손절을 걸어 두는 쪽이 오히려 "
    "나빴고, **+10% 지정가 매도를 미리 걸면 수익이 반 토막 납니다.** "
    "둘 다 종가에 보고 정하십시오. "
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


def trend_leg(row):
    """첫째 문 — 조용한데 길게 오르고 있는 자리. 34회차까지의 규칙입니다."""
    if _calm is None or (row.get("변동성") or 99) > _calm:
        return False
    return ((row.get("추세 기울기") or -99) >= SLOPE
            and (row.get("60일 전 대비") or -99) >= SIXTY)


def burst_leg(row):
    """둘째 문 — 네 선이 정배열인데 거래량이 터진 자리(51회차).

    조용함을 보지 않습니다. 오히려 시끄러운 날을 삽니다. 첫째 문과 겹치는
    자리가 거의 없어, 둘을 함께 걸면 자리가 노는 날이 줄어듭니다.
    """
    return row.get("배열") == 3 and (row.get("거래량비") or 0) >= BURST


def holds(row):
    """살 자리인지. 100등 안에서 추세 문을 지나야 합니다.

    52회차에 터짐 문을 둘째 문으로 붙였다가 **57회차에 떼어 냈습니다.**
    붙일 때의 근거(앞 8.79 · 뒤 37.88)는 주식수 자료가 199종목에만 있어
    하루에 153종목으로만 줄을 세우던 때의 수치였습니다. 499종목으로 제대로
    줄을 세우니 문 둘이 앞 0.63 · 뒤 18.91에 골 −29.2 / −44.4이고, 추세 문
    혼자가 앞 3.81 · 뒤 18.63에 골 −14.4 / −10.5입니다. **앞에서 지고 뒤에서
    비기며 골만 네 배로 깊어지는 문**이라 뗍니다.

    `burst_leg`는 남겨 둡니다 — `each_condition`이 아직 재고, 다시 붙일
    일이 있으면 그때 쓸 수 있게.
    """
    return caps.inside(row, TOP) and trend_leg(row)


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
                      "거래량비": row.get("거래량비"),
                      "변동성": row.get("변동성"),
                      "영업이익성장": row.get("영업이익성장"),
                      "매출성장": row.get("매출성장"),
                      "최근 공시": _filings(code, row["date"])})
    found.sort(key=lambda r: (not r["해당"], -(r.get("추세 기울기") or -99)))
    return found


def each_condition(rows, since=SINCE):
    """조건을 하나씩 빼 보면 무엇이 일을 하고 있는지 보입니다.

    네 조건을 한 덩어리로 보면 '이 규칙은 이렇다'로만 읽힙니다. 하나씩
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
        "네 조건 모두": holds,
        "떼어 낸 터짐 문": lambda r: caps.inside(r, TOP) and burst_leg(r),
        "100등 조건만 뺌": lambda r: holds_without(r, "top"),
        "조용함 조건만 뺌": lambda r: holds_without(r, "calm"),
        "기울기 조건만 뺌": lambda r: holds_without(r, "slope"),
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
    """조건 하나를 빼고 봅니다. 어느 것이 일하는지 재는 데 씁니다.

    두 문 가운데 어느 쪽 조건을 뺐는지에 따라 그 문만 느슨해집니다.
    "burst"를 빼면 둘째 문이 '정배열이기만 하면'이 됩니다.
    """
    if skip != "top" and not caps.inside(row, TOP):
        return False
    calm = skip == "calm" or (_calm is not None
                              and (row.get("변동성") or 99) <= _calm)
    slope = skip == "slope" or (row.get("추세 기울기") or -99) >= SLOPE
    sixty = skip == "sixty" or (row.get("60일 전 대비") or -99) >= SIXTY
    return calm and slope and sixty


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


def halves(rows, prices, slots=None, take=None, stop=None):
    """앞뒤로 나눠 나란히 냅니다. 한쪽에서만 좋은 것은 믿지 않으려는 것입니다.

    slots·take·stop을 주면 그 값으로 굴립니다. 73회차의 공격 갈래(자리 2 ·
    익절 12 · 손절 8)를 연구 스크립트가 아니라 이 길로 재려고 낸 자리입니다.
    비워 두면 지금 규칙 그대로입니다.
    """
    slots = SLOTS if slots is None else slots
    take = TAKE if take is None else take
    stop = STOP if stop is None else stop
    kin = apart(prices)
    found = {}
    for tag, use, since in ((f"앞쪽 {SINCE[:4]}~{int(MID[:4]) - 1}",
                             [r for r in rows if r["date"] < MID], SINCE),
                            (f"뒤쪽 {MID[:4]}~", rows, MID)):
        got = lab.run(use, prices, holds, lab.exit_fixed(take, stop, LIMIT),
                      slots=slots, rank=order, since=since, per_day=PER_DAY,
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
        "조건": {"등수": TOP,
               "추세 문": {"조용함": f"변동성 아래 {CALM*100:.0f}%",
                        "조용함 문턱": round(_calm, 2) if _calm else None,
                        "추세 기울기": SLOPE, "60일 전 대비": SIXTY},
               "터짐 문": {"배열": "네 선 정배열", "거래량비": BURST}},
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
