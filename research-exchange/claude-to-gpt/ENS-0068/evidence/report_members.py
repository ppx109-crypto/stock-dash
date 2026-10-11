"""보고 전용(판정 밖 · 결과 뒤 진단) — 구성원 15개를 하나씩(지금 판 몫 L0.4 · S0.4) 돌린 계좌 전체 연수익 · 가장 나쁜 완료 달 · 2026-03."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import ens as E  # noqa: E402
T = E.T
for n in E.N_SET:
    for p in E.P_SET:
        navs = T.full(dict(E.FINAL, n=n, persist=p))
        s = T.stats(navs)
        ds = sorted(navs); mar = 1.0
        for j in range(1, len(ds)):
            if ds[j][:6] == "202603":
                mar *= navs[ds[j]] / navs[ds[j - 1]]
        print(f"n {n} · persist {p}: 연 {s['annual_pct']:.3f}% · 가장 나쁜 달 {s['worst_full_month_pct']:.3f}% · 2026-03 {100*(mar-1):.2f}% · 손실 달 {s['loss_months']}")
