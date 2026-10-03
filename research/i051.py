"""RNA 23라운드 — D11 인버스 RNA(0.28 × σ60 × √10)의 이익이 운인지: 같은 날 산 매매 짝의 손익 차이를 되뽑기.
① 매매 짝 되뽑기 1,000번(차이 평균 > 0 확률) ② 해 묶음 되뽑기(해 통째로 뽑음 · 1,000번) ③ 2026 두 매매(03-18 · 08-10) 뺀 뒤.
15:15 문턱 9.5% · 인버스만(i049와 같은 매매)."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D = I.DAYS
qq = I.px("229200")
I.px("251340")
sig = np.nan_to_num(I.ret(qq, 10), nan=0) >= 0.095
s = I.sigma_n(qq, 60) * 0.28 * np.sqrt(10)
dt, _ = I.sim(sig, "251340", -0.015, 0.015, 10)
rt, _ = I.sim_var(sig, "251340", -s, s, 10)
dm, rm = {a: r for a, b, r in dt}, {a: r for a, b, r in rt}
keys = sorted(set(dm) | set(rm))
diff = np.array([(rm.get(a, 0.0) - dm.get(a, 0.0)) * 100 for a in keys])
year = np.array([D[a][:4] for a in keys])
rng = np.random.default_rng(7)
N = 1000


def boot(x, yr=None):
    if yr is None:
        m = np.array([rng.choice(x, len(x)).sum() for _ in range(N)])
    else:
        ys = sorted(set(yr))
        by = {y: x[yr == y].sum() for y in ys}
        m = np.array([sum(by[y] for y in rng.choice(ys, len(ys))) for _ in range(N)])
    return (m > 0).mean() * 100, np.percentile(m, 5), np.percentile(m, 50)


print(f"== RNA 23라운드: 인버스 RNA 되뽑기(매매 짝 {len(keys)} · 갈린 것 {int((np.abs(diff) > 0.05).sum())} · 차이 합 {diff.sum():+.2f}%p) ==")
for name, mask in (("전부", np.ones(len(keys), bool)),
                   ("2026 두 매매 뺌", ~np.isin([D[a] for a in keys], ["20260318", "20260810"])),
                   ("2026 통째로 뺌", year < "2026")):
    x, y = diff[mask], year[mask]
    p1, lo1, md1 = boot(x)
    p2, lo2, md2 = boot(x, y)
    print(f"  {name:12s} 차이 합 {x.sum():+6.2f}%p | 매매 되뽑기: 이길 확률 {p1:4.1f}% · 아래 5% {lo1:+.2f} · 가운데 {md1:+.2f} | 해 묶음: {p2:4.1f}% · 아래 5% {lo2:+.2f}")
