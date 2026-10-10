"""REGIME-SW-0052 합성 시험 — 격자 · 고정 규칙 · 기록 칸 · 0051 최종이 격자 안에 있음."""
import os, sys
os.environ["REG_BOX"] = "REGIME-SW-0052"
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_rules5 as R5
R = R5.R4
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
check("1 기록 칸 0052", R.D.BOX.name == "REGIME-SW-0052" and R.LOG.parent.name == "REGIME-SW-0052")
check("2 격자 = n 24 × 버팀 3 × 레버리지 3 × 횡보 인버스 6 = 18", R.NS == [24] and R.PS == [3] and len(R.LEVS) * len(R.SIDES) == 18)
check("3 고정 규칙 = 0051(r10m5 · above_only · band / lev_vt 없음 · 하락 1일봉만)", R.FIXED["confirm"] == "r10m5" and R.FIXED["lev_vt"] is None and R.FIXED["down_base"] == 1.0)
check("4 0051 최종(레버리지 0.20 · 횡보 0.2)과 횡보 0이 격자 안", 0.20 in R.LEVS and 0.2 in R.SIDES and 0.0 in R.SIDES)
check("5 이웃 = n 20 · 28 · 버팀 2 · 4 · r10m4 · r10m6", R.neighbors({"n": 24, "persist": 3}) == [("n", 20), ("n", 28), ("persist", 2), ("persist", 4), ("confirm", "r10m4"), ("confirm", "r10m6")])
r0 = R.D.stats(*R.D.account(dict(R.D.R0, **R.FIXED, n=24, persist=3, up_lev=0.2, side_inv=0.2)))
check("6 0051 최종 다시 셈 = 27.129% · 달 −8.567%", abs(r0["annual_pct"] - 27.129) < 1e-9 and abs(r0["worst_month_pct"] + 8.567) < 1e-9)
print(f"모두 {ok}개 통과")
