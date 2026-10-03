"""RNA 10라운드 — D11 인버스 매매 하나하나: DNA(±1.5%) vs RNA(0.28 × 229200 앞 60일 σ × √10) 어디서 갈리나.
15:15 문턱(9.5%) · 인버스만 따로(계좌 전부). 같은 날 산 매매끼리 짝지어 손익 차이 · 해마다 · 익절이 넓어져 번 것 / 좁아져 잃은 것."""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D = I.DAYS
TH = float(os.environ.get("I_QTH", 0.095))
qq = I.px("229200")
I.px("251340")
sig = np.nan_to_num(I.ret(qq, 10), nan=0) >= TH
s = I.sigma_n(qq, 60) * 0.28 * np.sqrt(10)
dt, _ = I.sim(sig, "251340", -0.015, 0.015, 10)
rt, _ = I.sim_var(sig, "251340", -s, s, 10)
dm = {a: (b, r) for a, b, r in dt}
rm = {a: (b, r) for a, b, r in rt}
print(f"== RNA 10라운드: 인버스 매매 짝짓기(문턱 {TH:.1%}) · DNA {len(dt)}건 · RNA {len(rt)}건 · 같은 날 산 것 {len(set(dm) & set(rm))}건 ==")
wide = narrow = 0.0
rows = []
for a in sorted(set(dm) | set(rm)):
    db, dr = dm.get(a, (None, 0.0))
    rb, rr = rm.get(a, (None, 0.0))
    w = s[a] * 100
    diff = (rr - dr) * 100
    if abs(diff) > 0.05:
        rows.append((D[a], w, dr * 100 if a in dm else None, rr * 100 if a in rm else None, diff))
    if w > 1.5:
        wide += diff
    else:
        narrow += diff
print("  산 날      RNA 폭  DNA 손익  RNA 손익  차이")
for d, w, dr, rr, df in rows:
    f = lambda x: f"{x:+7.2f}" if x is not None else "   없음"
    print(f"  {d}  {w:5.2f}%  {f(dr)}  {f(rr)}  {df:+6.2f}")
print(f"  갈린 매매 {len(rows)}건 · RNA 폭 > 1.5%(넓어짐) 합 {wide:+.2f}%p · ≤ 1.5%(좁아짐) 합 {narrow:+.2f}%p")
print(f"  RNA 폭이 1.5%보다 넓은 매매 {np.mean([s[a] > 0.015 for a in rm]) * 100:.0f}%")
