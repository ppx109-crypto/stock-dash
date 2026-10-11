# 보고 전용(판정 밖 · GPT #245 지적으로 증거에 더함): 새 봇이 실제로 쓴 평균 몫. account_x 원문에 날마다 몫 집계 한 줄을 넣은 사본으로 다시 셈(잠긴 실행기는 그대로 · NAV 같음 확인)
import sys, os, inspect, textwrap
sys.path.insert(0, 'research'); os.environ["REG_BOX"] = "XASSET-0060-report"
import xasset as X, mix54_run as M, regime_dev as D
src = textwrap.dedent(inspect.getsource(X.account_x))
src = src.replace("def account_x(", "def account_r(").replace("        nst[d] = s_prev\n", "        nst[d] = s_prev\n        SH.append(sum(sv.values()) / navs[d] if navs[d] > 0 else 0.0)\n")
src = src.replace("account_x.trims, account_x.base_trims, account_x.sleeve_trims, account_x.min_slack", "account_r.t1, account_r.t2, account_r.t3, account_r.ms")
g = dict(X.__dict__); exec(src, g); acc = g["account_r"]
D.BASE_CSV = M.BASES / f"{M.name(X.BASE)}.csv"; D.DATA, D.FEAT = None, None
for sl in ({"u": "U3", "n": 10, "w": 0.1}, {"u": "U3", "n": 10, "w": 0.2}, {"u": "U4", "n": 10, "w": 0.3}):
    g["SH"] = []; navs, _ = acc(dict(X.FINAL, sleeve=sl)); sh = g["SH"]
    full, _ = X.account_x(dict(X.FINAL, sleeve=sl))
    assert navs == full
    print(sl, "평균 몫 %", round(sum(sh) / len(sh) * 100, 2), "· 0인 날 %", round(sum(1 for x in sh if x < 1e-9) / len(sh) * 100, 1), "· 몫 > 0인 날 평균 %", round(sum(x for x in sh if x > 1e-9) / max(1, sum(1 for x in sh if x > 1e-9)) * 100, 2))
