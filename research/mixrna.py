"""시장 상황별 시드 나누기 RNA(docs/RL-MIX-RNA.md) — 세 봇(1일봉 · 1시간봉 · 15분봉) 몫을 산 날의 시장 상황(전 거래일 종가까지)에 따라.
MR_LO / MR_HI · MR_D1 · MR_H1 · MR_M15(scratchpad 무작위 풀 파일) · MR_N(판 수) · MR_G(G1 · G2 · G3 · none)
MR_MODE=climb(고정 MR_START에서 상황마다 차례로: 1바퀴 20% 단위 전부 · 2 · 3바퀴 고른 몫 이웃 10% · 비가 가장 큰 쪽으로) | eval(MR_SPEC '상승:50_0_50,횡보:..,하락:..' 를 잼)
계좌: a_mtm과 같되 산 날 몫만큼 사고(현금보다 많이는 못 삼) 값이 오르내리는 대로 · 판 날 장부 손익에 맞춤. 실제 비용 1일봉 −0.2 · 1시간봉 · 15분봉 −0.15%p."""
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import numpy as np
import itools as I
import nrl

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
LO, HI = os.environ["MR_LO"], os.environ["MR_HI"]
G = os.environ.get("MR_G", "G1")
ALLD = list(I.DAYS); K = np.asarray(I.K200, float); BR = np.asarray(I.breadth(), float)
pos = {d: i for i, d in enumerate(ALLD)}
D = [d for d in ALLD if LO <= d < HI]
nxt = {d: D[i + 1] for i, d in enumerate(D[:-1])}
# 문턱 = 2017 ~ 2022(고르기 · 시험보다 앞)
_m = np.array([("20170101" <= d < "20230101") for d in ALLD])
R60 = np.r_[np.full(60, np.nan), K[60:] / K[:-60] - 1]
MA120 = np.array([np.nanmean(K[max(0, i - 119):i + 1]) if i >= 119 else np.nan for i in range(len(K))])
T1 = np.nanpercentile(R60[_m], [100 / 3, 200 / 3]); T3 = np.nanpercentile(BR[_m], [100 / 3, 200 / 3])


def regime_at(i):
    """날 i의 판단에 쓰는 상황 = 날 i − 1 종가까지."""
    j = i - 1
    if G == "none" or j < 140:
        return "횡보"
    if G == "G1":
        v = R60[j]; return "상승" if v >= T1[1] else "하락" if v <= T1[0] else "횡보"
    if G == "G2":
        up = K[j] > MA120[j] and MA120[j] > MA120[j - 20]; dn = K[j] < MA120[j] and MA120[j] < MA120[j - 20]
        return "상승" if up else "하락" if dn else "횡보"
    v = BR[j]; return "상승" if v >= T3[1] else "하락" if v <= T3[0] else "횡보"


REG = {d: regime_at(pos[d]) for d in D}
SRC = [(json.load(open(SP + os.environ[k])), extra) for k, extra in (("MR_D1", 0.2), ("MR_H1", 0.15), ("MR_M15", 0.15))]
N = min([int(os.environ.get("MR_N", "100"))] + [len(j["판"]) for j, _ in SRC])
idx = {d: i for i, d in enumerate(D)}


def led(s, i):
    j, extra = SRC[s]
    return [(c, b, nxt.get(e, e) if e == b else e, p - extra, k) for c, b, e, p, k in j["판"][i]["장부"] if LO <= b < HI and e in idx and b in idx]


LED = [[led(s, i) for i in range(N)] for s in range(3)]
PX = {}
for s in range(3):
    for i in range(N):
        for c, *_ in LED[s][i]:
            if c not in PX:
                PX[c] = dict(nrl.prices.get(c, {}).get("rows") or [])
n = len(D)


def run(spec, i):
    """spec: {상황: (a, b, c)} → 판 i의 (해마다 수익, 되돌림 뺀 골, 비)."""
    L = []
    for s in range(3):
        for c, b, e, p, k in LED[s][i]:
            sh = spec[REG[b]][s]
            if sh:
                L.append((c, b, e, p, k * sh / 100))
    L.sort(key=lambda x: x[1])
    buys, sells = {}, {}
    for t, (c, b, e, p, k) in enumerate(L):
        buys.setdefault(idx[b], []).append(t); sells.setdefault(idx[e], []).append(t)
    E = np.ones(n); C = np.ones(n); val, last, units = {}, {}, {}
    cash = 1.0
    for d in range(1, n):
        for t in list(val):
            v = PX[L[t][0]].get(D[d])
            if v:
                val[t] *= v / last[t]; last[t] = v
        for t in sells.get(d, []):
            if t in val:
                cash += units[t] * (1 + L[t][3] / 100); val.pop(t)
        eq = cash + sum(val.values())
        for t in buys.get(d, []):
            c, b, e, p, k = L[t]; v = PX[c].get(D[d])
            if v and idx[e] > d:
                u = min(eq * k / 10, max(cash, 0.0))       # 현금보다 많이는 못 삼
                if u > 0:
                    units[t] = u; val[t] = u; last[t] = v; cash -= u
        E[d] = cash + sum(val.values())
        C[d] = E[d] - sum(max(0.0, val[t] - units[t]) for t in val)
    yrs = n / 250
    ann = (E[-1] ** (1 / yrs) - 1) * 100
    dd = (C / np.maximum.accumulate(C) - 1).min() * 100
    return ann, dd, ann / max(abs(dd), 1e-9)


def score(spec, n_=None):
    a = np.array([run(spec, i) for i in range(n_ or N)])
    return float(np.median(a[:, 2])), float(np.median(a[:, 0])), float(np.median(a[:, 1])), float(np.percentile(a[:, 0], 10))


def fmt(spec):
    return " · ".join(f"{r} {'·'.join(map(str, spec[r]))}" for r in ("상승", "횡보", "하락"))


GRID = [(a, b, 100 - a - b) for a in range(0, 101, 10) for b in range(0, 101 - a, 10)]
days = {r: sum(1 for d in D if REG[d] == r) for r in ("상승", "횡보", "하락")}
print(f"== {G} · {LO} ~ {HI} · {N}판 · 상황별 날 수 {days} ==", flush=True)
mode = os.environ.get("MR_MODE", "climb")
if mode == "eval":
    spec = {kv.split(":")[0]: tuple(int(x) for x in kv.split(":")[1].split("_")) for kv in os.environ["MR_SPEC"].split(",")}
    s = score(spec)
    print(f"  {fmt(spec)} → 비 {s[0]:.2f} · 해마다 {s[1]:+.1f} · 되돌림 뺀 골 {s[2]:.1f} · 아래10% {s[3]:+.1f}", flush=True)
else:
    st = tuple(int(x) for x in os.environ.get("MR_START", "50_0_50").split("_"))
    spec = {r: st for r in ("상승", "횡보", "하락")}
    best = score(spec); tried = 1
    print(f"  시작(고정 {'·'.join(map(str, st))}) 비 {best[0]:.2f} · 해마다 {best[1]:+.1f} · 골 {best[2]:.1f}", flush=True)
    GRID20 = [(a, b, 100 - a - b) for a in range(0, 101, 20) for b in range(0, 101 - a, 20)]
    nb_of = lambda g: [q for q in ((g[0] + x, g[1] + y, g[2] - x - y) for x, y in ((10, 0), (-10, 0), (0, 10), (0, -10), (10, -10), (-10, 10))) if min(q) >= 0]
    for rnd, grid_of in ((1, lambda r: GRID20), (2, lambda r: nb_of(spec[r])), (3, lambda r: nb_of(spec[r]))):
        for r in ("상승", "횡보", "하락"):
            if G == "none" and r != "횡보":
                continue
            res = {spec[r]: best}
            for g in grid_of(r):
                if g not in res:
                    res[g] = score(dict(spec, **{r: g})); tried += 1
            g = max(res, key=lambda x: res[x][0])
            if res[g][0] > best[0]:
                spec[r], best = g, res[g]
            nbv = [res[q][0] for q in nb_of(spec[r]) if q in res]
            print(f"  {rnd}바퀴 {r}: {'·'.join(map(str, spec[r]))} 비 {best[0]:.2f} · 해마다 {best[1]:+.1f} · 골 {best[2]:.1f}"
                  + (f" · 이웃 비 {min(nbv):.2f} ~ {max(nbv):.2f}" if nbv else ""), flush=True)
    json.dump({r: list(v) for r, v in spec.items()}, open(SP + f"mixrna_{G}.json", "w"))
    print(f"== {G} 고른 몫: {fmt(spec)} · 비 {best[0]:.2f} · 해마다 {best[1]:+.1f} · 골 {best[2]:.1f} · 아래10% {best[3]:+.1f} · 시험한 판 수 {tried}", flush=True)
