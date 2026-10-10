"""REGIME-SW-0050 합성 시험 — −10% 잣대(반올림 전) · 고정 규칙 · 격자 · 앞 결과 그대로 · 고원 이웃."""
import json, os, sys
os.environ["REG_BOX"] = "REGIME-SW-0050"
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D
import regime_rules3 as R3
import regime_rules2 as R2
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
check("1 기록 칸 0050 · 1일봉 장부는 0048 파일", D.BOX.name == "REGIME-SW-0050" and D.BASE_CSV.parent.name == "REGIME-SW-0048")
F49 = {"n": 30, "confirm": "r10m5", "persist": 2, "down_base": 1.0, "down_inv": 0.0, "inv": "114800", "up_lev": 0.8, "side_inv": 0.2, "up_need": "above_only", "exit_buf": 0.0, "lev_vt": 0.25, "band": None}
check("2 고정 규칙 = 0049 최종의 규칙 칸(몫 칸 빼고)", all(R3.RULE[k] == F49[k] for k in R3.RULE))
check("3 몫 격자 = 11 × 7 × 3 = 231", len(R3.LEVS) * len(R3.VTS) * len(R3.SIDES) == 231 and R3.LEVS[0] == 0.30 and R3.LEVS[-1] == 0.80)
r49 = D.stats(*D.account(F49))
check("4 0049 최종 다시 셈 = 40.371%(앞 결과 그대로) · 가장 나쁜 달 −14.887%", abs(r49["annual_pct"] - 40.371) < 1e-9 and abs(r49["worst_month_pct"] + 14.887) < 1e-9)
check("5 0049 최종은 −10% 잣대 밖(달 −14.9%)", not R3.within(r49))
def fake(day, month):
    return {"by_kind": {"상승": {"worst_day_raw": day, "worst_month_raw": month}, "하락": {"worst_day_raw": -0.01, "worst_month_raw": -0.02}, "횡보": {"worst_day_raw": -0.01, "worst_month_raw": -0.02}}}
check("6 잣대는 반올림 전: 달 −0.100000 통과 · −0.1000001 탈락 · 하루 −0.15 통과 · −0.1500001 탈락",
      R3.within(fake(-0.15, -0.10)) and not R3.within(fake(-0.01, -0.1000001)) and not R3.within(fake(-0.1500001, -0.05)))
check("7 by_kind에 반올림 전 칸(worst_day_raw · worst_month_raw)이 있음", all("worst_month_raw" in v for v in r49["by_kind"].values()))
nb = R2.neighbors(dict(F49, lev_vt=0.15))
check("8 고원 이웃은 규칙 숫자만(n 26 · 34 · 버팀 1 · 3 · r10m4 · r10m6 · lev_vt ±0.02) · 몫 축 없음",
      {("n", 26), ("n", 34), ("persist", 1), ("persist", 3), ("confirm", "r10m4"), ("confirm", "r10m6"), ("lev_vt", 0.13), ("lev_vt", 0.17)} <= set(nb)
      and not ({"up_lev", "side_inv", "down_inv", "down_base"} & {a for a, _ in nb}))
check("9 lev_vt가 None이면 그 이웃 없음(꺼진 분기)", not any(a == "lev_vt" for a, _ in R2.neighbors(dict(F49, lev_vt=None))))
print(f"모두 {ok}개 통과")
