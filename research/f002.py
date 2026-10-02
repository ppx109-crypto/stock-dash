"""F 2회차 — f001을 '그날 시총 100위 안'(미래 정보 없음)으로 다시. 시장 = 그날 100위 평균.
[1] 하나씩 다섯 무리 [2] 둘씩 부호 짝 [3] 다섯 투자자 부호 조합 위 · 아래 [4] 같은 날 100종목 안 순위(힘 위 20%)."""
import itertools
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import ftools as F

tab = F.pit(F.build(5))
print(f"== F 2회차(그날 시총 100위 안): {len(tab['day'])}줄 · 종목 {len(set(tab['code']))} ==", flush=True)
CAT7 = F.CATS + ("프로그램",)
TH = 0.02
print("\n[0] 모두", flush=True)
F.show(tab, np.ones(len(tab["day"]), bool), "모두")
print("\n[1] 하나씩 다섯 무리(1 = 가장 많이 판 쪽 … 5 = 가장 많이 산 쪽)", flush=True)
for c in CAT7:
    s = tab[f"s_{c}"]
    ok = ~np.isnan(s)
    qs = np.nanquantile(s, [0.2, 0.4, 0.6, 0.8])
    for q in range(5):
        lo = -np.inf if q == 0 else qs[q - 1]
        hi = np.inf if q == 4 else qs[q]
        F.show(tab, ok & (s >= lo) & (s < hi), f"{c} 무리 {q + 1}")
sg = {c: np.where(np.isnan(tab[f"s_{c}"]), np.nan, np.where(tab[f"s_{c}"] > TH, 1, np.where(tab[f"s_{c}"] < -TH, -1, 0))) for c in CAT7}
print("\n[2] 둘씩 부호 짝", flush=True)
for a, b in itertools.combinations(("외국인", "투신", "연기금", "사모", "프로그램", "개인", "기관"), 2):
    for va, vb in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        F.show(tab, (sg[a] == va) & (sg[b] == vb), f"{a}{'+' if va > 0 else '−'} {b}{'+' if vb > 0 else '−'}")
print("\n[3] 다섯 투자자(외국인 · 투신 · 연기금 · 사모 · 개인) 부호 조합 — 두 반 가운데 작은 20일 값 순 위 8 · 아래 5 (두 반 모두 200건 넘는 것)", flush=True)
five = ("외국인", "투신", "연기금", "사모", "개인")
res = []
for pat in itertools.product((1, -1), repeat=5):
    m = np.ones(len(tab["day"]), bool)
    for c, v in zip(five, pat):
        m &= sg[c] == v
    got = [(int((m & hm).sum()), np.nanmean(tab["x20"][m & hm]) * 100 if (m & hm).sum() else np.nan) for _, hm in F.halves(tab)]
    if min(g[0] for g in got) >= 200:
        res.append((min(g[1] for g in got), " ".join(f"{c}{'+' if v > 0 else '−'}" for c, v in zip(five, pat)), m))
res.sort(key=lambda x: -x[0])
for one in res[:8] + [None] + res[-5:]:
    if one is None:
        print("  …", flush=True)
    else:
        F.show(tab, one[2], one[1], 40)
print("\n[4] 같은 날 100종목 안에서 힘 위 20% · 아래 20%", flush=True)
days = tab["day"]
for c in CAT7:
    s = tab[f"s_{c}"]
    top = np.zeros(len(s), bool); bot = np.zeros(len(s), bool)
    order = np.argsort(days, kind="stable")
    ud, start = np.unique(days[order], return_index=True)
    bounds = list(start) + [len(order)]
    for k in range(len(ud)):
        sl = order[bounds[k]: bounds[k + 1]]
        v = s[sl]
        ok = ~np.isnan(v)
        if ok.sum() < 20:
            continue
        hi, lo = np.nanquantile(v, 0.8), np.nanquantile(v, 0.2)
        top[sl] = ok & (v >= hi); bot[sl] = ok & (v <= lo)
    F.show(tab, top, f"{c} 그날 위 20%")
    F.show(tab, bot, f"{c} 그날 아래 20%")
print("끝", flush=True)
