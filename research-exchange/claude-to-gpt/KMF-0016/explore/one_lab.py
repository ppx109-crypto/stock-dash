"""KMF-0016 탐색(사용자 2026-10-13: "계약1개로하자 · 추세봇일때는 추세봇을 횡보일때는 횡보봇을").
전체 자료 01-02 ~ 10-12 · 5분봉 · 한 계약 · 하루 −25p(계좌 하나에 한 번) · 편도 0.04p.
봇마다 '원하는 자리'(마지막 신호 값 · 그날 처음엔 0)를 봉마다 만들고, 한 계약으로 합치는 규칙을 견줌:
  first  먼저 든 봇이 정리할 때까지 그 봇을 따름(둘 다 새로 들면 추세 봇 먼저)
  trend  추세 봇이 자리를 원하면 언제나 추세 봇 · 아니면 횡보 봇
  range  횡보 봇 우선
  + time 위 둘이 모두 쉬는 동안에만 KMF-0015 시간대 봇(선택)"""
import sys, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf13 as M13, kmf14 as M14, kmf15 as M15
sys.path.insert(0, str(ROOT / "research-exchange/claude-to-gpt/KMF-0014/explore"))
import short_lab as S
K.DAY_STOP = -25.0
b = M13.prep(K._rows_before(M13.END))


def intent(want):
    out, cur, day = [], 0, None
    for i, x in enumerate(want):
        if b[i][0] != day:
            day, cur = b[i][0], 0
        if x in (1, -1, 0):
            cur = x
        out.append(cur)
    return out


P = {"T": intent(M13.signals(b, M13.grid()[0])), "R": intent(M14.signals(b, M14.grid()[0])), "W": intent(M15.signals(b, M15.grid()[0]))}


def combine(rule, use_w):
    want = [None] * len(b); prev = 0; holder = None; day = None
    for i in range(len(b)):
        if b[i][0] != day:
            day, prev, holder = b[i][0], 0, None
        t, r, w = P["T"][i], P["R"][i], P["W"][i] if use_w else 0
        if rule == "trend":
            tgt = t if t else (r if r else w)
            holder = None
        elif rule == "range":
            tgt = r if r else (t if t else w)
        else:                                            # first
            if holder and P[holder][i] == 0 if holder != "W" or use_w else True:
                holder = None
            if holder is None:
                holder = "T" if t else ("R" if r else ("W" if w else None))
            tgt = P[holder][i] if holder else 0
            if holder == "W" and (t or r):               # 시간대 봇은 두 봇이 쉬는 동안만 · 둘 중 하나가 들면 넘겨줌
                holder = "T" if t else "R"; tgt = P[holder][i]
        if tgt != prev:
            want[i] = tgt
            prev = tgt
    return want


res = {}
d13, _ = K.simulate(b, M13.signals(b, M13.grid()[0]))
top13 = set(sorted(d13, key=lambda d: -d13[d])[:10])
for rule in ("first", "trend", "range"):
    for use_w in (0, 1):
        days, tr = K.simulate(b, combine(rule, use_w))
        r = S.report(days, tr)
        r["ex_top13"] = round(sum(v for d, v in days.items() if d not in top13), 1)
        r["worst_d"] = round(min(days.values()), 1)
        res[f"{rule}{'+W' if use_w else ''}"] = r
for k, v in res.items():
    print(k, {x: v[x] for x in ("total", "ex10", "ex_top13", "trades", "pos_m", "worst_m", "worst_d", "mdd")})
both = {}
for nm, f in (("T", M13), ("R", M14), ("W", M15)):
    d, t = K.simulate(b, f.signals(b, f.grid()[0])); both[nm] = d
ds = sorted(both["T"])
both_ov = sum(1 for i in range(len(b)) if P["T"][i] and P["R"][i])
print("두 봇이 같은 봉에 함께 자리 원함:", both_ov, "봉 /", sum(1 for i in range(len(b)) if P["T"][i] or P["R"][i]), "봉")
print("따로 두 계약 합(비교):", round(sum(both["T"][d] + both["R"][d] for d in ds), 1))
json.dump(res, open(Path(__file__).parent / "one_lab.json", "w"), ensure_ascii=False)
