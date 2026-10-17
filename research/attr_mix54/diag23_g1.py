"""MPOS-0023 준비 진단 판 2(G1 · GPT #454 G1 답 반영 · 새 지표별 성과 안 봄): 원판 경로(문은 하나도 안 막음)에서 엔진이
기존 닮은 종목 문을 통과시킨 정배열 후보마다, 1일봉 엔진의 '슬롯 기준 사전 위험 증가 추정치'를 셈(최종 계좌 위험 아님).
- 후보 칸: 요청 = nrl.BASE_SIZE(row) · 가용 = top − used(엔진 프레임) · 예상 배정 = min(max(요청, 1), 가용, top) — lab.py:1031과 같은 식
  (swap · stop_run 안 씀 → freed/beyond 없음). 보유 칸 = open_slots의 실제 '자리'(종목마다 하나 · 같은 종목 겹침 없음).
- 공분산: 보유 + 후보 모두에 공통인 (시작 날, 끝 날) 하루 수익 구간만 고정(전 거래일까지 60개 창) → 그 같은 표본에서 포트폴리오 수익열을 직접 만들어
  표본 표준편차 σ_전 · σ_후. 공통 구간 < 40이면 결측. 상수열이면 결측. 음수 분산은 생길 수 없음(같은 표본 · 직접 셈).
- A(주가설) = σ_후(예상 배정) − σ_전 · B = σ_후(고정 1칸) − σ_전 · C(단독 위험 대조) = 예상 배정 비중 × 후보 σ(같은 표본) — 모두 %p(하루).
- 장부가 원판(0ec97a14…)과 같은지 이 안에서 확인(assert). cwd = 고정 나무 · tree_run. 출력: EX_OUT json(판단 순간 기록 · 요약)."""
import hashlib
import json
import math
import os
import sys
import types

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402

RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"
_SRC = open(os.environ["EX_PARTS"], "rb").read()
P = types.SimpleNamespace()
exec(compile(_SRC, os.environ["EX_PARTS"], "exec"), P.__dict__)
DAYS = {c: [d for d, _ in b["rows"]] for c, b in nrl.prices.items()}
CLOSE = {c: [x for _, x in b["rows"]] for c, b in nrl.prices.items()}
REC = []
CNT = {"판단": 0, "보유 없음": 0, "자료 모자람(60개 창)": 0, "공통 구간 < 40": 0, "상수열": 0, "요청 ≠ 예상 배정": 0, "가용 ≤ 0": 0}


def win(code, d):
    r, last = P.window(DAYS[code], CLOSE[code], d, 60)
    assert last is None or last < d
    return r


def sd(xs):
    n = len(xs)
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return math.sqrt(v) if v > 1e-18 else None


def measure(held, cand_code, w_cand, d):
    """held: [(종목, 비중)] · 공통 구간 표본에서 σ_전 · σ_후 · 후보 σ. 결측이면 (None, 이유)."""
    codes = [c for c, _ in held] + [cand_code]
    W = {c: win(c, d) for c in codes}
    if any(v is None for v in W.values()):
        return None, "자료 모자람(60개 창)"
    keys = set(W[codes[0]])
    for c in codes[1:]:
        keys &= set(W[c])
    keys = sorted(keys)
    if len(keys) < 40:
        return None, "공통 구간 < 40"
    p0 = [sum(w * W[c][k] for c, w in held) for k in keys]
    s0 = sd(p0)
    sc = sd([W[cand_code][k] for k in keys])
    if s0 is None or sc is None:
        return None, "상수열"
    out = {"n": len(keys), "σ전": s0, "σ후보": sc}
    for tag, w in (("A", w_cand), ("B", 0.1)):
        p1 = [p0[i] + w * W[cand_code][k] for i, k in enumerate(keys)]
        out[tag] = (sd(p1) - s0) * 100
    out["C"] = w_cand * sc * 100
    return out, ""


def apart(row, held):
    if not nrl.kin(row, held):
        return False
    if nrl.tier(row) != "정배열":
        return True
    loc = sys._getframe(1).f_locals
    CNT["판단"] += 1
    if not held:
        CNT["보유 없음"] += 1
        REC.append([row["date"], row["code"], None, "보유 없음"])
        return True
    slots = loc["open_slots"]
    top, used = loc["top"], loc["used"]
    req = nrl.BASE_SIZE(row)
    avail = top - used
    if avail <= 0:
        CNT["가용 ≤ 0"] += 1
    alloc = min(max(int(req), 1), avail, top)
    if alloc != req:
        CNT["요청 ≠ 예상 배정"] += 1
    items = [(sp["row"]["code"], sp["자리"] / 10) for sp in slots.values()]
    assert len({c for c, _ in items}) == len(items)
    m, why = measure(items, row["code"], alloc / 10, row["date"])
    if m is None:
        CNT[why] += 1
        REC.append([row["date"], row["code"], None, why])
        return True
    cs = [P.corr(win(row["code"], row["date"]), win(c, row["date"])) for c, _ in items]
    cs = [x for x in cs if x is not None]
    REC.append([row["date"], row["code"], {"요청": req, "가용": avail, "예상 배정": alloc, "보유 칸 합": sum(sp["자리"] for sp in slots.values()),
                                           "A": m["A"], "B": m["B"], "C": m["C"], "공통 구간": m["n"],
                                           "평균 상관": sum(cs) / len(cs) if cs else None}, ""])
    return True


rows = []
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=since, apart=apart, realistic=True, cap=130,
                detail=True, size=nrl.BASE_SIZE)
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in g["매매목록"]]
led = json.dumps(rows).encode()
assert hashlib.sha256(led).hexdigest() == RAW_SHA, "장부가 원판과 다름"


def ranks(xs):
    """평균 순위(동률은 평균)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2
        i = j + 1
    return r


def spear(x, y):
    a, b = ranks(x), ranks(y)
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    t = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    w = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b))
    return t / w if w else None


ok = [r for r in REC if r[2] is not None]
fr = [r for r in ok if r[0] <= "20211231"]


def q(xs, p):
    xs = sorted(xs)
    return xs[int(p * (len(xs) - 1))]


summary = {"판단 수 · 결측 · 요청 ≠ 배정": CNT, "값 있음": len(ok), "앞 기간(≤ 2021-12-31) 값": len(fr)}
for tag in ("A", "B", "C"):
    allv = [r[2][tag] for r in ok]
    fv = [r[2][tag] for r in fr]
    summary[tag] = {"분위 10 · 50 · 90%": [round(q(allv, p), 4) for p in (.1, .5, .9)], "앞 기간 70 · 80 · 90%": [round(q(fv, p), 4) for p in (.7, .8, .9)],
                    "음수 비율 %": round(sum(1 for v in allv if v < 0) / len(allv) * 100, 2)}
mc = [r for r in ok if r[2]["평균 상관"] is not None]
summary["순위 상관(평균 순위 · 동률 평균)"] = {"A 대 B": round(spear([r[2]["A"] for r in ok], [r[2]["B"] for r in ok]), 4),
                                    "A 대 C": round(spear([r[2]["A"] for r in ok], [r[2]["C"] for r in ok]), 4),
                                    "A 대 평균 상관": round(spear([r[2]["A"] for r in mc], [r[2]["평균 상관"] for r in mc]), 4),
                                    "B 대 평균 상관": round(spear([r[2]["B"] for r in mc], [r[2]["평균 상관"] for r in mc]), 4)}
th = q([r[2]["A"] for r in fr], .8)
top = [r for r in ok if r[2]["A"] >= th]
summary["A 앞 80% 넘는 판단(전체 · 앞 · 뒤)"] = [len(top), sum(1 for r in top if r[0] <= "20211231"), sum(1 for r in top if r[0] > "20211231")]
summary["그중 평균 상관 ≥ 0.2895(K80)"] = sum(1 for r in top if (r[2]["평균 상관"] or -9) >= 0.2895)
summary["그중 C도 앞 80% 넘음"] = sum(1 for r in top if r[2]["C"] >= q([x[2]["C"] for x in fr], .8))
out = {"부품 지문": hashlib.sha256(_SRC).hexdigest(), "장부 지문": RAW_SHA, "요약": summary, "판단 순간": REC}
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False)
print(json.dumps(summary, ensure_ascii=False, indent=1))
