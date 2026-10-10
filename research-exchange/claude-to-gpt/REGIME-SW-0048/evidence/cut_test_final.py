"""결과 제출용 추가 자르기 시험(GPT #211 6098402467 요청) — 코드는 바꾸지 않고 regime_dev.account를 그대로 부름.
최종 설정 + 새 확인 조건(r5m3 · r10m5 · sbr30) + exit_buf > 0을 실제로 쓰는 설정들을, 온 자료와 2022-06-15에서 자른 자료로 돌려 그 앞 국면 · NAV가 같은지."""
import json, sys
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D
FINAL = {"n": 20, "confirm": "br30", "persist": 3, "down_base": 1.0, "down_inv": 0.0, "inv": "114800", "up_lev": 0.3, "side_inv": 0.0, "up_need": "above_only", "exit_buf": 0.0}
cfgs = [FINAL,
        dict(D.R0, confirm="r5m3", down_base=0.5, down_inv=0.5, up_lev=0.3, exit_buf=0.02),
        dict(D.R0, n=60, confirm="r10m5", persist=5, down_base=0.0, down_inv=0.5, inv="252670", exit_buf=0.05),
        dict(D.R0, n=120, confirm="sbr30", persist=3, down_base=0.5, down_inv=0.3, up_lev=0.6, side_inv=0.2, exit_buf=0.05)]
full = [D.account(c) for c in cfgs]
D.CUT, D.SNAP, D.DATA, D.FEAT = "20220615", "/tmp/reg-cut.pkl", None, None
part = [D.account(c) for c in cfgs]
n, bad, used = 0, [], []
for (fa, sa), (pa, ps) in zip(full, part):
    used.append(sorted(set(v for d, v in ps.items() if d < D.CUT)))
    for d in pa:
        if d >= D.CUT:
            continue
        n += 1
        if abs(fa[d] - pa[d]) > 1e-12 or sa.get(d) != ps.get(d):
            bad.append(d)
print(json.dumps({"cells_compared": n, "differ": len(bad), "first_bad": bad[:3], "configs": len(cfgs), "states_seen_before_cut": used}, ensure_ascii=False))
