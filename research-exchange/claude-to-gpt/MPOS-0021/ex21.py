"""MPOS-0021(국면 다시 나누기 · 사용자 2026-10-16 "장기이평 60 밑 마감 · 국면 제거 · 더 잘게 · 1,2,3 전부 해보자"): 1일봉 장부 만들기.
고정 나무(9743cb802) 엔진 lab.run을 그대로 쓰고 살 문(holds) · 크기(size) · 나가기(exit_at)에 국면 조건만 덧씌움(엔진 수정 없음).
EX_MODE=BASE : 원판 — 장부가 z055_d1_raw.json(sha 0ec97a14…)과 같아야 함(재현 검사).
EX_MODE=B    : 1일봉 국면 문 — 판단 날 d의 '전 거래일' KODEX 200(069500) 종가 < 그 전 거래일까지 N일 단순평균이면 d에 새로 사지 않음.
EX_MODE=BX   : B + 들고 있는 것 정리 — 보유 중 오늘(d) 칸에서 위 조건(전 거래일 기준)이 참이면 d 종가에 팜(두 갈래 모두).
EX_MODE=C    : 정배열 갈래 시장 폭 문의 문턱을 EX_N으로 바꿈(원판 50 · EX_N=0이면 문 없앰 = 국면 제거).
EX_MODE=CT   : 시장 폭 잘게 — 폭 < 40 안 삼 · 40 ≤ 폭 < 50 정배열 갈래만 1칸으로 삼 · 폭 ≥ 50 원판 그대로.
EX_MODE=GLEAK: 검사 도구 자체 시험 전용 — B 문이 'd 뒤 5번째 거래일' 069500 종가를 봄(일부러 미래 · 자르기 시험이 잡아야 함).
판단에 쓰는 값: B · BX는 d보다 앞 날의 069500 종가만(국면 판단 하루 늦춤 · 같은 날 종가 안 씀). C · CT는 원판과 같은 그날 시장 폭(BR · 원판 상속).
EX_POISON=날 · EX_CUTMODE=scale|drop: 그 날 뒤 종목 종가와 069500 종가를 0.7배로 바꾸거나(scale) 처음부터 지움(drop) · 그 날 뒤엔 새로 사지 않음.
날짜 접근 감사(parts21.HeldAudit = MPOS-0020 Audit + 보유 칸 관찰) · 진입 기록(parts21.Entries: 요청 칸 · 배정 칸) + 국면 문 접근 감사(읽은 069500 날 < 판단 날)를 EX_OUT.audit.json에 씀.
cwd = 고정 나무 · tree_run으로 실행. 출력: EX_OUT(json 장부 [(코드, 산 날, 판 날, 손익, 자리)])."""
import bisect
import hashlib
import json
import os
import sys
import types

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
from pathlib import Path  # noqa: E402

_C = Path(os.environ["NRL_CACHE"])
assert _C.exists() and _C.stat().st_mtime > lab.CACHE.stat().st_mtime, "nrl 캐시를 다시 구울 상황 → 중단"
import nrl  # noqa: E402
import rule  # noqa: E402
import final_study as F  # noqa: E402

_SRC = open(os.environ["EX_PARTS"], "rb").read()
PARTS_SHA = hashlib.sha256(_SRC).hexdigest()
parts20 = types.SimpleNamespace()
exec(compile(_SRC, os.environ["EX_PARTS"], "exec"), parts20.__dict__)

MODE = os.environ["EX_MODE"]
assert MODE in ("BASE", "B", "BX", "C", "CT", "GLEAK")
N = int(os.environ.get("EX_N", "0"))
POISON = os.environ.get("EX_POISON", "")
CUTMODE = os.environ.get("EX_CUTMODE", "scale")
assert CUTMODE in ("scale", "drop")


def poisoned(rows):
    if POISON and CUTMODE == "scale":
        return [(d, x * 0.7 if d > POISON else x) for d, x in rows]
    if POISON and CUTMODE == "drop":
        return [(d, x) for d, x in rows if d <= POISON]
    return rows


PRICES = nrl.prices
if POISON:
    PRICES = {c: dict(b, rows=poisoned(b["rows"])) for c, b in nrl.prices.items()}
    PRICES = {c: b for c, b in PRICES.items() if b["rows"]}
DATA_END = max(d for b in PRICES.values() for d, _ in b["rows"])

ETF = poisoned([(d, float(x)) for d, x in json.load(open("etf-data/069500.json"))["closes"] if x])
ED = [d for d, _ in ETF]
EX = [x for _, x in ETF]
PRE = [0.0]
for x in EX:
    PRE.append(PRE[-1] + x)
GATE = {"판단 수": 0, "막음": 0, "읽은 069500 날 ≥ 판단 날": 0}


def below(d):
    """d보다 앞 마지막 069500 거래일 p의 종가 < p까지 N일 단순평균이면 True(국면 아래). 평균이 모자라면 False(막지 않음).
    GLEAK는 일부러 d 뒤 첫 거래일을 p로 씀."""
    k = bisect.bisect_left(ED, d)                       # ED[k-1] < d ≤ ED[k]
    # GLEAK: d 뒤 5번째 거래일 · 그 칸이 없으면 마지막 칸으로 붙음(흔한 누수 모양).
    # 판 1(다음 거래일 · 없으면 안 막음)과 판 2(5번째 · 없으면 안 막음)는 D 방식에서 0/6 — 시험 날이 '문이 열린 날'이라 '안 막음'과 늘 같았음
    p = k - 1 if MODE != "GLEAK" else min(bisect.bisect_right(ED, d) + 4, len(ED) - 1)
    GATE["판단 수"] += 1
    if p < 0 or p >= len(ED) or p - N + 1 < 0:
        return False
    if ED[p] >= d:
        GATE["읽은 069500 날 ≥ 판단 날"] += 1
    ma = (PRE[p + 1] - PRE[p + 1 - N]) / N
    hit = EX[p] < ma
    GATE["막음"] += hit
    return hit


def wide_aligned(r, lo):
    f = F.form_of(nrl.shape, r)
    return f.get("정배열") and f.get("간격") is not None and nrl.LO <= f["간격"] < nrl.HI and nrl.BR.get(r["date"], 0) >= lo


holds, size, exit_at = nrl.BASE_HOLD, nrl.BASE_SIZE, nrl.BASE_EXIT
if MODE in ("B", "BX", "GLEAK"):
    holds = (lambda h: lambda r: h(r) and not below(r["date"]))(nrl.BASE_HOLD)
if MODE == "BX":
    def exit_at(lane, start, price, step, peak, row=None):
        if step >= 1 and below(lane["날"][start + step]):
            return True
        return nrl.BASE_EXIT(lane, start, price, step, peak, row)
if MODE == "C":
    holds = lambda r: (rule.holds(r) or wide_aligned(r, N)) and nrl.teacher(r) and not nrl.target_cut(r)   # noqa: E731
if MODE == "CT":
    holds = lambda r: (rule.holds(r) or wide_aligned(r, 40)) and nrl.teacher(r) and not nrl.target_cut(r)  # noqa: E731
    size = lambda r: nrl.BASE_SIZE(r) if rule.holds(r) or nrl.BR.get(r["date"], 0) >= 50 else 1       # noqa: E731

rows, audit = [], {}
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    h = holds
    if POISON:
        h = (lambda hh: lambda r: r["date"] <= POISON and hh(r))(holds)
    ex = parts20.HeldAudit(exit_at, DATA_END)
    ent = parts20.Entries(size)
    g = lab.run(pool, PRICES, h, ex, slots=nrl.SLOTS, rank=rule.order, since=since, apart=nrl.kin, realistic=True, cap=130,
                detail=True, size=ent)
    lane_of = {c: [d for d, _ in b["rows"]] for c, b in PRICES.items()}
    held = {(c, lane_of[c][i]): z for (c, i), z in ex.held.items()}          # (종목, 산 날) → 다음 날 청산 판단에서 본 실제 보유 칸
    seen = [e for e in ent.rows if (e[0], e[1]) in held]
    bad = [e for e in seen if held[(e[0], e[1])] != e[3]]
    got = (g or {}).get("매매목록") or []
    assert g or POISON, side
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in got]
    audit[side] = dict(ex.receipt(), **{"국면 문": dict(GATE), "자리일(들고 × 자리)": sum(t["들고"] * (t.get("자리") or 1) for t in got),
                                       "진입(종목 · 산 날 · 요청 칸 · 배정 칸)": ent.rows,
                                       "배정 칸 대조": {"다음 날 보유 칸을 본 진입": len(seen), "배정 칸 ≠ 보유 칸": len(bad), "예": bad[:3]}})
    GATE.update({k: 0 for k in GATE})
    print(side, len(got), flush=True)
json.dump(rows, open(os.environ["EX_OUT"], "w"))
json.dump({"부품 지문": PARTS_SHA, "자료 끝": DATA_END, "자르기": CUTMODE if POISON else "없음", **audit}, open(os.environ["EX_OUT"] + ".audit.json", "w"),
          ensure_ascii=False, indent=1)
print("매매", len(rows))
