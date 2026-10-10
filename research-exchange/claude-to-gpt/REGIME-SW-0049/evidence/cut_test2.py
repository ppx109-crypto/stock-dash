"""REGIME-SW-0049 자르기 시험 — 흔들림 몫(lev_vt) · band 다시 맞춤을 쓰는 설정 4개를 온 자료와 2022-06-15에서 자른 자료로 → 그 앞 국면 · NAV가 같은지(round 2: n 10 · 17 · 23 · 40 이동평균이 실제로 계산되는 상태 · 새 문턱 이름 포함 · 코드 안 바꿈)."""
import json, os, sys
os.environ["REG_BOX"] = "REGIME-SW-0049"
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D
S = {"n": 20, "confirm": "br30", "persist": 3, "down_base": 1.0, "down_inv": 0.0, "inv": "114800", "up_lev": 0.6, "side_inv": 0.0, "up_need": "above_only", "exit_buf": 0.0, "lev_vt": 0.15, "band": 0.05}
cfgs = [S, dict(S, lev_vt=0.10, band=0.10, up_lev=0.8), dict(S, n=40, persist=2, lev_vt=0.25, band=None, side_inv=0.1),
        dict(S, n=10, confirm="r5m3", lev_vt=0.125, down_inv=0.3, down_base=0.5),
        dict(S, n=17, confirm="br25", persist=4, lev_vt=0.13, band=0.03), dict(S, n=23, confirm="r5m2.5", exit_buf=0.01, band=0.07, up_need="ma_rising")]
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
