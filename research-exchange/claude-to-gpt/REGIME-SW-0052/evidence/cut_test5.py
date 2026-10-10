"""REGIME-SW-0052 자르기 시험 — 횡보 인버스 0.5 · 0.3 설정을 온 자료와 2022-06-15에서 자른 자료로(코드 안 바꿈)."""
import json, os, sys
os.environ["REG_BOX"] = "REGIME-SW-0052"
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_rules5 as R5
R = R5.R4; D = R.D
cfgs = [dict(D.R0, **R.FIXED, n=24, persist=3, up_lev=a, side_inv=b) for a, b in ((0.25, 0.5), (0.15, 0.3))]
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
