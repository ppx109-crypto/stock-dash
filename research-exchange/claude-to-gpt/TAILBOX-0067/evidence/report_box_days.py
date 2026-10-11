"""보고 전용(판정 밖) — 나 6칸의 '박스' 날 비율. 잠긴 tailbox.py를 그대로 불러 국면만 셉니다(성과 셈 없음)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import tailbox as T  # noqa: E402
D = T.D
T.full(T.FINAL)                                  # 자료 · 바탕 읽기
base, etf, br, flow = D.data()
if D.FEAT is None or D.FEAT[0] is not D.DATA:
    D.FEAT = (D.DATA, D.features(etf, br, flow, D.short_breadth() if br else {}))
feat = D.FEAT[1]
spans = {"dev": ("20100301", "20161231"), "full": ("20170201", "20260915")}
st0 = D.states(feat, T.FINAL)
for n in T.ER_N:
    for thr in T.ER_THR:
        cfg = dict(T.FINAL, box={"n": n, "thr": thr})
        st = D.states(feat, cfg)
        out = []
        for k, (lo, hi) in spans.items():
            ds = [d for d in st if lo <= d <= hi]
            upside = [d for d in ds if st0.get(d) in ("상승", "횡보")]
            bx = [d for d in ds if st[d] == "박스"]
            out.append(f"{k}: 박스 {len(bx)}/{len(ds)}일 = {100*len(bx)/len(ds):.1f}% · 상승 · 횡보 날 중 {100*len(bx)/max(1,len(upside)):.1f}%")
        print(f"ER{n}_{thr}", " | ".join(out))
