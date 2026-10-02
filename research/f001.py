"""F 1회차 — 투자자별 5일 순매수 힘이 앞으로 5 · 20 · 60일 '시장 넘는 수익'과 어떤 관계인가(하나씩 · 둘씩 · 부호 조합).
힘 = 5일 순매수 ÷ 20일 평균 거래량. 부호: + (힘 > 0.02) · − (힘 < −0.02) · 0(그 사이)."""
import itertools
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import ftools as F

tab = F.build(5)
print(f"== F 1회차: 표 {len(tab['day'])}줄 · 종목 {len(set(tab['code']))} · {min(tab['day'])} ~ {max(tab['day'])} ==", flush=True)
CAT7 = F.CATS + ("프로그램",)
TH = 0.02


def line(mask, name):
    out = [f"  {name:<34}"]
    for hn, hm in F.halves(tab):
        m = mask & hm
        n = int(m.sum())
        vals = [np.nanmean(tab[f'x{h}'][m]) * 100 if n else np.nan for h in F.HS]
        win = np.nanmean(tab["x20"][m] > 0) * 100 if n else np.nan
        out.append(f"| {hn[:1]} 건수 {n:7d} · 넘는수익 5일 {vals[0]:+5.2f} 20일 {vals[1]:+5.2f} 60일 {vals[2]:+5.2f} · 20일 이긴 비율 {win:4.1f}")
    print(" ".join(out), flush=True)


print("\n[1] 하나씩: 힘을 다섯 무리로(1 = 가장 많이 판 쪽, 5 = 가장 많이 산 쪽)", flush=True)
for c in CAT7:
    s = tab[f"s_{c}"]
    ok = ~np.isnan(s)
    qs = np.nanquantile(s, [0.2, 0.4, 0.6, 0.8])
    for q in range(5):
        lo = -np.inf if q == 0 else qs[q - 1]
        hi = np.inf if q == 4 else qs[q]
        line(ok & (s >= lo) & (s < hi), f"{c} 무리 {q + 1}")
print("\n[2] 둘씩: 부호 짝(외국인 · 투신 · 연기금 · 사모 · 프로그램 · 개인)", flush=True)
sg = {c: np.where(np.isnan(tab[f"s_{c}"]), np.nan, np.where(tab[f"s_{c}"] > TH, 1, np.where(tab[f"s_{c}"] < -TH, -1, 0))) for c in CAT7}
for a, b in itertools.combinations(("외국인", "투신", "연기금", "사모", "프로그램", "개인", "기관"), 2):
    for va, vb in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        line((sg[a] == va) & (sg[b] == vb), f"{a}{'+' if va > 0 else '−'} {b}{'+' if vb > 0 else '−'}")
print("\n[3] 부호 조합(외국인 · 투신 · 연기금 · 사모 · 개인, 0 빼고 +/−만) — 앞 · 뒤 모두 20일 넘는수익 큰 순", flush=True)
five = ("외국인", "투신", "연기금", "사모", "개인")
res = []
for pat in itertools.product((1, -1), repeat=5):
    m = np.ones(len(tab["day"]), bool)
    for c, v in zip(five, pat):
        m &= sg[c] == v
    nm = " ".join(f"{c}{'+' if v > 0 else '−'}" for c, v in zip(five, pat))
    got = []
    for hn, hm in F.halves(tab):
        mm = m & hm
        got.append((int(mm.sum()), np.nanmean(tab["x20"][mm]) * 100 if mm.sum() else np.nan))
    if min(g[0] for g in got) >= 300:
        res.append((min(g[1] for g in got), nm, m))
res.sort(key=lambda x: -x[0])
for one in res[:8] + [None] + res[-5:]:
    if one is None:
        print("  …", flush=True)
        continue
    line(one[2], one[1])
print("끝", flush=True)
