"""PHASE-SWITCH-0046 합성 시험 — 고르기 · 합치기 · 판정 · 영수증 순서."""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/home/user/stock-dash/research")
import phase_switch as P
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
real = json.loads(P.MAP_RESULT.read_text())["map"]
check("1 SIG-MAP 결과에서 기계적으로 고르면 오름 S8 · 횡보 S7 · 내림 S2", P.pick_from_map(real) == P.WANT)
check("2 고르는 풀에 수급 S5 · S6 없음", not ({"S5_FLOW_FT10", "S6_RETAIL_CONTRA10"} & set(P.POOL)))
fake = {k: {"phase_pct": {"오름": 0.1, "횡보": 0.1, "내림": 0.1}} for k in P.POOL}
check("3 모두 같으면 풀 앞(S1)", set(P.pick_from_map(fake).values()) == {"S1_MOM20"})
res = {"S2_REV5": {"20220103": (0.02, "내림"), "20220104": (0.5, "오름"), "20230105": (0.01, "횡보")},
       "S7_EMA_ALIGN": {"20220103": (-0.03, "내림"), "20220104": (0.9, "오름"), "20230105": (0.004, "횡보")},
       "S8_MOM120_SKIP20": {"20220103": (-0.05, "내림"), "20220104": (0.006, "오름")}}
c = P.combine(res, P.WANT)
check("4 그날 국면의 신호 값만 씀", c["20220103"] == (0.02, "내림", "S2_REV5") and c["20220104"] == (0.006, "오름", "S8_MOM120_SKIP20") and c["20230105"] == (0.004, "횡보", "S7_EMA_ALIGN"))
res2 = dict(res); res2["S7_EMA_ALIGN"] = {k: v for k, v in res["S7_EMA_ALIGN"].items() if k != "20230105"}
check("5 그날 쓸 신호 값이 없으면 그날 뺌", "20230105" not in P.combine(res2, P.WANT))
PH = ("오름", "횡보", "내림")
def days_of(y):            # 해마다 국면마다 12날(5해 × 12 = 60날 · 문턱 딱 맞음)
    return [(f"{y}{m:02d}{k + 1:02d}", PH[(m - 1) % 3]) for m in range(1, 13) for k in range(3)]
def mk(vals):
    return {d: (v, ph, "S7_EMA_ALIGN") for y, v in vals.items() for d, ph in days_of(y)}
def mkb(v):
    return {d: (v, ph) for y in P.YEARS for d, ph in days_of(y)}
j = P.judge(mk({"2022": 0.01, "2023": 0.01, "2024": -0.01, "2025": 0.01, "2026": -0.01}), mkb(0.0))
check("6 평균 + · 3/5해 + · S7 늘 판보다 큼 → 통과", j["verdict"] == "PHASE_SWITCH_IN_REUSED_T" and j["years_pos"] == "3/5")
j = P.judge(mk({"2022": 0.05, "2023": 0.01, "2024": -0.01, "2025": -0.01, "2026": -0.01}), mkb(0.0))
check("7 2/5해만 + → 탈락(조건 ②)", j["verdict"] == "PHASE_SWITCH_REJECTED" and j["c1_mean_gt0"] and not j["c2_years_ge_3"])
j = P.judge(mk({y: 0.01 for y in P.YEARS}), mkb(0.02))
check("8 S7 늘 판보다 작으면 탈락(조건 ③)", j["verdict"] == "PHASE_SWITCH_REJECTED" and not j["c3_beats_always_S7"])
j = P.judge(mk({y: -0.01 for y in P.YEARS}), mkb(-0.02))
check("9 평균 − → 탈락(조건 ①)", not j["c1_mean_gt0"] and j["verdict"] == "PHASE_SWITCH_REJECTED")
# round 2(GPT #205 6096936274)
c60 = mk({y: 0.01 for y in P.YEARS})
check("16 국면마다 60날이면 판정함(문턱 딱 맞음)", P.judge(c60, mkb(0.0))["c0_phase_days_ge_60"] and P.judge(c60, mkb(0.0))["verdict"] == "PHASE_SWITCH_IN_REUSED_T")
c59 = dict(c60); c59.pop(next(d for d, (v, ph, _) in c60.items() if ph == "내림"))
j = P.judge(c59, mkb(0.0))
check("17 한 국면이라도 59날이면 ① ② ③과 관계없이 NEEDS_DATA", j["verdict"] == "NEEDS_DATA" and j["phase_days"]["내림"] == 59 and j["c1_mean_gt0"])
j1 = P.judge(c60, mkb(0.0)); j2 = P.judge(c60, mkb(0.0))
check("18 구간 칸 · 보고 전용 · 달 단위 2,000번 · 씨앗 46 · 같은 입력 같은 값", j1["ci_use"] == "보고 전용(판정 밖)" and j1["boot"] == {"unit": "달", "reps": 2000, "seed": 46}
      and j1["switch_mean_ci95_pct"] == j2["switch_mean_ci95_pct"] == [1.0, 1.0])
check("19 같은 날 차 구간: 늘 0.01 − 0.0 → [1.0, 1.0]%", j1["paired_switch_minus_S7_ci95_pct"] == [1.0, 1.0])
base_half = {d: v for k, (d, v) in enumerate(sorted(mkb(0.02).items())) if k % 2 == 0}
j = P.judge(c60, base_half)
check("20 차 구간은 S7 값이 있는 같은 날만(0.01 − 0.02 → [−1.0, −1.0]%) · 판정 ③도 같은 날", j["same_days"] == len(base_half) and j["paired_switch_minus_S7_ci95_pct"] == [-1.0, -1.0] and not j["c3_beats_always_S7"])
cvar = {d: ((0.03 if d[4:6] in ("01", "02", "03") else -0.005), ph, s_) for d, (v, ph, s_) in c60.items()}
j = P.judge(cvar, mkb(0.0))
lo, hi = j["switch_mean_ci95_pct"]
check("21 값이 흔들리면 구간이 평균을 감쌈 · 판정은 구간을 안 씀", lo < j["mean_pct"] < hi and j["verdict"] == "PHASE_SWITCH_IN_REUSED_T")
tmp = Path(tempfile.mkdtemp())
P.LOCK = tmp / "l.json"; P.RECEIPT = tmp / "r.json"
P.LOCK.write_text(json.dumps({"x": "다름"}))
try:
    P.run_t(); why = ""
except SystemExit as e:
    why = str(e)
check("10 잠금이 다르면 셈 전에 멈춤 · 영수증 없음", "잠금이 다름" in why and not P.RECEIPT.exists())
P.LOCK.write_text(json.dumps(P.lock_body()))
calls = []
real_merge = P.G.merge
def spy(parts, only=None):
    calls.append((P.RECEIPT.exists(), only))
    raise RuntimeError("멈춤(시험)")
P.G.merge = spy
P.RECEIPT.write_text("{}")
try:
    P.run_t(); why = ""
except SystemExit as e:
    why = str(e)
check("11 영수증이 있으면 셈 전에 멈춤", "영수증이 이미 있음" in why and calls == [])
P.RECEIPT = tmp / "r2.json"
try:
    P.run_t()
except RuntimeError:
    pass
check("12 새 영수증은 셈 첫 호출 때 이미 있음 · T 굽기에서 세 신호만 셈", calls == [(True, ("S2_REV5", "S7_EMA_ALIGN", "S8_MOM120_SKIP20"))])
sys.argv = ["phase_switch.py"]
try:
    P.main(); why = ""
except SystemExit as e:
    why = str(e)
check("13 깃발 없이 돌리면 셈 없이 거부", "영수증 없는 성과 셈은 없음" in why and len(calls) == 1)
P.G.merge = real_merge
src = Path(P.__file__).read_text()
check("14 지도 굽기(M) 경로를 셈에 쓰지 않음 · T만", "M_PARTS" not in src and "G.T_PART" in src)
check("15 잠금에 sig_map.py · T 굽기 · SIG-MAP 결과 파일 해시 포함", set(P.lock_body()) == {"research/phase_switch.py", "research/sig_map.py", "/tmp/sig-t.pkl", "SIG-MAP-0045/evidence/t_main.json"})
print(f"모두 {ok}개 통과")
