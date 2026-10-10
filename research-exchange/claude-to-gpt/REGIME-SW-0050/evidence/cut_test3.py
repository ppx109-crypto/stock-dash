"""REGIME-SW-0050 자르기 시험 — 몫 격자에서 고른 설정 3개를 온 자료와 2022-06-15에서 자른 자료로(코드 안 바꿈)."""
import json, os, sys
os.environ["REG_BOX"] = "REGIME-SW-0050"
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D
import regime_rules3 as R3
cfgs = [dict(D.R0, **R3.RULE, up_lev=a, lev_vt=b, side_inv=c) for a, b, c in ((0.5, 0.15, 0.1), (0.8, None, 0.2), (0.3, 0.10, 0.0))]
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
