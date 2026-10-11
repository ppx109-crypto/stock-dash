# 보고 전용(판정 밖): 1일봉 0.3 바탕에서 새 봇이 실제로 쓴 평균 몫(XASSET-0060 report_share.py와 같은 방법 · 잠긴 실행기와 NAV 같음 확인)
import sys, os, inspect, textwrap
sys.path.insert(0, 'research'); os.environ["REG_BOX"] = "XROOM-0061-report"
import xroom as R, xasset as X
src = textwrap.dedent(inspect.getsource(X.account_x))
src = src.replace("def account_x(", "def account_r(").replace("        nst[d] = s_prev\n", "        nst[d] = s_prev\n        SH.append(sum(sv.values()) / navs[d] if navs[d] > 0 else 0.0)\n")
src = src.replace("account_x.trims, account_x.base_trims, account_x.sleeve_trims, account_x.min_slack", "account_r.t1, account_r.t2, account_r.t3, account_r.ms")
g = dict(X.__dict__); exec(src, g); acc = g["account_r"]
R.use_base("d0.3")
for sl in ({"u": "U3", "n": 10, "w": 0.2}, {"u": "U3", "n": 10, "w": 0.3}, {"u": "U3", "n": 10, "w": 0.4}):
    g["SH"] = []; navs, _ = acc(dict(X.FINAL, sleeve=sl)); sh = g["SH"]
    full, _ = R.run_cfg({"base": "d0.3", "sleeve": sl})
    assert navs == full
    print(sl, "평균 몫 %", round(sum(sh) / len(sh) * 100, 2), "· 0인 날 %", round(sum(1 for x in sh if x < 1e-9) / len(sh) * 100, 1))
