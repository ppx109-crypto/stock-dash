"""RNA 횡보장 봇 탐색(전체 자료 · 5분봉 · −25p): 한투 1일봉 RNA의 '이격도 · 이격밴드'를 5분봉에 옮김.
 이격도 disp = 종가 ÷ EMA(L) − 1 · 이격밴드 z = disp가 앞 W봉(그 봉 제외) 평균에서 몇 표준편차인지
 횡보 거름(RNA): gate 'tangle' 배열 꼬임(EMA 4 · 15 · 45 · 90이 정 · 역배열 아님) / 'flat' 90선 3봉 기울기 < f × ATR / 'both'
 들기: z ≥ +k 팖 · z ≤ −k 삼(거름 켜졌을 때만) · 나가기: |z| ≤ e(평균 돌아옴) · 멈춤 s × ATR · 최대 H봉 · 하루 n번
 함께 셈: KMF-0013 추세 봇과 날별 합(같은 1계약씩 · 두 계좌로 봄) · 추세 봇이 잃은 날에 이 봇 손익."""
import sys, json, itertools
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import short_lab as S
sys.path.insert(0, str(S.ROOT / "research"))
import kmf13 as M13
rows, b, B = S.load()
c, h, l, atr = B
d13, _ = S.K.simulate(b, M13.signals(b, M13.grid()[0]))
e4, e15, e45, e90 = (S.E(c, s) for s in (4, 15, 45, 90))
aligned = ((e4 > e15) & (e15 > e45) & (e45 > e90)) | ((e4 < e15) & (e15 < e45) & (e45 < e90))
slope90 = np.r_[np.full(3, np.nan), e90[3:] - e90[:-3]]
ZC = {}


def zband(L, W):
    if (L, W) not in ZC:
        disp = c / S.E(c, L) - 1
        z = np.full(len(c), np.nan)
        cs = np.r_[0, np.nancumsum(disp)]; cs2 = np.r_[0, np.nancumsum(disp ** 2)]
        for i in range(W + L, len(c)):
            mu = (cs[i] - cs[i - W]) / W; var = (cs2[i] - cs2[i - W]) / W - mu * mu
            z[i] = (disp[i] - mu) / np.sqrt(var) if var > 0 else 0.0
        ZC[(L, W)] = z
    return ZC[(L, W)]


def rsig(cfg):
    z = zband(cfg["L"], cfg["W"])
    n = len(b); want = [None] * n; pos = 0; ent = None; cnt = 0; day = None; held = 0
    for i in range(n):
        d, m = b[i][0], b[i][1]
        if d != day:
            day, pos, cnt = d, 0, 0
        if np.isnan(z[i]) or np.isnan(atr[i]) or np.isnan(slope90[i]) or np.isnan(e90[i]):
            continue
        if pos:
            held += 1
            if abs(z[i]) <= cfg["e"] or pos * (c[i] - ent) <= -cfg["s"] * atr[i] or (cfg["H"] and held >= cfg["H"]):
                want[i], pos = 0, 0
            continue
        if m < S.K.ENTRY_FROM or m > S.K.ENTRY_TO or cnt >= cfg["n"]:
            continue
        flat = abs(slope90[i]) < cfg["f"] * atr[i]
        g = {"tangle": not aligned[i], "flat": flat, "both": (not aligned[i]) and flat}[cfg["gate"]]
        if g and abs(z[i]) >= cfg["k"]:
            side = -1 if z[i] > 0 else 1
            want[i], pos, ent, cnt, held = side, side, c[i], cnt + 1, 0
    return want


res = {}
for L, W, gate, f, k, e, s, H in itertools.product((15, 45), (60, 120), ("tangle", "flat", "both"), (0.3, 0.6), (2.0, 2.5, 3.0), (0.0, 0.5), (1.5, 3.0), (0, 12)):
    if gate == "tangle" and f == 0.6:
        continue
    cfg = {"L": L, "W": W, "gate": gate, "f": f, "k": k, "e": e, "s": s, "H": H, "n": 5}
    days, tr = S.K.simulate(b, rsig(cfg))
    r = S.report(days, tr)
    ds = sorted(days)
    r["corr13"] = round(float(np.corrcoef([days[d] for d in ds], [d13[d] for d in ds])[0, 1]), 3)
    r["on13loss"] = round(sum(days[d] for d in ds if d13[d] < 0), 1)
    both = {d: days[d] + d13[d] for d in ds}
    r["with13"] = round(sum(both.values()), 1)
    r["with13_ex10"] = round(sum(sorted(both.values(), reverse=True)[10:]), 1)
    res[json.dumps(cfg)] = r
json.dump(res, open(Path(__file__).parent / "range_r3.json", "w"), ensure_ascii=False)
print("조합", len(res), "· 혼자 합 > 0:", sum(1 for v in res.values() if v["total"] > 0), "· 혼자 ex10 > 0:", sum(1 for v in res.values() if v["ex10"] > 0))
for k_, v in sorted(res.items(), key=lambda kv: (-kv[1]["pos_m"], -kv[1]["total"]))[:20]:
    print(k_, {x: v[x] for x in ("total", "ex10", "trades", "pos_m", "worst_m", "mdd", "corr13", "on13loss", "with13", "with13_ex10")})
