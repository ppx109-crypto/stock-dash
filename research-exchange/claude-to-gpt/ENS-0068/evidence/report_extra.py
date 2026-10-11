"""보고 전용(판정 밖) — 7칸의 맞춤 횟수 · 가장 나쁜 완료 달(어느 달) · 앞 반 / 뒤 반 연수익. 잠긴 ens.py를 그대로 불러 셈."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import ens as E  # noqa: E402
D, T = E.D, E.T


def halves(navs):
    ds = sorted(navs); h = len(ds) // 2
    f = lambda a, b: (navs[ds[b]] / navs[ds[a]]) ** (250 / (b - a)) - 1
    return f(0, h), f(h, len(ds) - 1), ds[h]


def months(navs):
    ds = sorted(navs); mo = {}
    for j in range(1, len(ds)):
        mo[ds[j][:6]] = mo.get(ds[j][:6], 1.0) * navs[ds[j]] / navs[ds[j - 1]]
    return {m: v - 1 for m, v in mo.items() if T.FIRST_FULL <= m <= T.LAST_FULL}


rows = []
for name, cfg in E.grid():
    navs = T.full(cfg)
    base, etf, br, flow = D.data()
    st = D.states(D.FEAT[1], cfg)
    ds = [d for d in sorted(navs)]
    ch = sum(1 for j in range(1, len(ds)) if st.get(ds[j - 1]) != st.get(ds[j - 2] if j >= 2 else None) or ds[j][:6] != ds[j - 1][:6])
    a, b, mid = halves(navs)
    mo = months(navs)
    worst = sorted(mo.items(), key=lambda x: x[1])[:3]
    rows.append((name, a, b))
    print(f"{name}: 맞춤(어림 · 표 바뀜 다음 날 + 달 첫날) {ch}번 · 앞 반 연 {a*100:.2f}% · 뒤 반 연 {b*100:.2f}%(나눔 {mid}) · 나쁜 달 "
          + " · ".join(f"{m} {v*100:.2f}%" for m, v in worst))
best = max(rows[1:], key=lambda x: x[1])
print(f"앞 반 가장 높은 칸 = {best[0]}(앞 {best[1]*100:.2f}%) → 뒤 반 {best[2]*100:.2f}% · 기준 뒤 반 {rows[0][2]*100:.2f}%")
