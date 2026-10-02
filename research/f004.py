"""F 4회차 — 기간 · 세기 · 전환 · 엇갈림(그날 시총 100위 · 시장 넘는 수익).
Q_PART=1: 순매수 기간 1 · 3 · 10일의 그날 위 20% / 아래 20%(외국인 · 기관 · 투신 · 연기금 · 개인 · 프로그램)
Q_PART=2: 20 · 60일 같은 것
Q_PART=3: 외국인 · 투신 연속 순매수 날 수(1 · 2 · 3 · 5 · 8 · 13일↑) · 전환(20일 합 −인데 5일 합 +) · 엇갈림(20일 −5% 넘게 빠졌는데 5일 힘 위 20%)"""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import ftools as F

CAT = ("외국인", "기관", "투신", "연기금", "개인", "프로그램")


def daytop(tab, s, q=0.2):
    """같은 날 안 순위로 위 q · 아래 q."""
    top = np.zeros(len(s), bool); bot = np.zeros(len(s), bool)
    days = tab["day"]
    order = np.argsort(days, kind="stable")
    ud, start = np.unique(days[order], return_index=True)
    bounds = list(start) + [len(order)]
    for k in range(len(ud)):
        sl = order[bounds[k]: bounds[k + 1]]
        v = s[sl]
        ok = ~np.isnan(v)
        if ok.sum() < 20:
            continue
        hi, lo = np.nanquantile(v, 1 - q), np.nanquantile(v, q)
        top[sl] = ok & (v >= hi); bot[sl] = ok & (v <= lo)
    return top, bot


part = os.environ.get("Q_PART", "1")
print(f"== F 4회차({part}): 기간 · 세기 · 전환 · 엇갈림 ==", flush=True)
if part in ("1", "2"):
    for n in ((1, 3, 10) if part == "1" else (20, 60)):
        tab = F.pit(F.build(n))
        print(f"\n[{n}일 순매수]", flush=True)
        for c in CAT:
            top, bot = daytop(tab, tab[f"s_{c}"])
            F.show(tab, top, f"{c} {n}일 위 20%", 26)
            F.show(tab, bot, f"{c} {n}일 아래 20%", 26)
else:
    tab = F.pit(F.build(5))
    t20 = F.pit(F.build(20))
    k20 = {(c, d): i for i, (c, d) in enumerate(zip(t20["code"], t20["day"]))}
    idx = np.array([k20.get((c, d), -1) for c, d in zip(tab["code"], tab["day"])])
    for c in ("외국인", "투신"):
        run = tab[f"run_{c}"]
        for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 13), (13, 999)):
            F.show(tab, (run >= lo) & (run < hi), f"{c} 연속 {lo}~{hi - 1 if hi < 999 else '↑'}일", 26)
    for c in ("외국인", "기관", "투신", "연기금", "프로그램"):
        s20 = np.where(idx >= 0, t20[f"s_{c}"][np.maximum(idx, 0)], np.nan)
        turn = (s20 < 0) & (tab[f"s_{c}"] > 0)
        F.show(tab, turn, f"{c} 전환(20일 − · 5일 +)", 26)
        top, _ = daytop(tab, tab[f"s_{c}"])
        F.show(tab, top & (tab["r20"] < -0.05), f"{c} 엇갈림(값 −5%↓ · 힘 위20%)", 26)
        F.show(tab, top & (tab["r20"] > 0.10), f"{c} 같이 감(값 +10%↑ · 힘 위20%)", 26)
print("끝", flush=True)
