"""체결 늦음 · 비용 견딤(판정 밖): 5분봉 신호를 1분봉에서 0 ~ 5분 늦게 · 편도 0.08p."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf14 as M
rows = K._rows_before(M.END); b = M.prep(rows); w = M.signals(b, M.grid()[0])
idx = {(r[0], r[1]): i for i, r in enumerate(rows)}
for delay in (0, 1, 2, 3, 5):
    w1 = [None] * len(rows)
    for i, x in enumerate(w):
        if x is None or (x in (1, -1) and b[i][1] < K.ENTRY_FROM):
            continue
        j = idx.get((b[i][0], b[i][1] + delay))
        if j is not None:
            w1[j] = x
    d, t = K.simulate(rows, w1)
    print(f"{delay}분 늦게 합 {sum(d.values()):+.1f} 거래 {len(t)}")
K.COST = 0.08
d, t = K.simulate(b, w)
print(f"비용 2배(편도 0.08) 합 {sum(d.values()):+.1f}")
