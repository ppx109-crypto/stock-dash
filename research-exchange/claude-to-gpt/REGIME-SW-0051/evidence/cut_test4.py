"""REGIME-SW-0051 자르기 시험 — 격자 설정 3개를 온 자료와 2022-06-15에서 자른 자료로(코드 안 바꿈)."""
import json, os, sys
os.environ["REG_BOX"] = "REGIME-SW-0051"
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D
import regime_rules4 as R
cfgs = [dict(D.R0, **R.FIXED, n=a, persist=b, up_lev=c, side_inv=e) for a, b, c, e in ((24, 1, 0.10, 0.0), (40, 3, 0.25, 0.2), (28, 2, 0.15, 0.2))]
full = [D.account(c) for c in cfgs]
D.CUT, D.SNAP, D.DATA, D.FEAT = "20220615", "/tmp/reg-cut.pkl", None, None
part = [D.account(c) for c in cfgs]
n, bad = 0, []
for (fa, sa), (pa, ps) in zip(full, part):
    for d in pa:
        if d < D.CUT:
            n += 1
            if abs(fa[d] - pa[d]) > 1e-12 or sa.get(d) != ps.get(d):
                bad.append(d)
print(json.dumps({"cells_compared": n, "differ": len(bad), "first_bad": bad[:3], "configs": len(cfgs)}, ensure_ascii=False))
