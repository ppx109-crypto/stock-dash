"""USINV-0039 합성 자료 시험(round 2) — 실제 수익 셈 없음. python3 evidence/synth_test.py"""
import copy, importlib.util, json, random, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("t009", Path(__file__).resolve().parents[4] / "research/t009.py")
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
t.REPS = 200   # 시험 시간만 줄임
fails = []
def ok(c, m):
    print(("통과 " if c else "실패 ") + m)
    if not c: fails.append(m)

# 1) 비용 · 신호 자르기
ok(abs(t.side(5000, t.MAIN) - 0.00115) < 1e-12, "편도 비용 5,000원 = 0.115%")
rng = random.Random(1)
def bdays(y0, y1):
    import datetime as dt
    d, out = dt.date(y0, 1, 2), []
    while d.year <= y1:
        if d.weekday() < 5: out.append(d.strftime("%Y%m%d"))
        d += dt.timedelta(days=1)
    return out
days = [d for d in bdays(2015, 2026) if "20150729" <= d <= "20260916"]
px, v = {}, 5000.0
for d in days:
    v *= 1 + rng.gauss(0, 0.012); px[d] = max(2500, round(v / 5) * 5)
inv = (days, px, {})
base, a = {}, 1e8
for d in days:
    if d >= "20170201":
        a *= 1 + rng.gauss(0.0005, 0.01); base[d] = a
tri = t.tri_of(*inv)
for var in t.VARIANTS:
    full = t.signal(var, days, tri)
    cut = [d for d in days if d <= "20211230"]
    part = t.signal(var, cut, t.tri_of(*t.cut_inv(inv, "20211230")))
    ok(all(full.get(d) == part.get(d) for d in cut), f"{var} 신호 자르기 같음 · 켜진 날 {sum(1 for x in full.values() if x)}")

# 2) 덧대기 손셈(값 고정이면 비용만큼만 줄어듦 · 신호 다음 날 종가 체결)
d0 = days[:300]
b0 = {d: 100.0 for d in d0}; flat = {d: 5000.0 for d in d0}
on = {d: (100 <= i < 110) for i, d in enumerate(d0)}
nv = dict(t.overlay(b0, d0, flat, {}, on, t.MAIN, d0[0])[0])
ok(abs(nv[d0[100]] - 100) < 1e-12, "신호 켜진 그날 종가에는 안 삼")
ok(abs(nv[d0[101]] - (100 - 20 * (t.A_COST + 0.00115))) < 1e-9, "들어간 날 NAV = 옮긴 돈 × (A 비용 + 인버스 비용)만큼 줄어듦")
exp_out = 100 - 20 * (1 + t.A_COST) + 20 * (1 - 0.00115) * (1 - 0.00115) * (1 - t.A_COST)
ok(abs(nv[d0[111]] - exp_out) < 1e-9, "나온 날 NAV 손셈과 같음")
w, _ = t.windows_fix(b0, d0, flat, {}, on, t.MAIN, d0[0])
ok(w and w[0][:2] == (d0[101], d0[111]), "창 산 날 · 판 날 = 신호 다음 날")

# 3) GPT 1번: Train 단계는 컷 뒤 값을 크게 바꿔도 한 칸도 안 바뀌고, 컷 뒤 날짜가 나오지 않음
r1 = t.run(base, inv)
base2 = {d: (x * (5 if d > "20211230" else 1)) for d, x in base.items()}
px2 = {d: (x * 3 if d > "20211230" else x) for d, x in px.items()}
r2 = t.run(base2, (days, px2, {}))
ok(all(r1[k] == r2[k] for k in t.CUT_KEYS), f"컷 뒤 값을 5배 · 3배로 바꿔도 CUT_KEYS 같음(고른 판 {r1['pick']})")
txt = json.dumps({k: r1[k] for k in t.CUT_KEYS})
ok(not any(d in txt for d in days if d > "20211230"), "Train 산출물에 2021-12-30 뒤 날짜 없음")
r3 = t.run(base, inv, to="20211230")
ok(all(r1[k] == r3[k] for k in t.CUT_KEYS) and r3["valid"] is None, "T_TO=20211230 셈과 본 셈의 CUT_KEYS 같음 · 자르기 셈은 Validation 없음")

# 4) GPT 2번: Validation 시작 = 2021-12-30 종가 A만 100% · 인버스 0 · 첫 진입은 같은 규칙
alw = {d: True for d in days}
days_v, px_v, _ = t.cut_inv(inv, t.VALID[1])
nav, alone = t.overlay(t.cut_base(base, t.VALID[1]), days_v, px_v, {}, alw, t.MAIN, "20211230")
ok(nav[0] == ("20211230", base["20211230"]), "Validation 첫 값 = 2021-12-30 A NAV(Train 덧댄 NAV 이어받지 않음)")
first_v = [d for d in days_v if d > "20211230"][0]
exp = base[first_v] - 0.2 * base[first_v] * (t.A_COST + t.side(px_v[first_v], t.MAIN))
ok(abs(dict(nav)[first_v] - exp) < 1e-6, f"늘 켜진 신호면 {first_v} 종가에 처음 들어감(그날 수익은 A만)")
if r1["valid"]:
    ok(r1["valid"]["start"] == "20211230", "valid_phase 시작 날 = 20211230")

# 5) GPT 3번: 반올림 전 값으로 고름
raws = {v: {"windows": 5, "cagr_gain": 0.0} for v in t.VARIANTS}
raws["T50"]["cagr_gain"] = 1e-7; raws["V90"]["cagr_gain"] = 2e-7
ok(t.choose(raws) == "V90", "증분 차 1e-7(0.00001%p)도 큰 쪽(V90)을 고름")
raws["V90"]["cagr_gain"] = 1e-7
ok(t.choose(raws) == "T50", "원시값이 정확히 같을 때만 표의 앞 판")
raws = {v: {"windows": 2, "cagr_gain": 1.0} for v in t.VARIANTS}
ok(t.choose(raws) is None, "창 3개 미만만 있으면 고를 판 없음")

# 6) GPT 4번: 손실 조건은 네 경로
good = {"worst_day": -0.05, "worst_month": -0.10}
ok(t.loss_ok([good] * 4), "네 경로 모두 −15% 안이면 통과")
ok(not t.loss_ok([good, good, good, {"worst_day": -0.05, "worst_month": -0.1500001}]), "Validation 스트레스 달 −15.00001%면 실패(반올림 안 함)")
ok(not t.loss_ok([good, {"worst_day": -0.151, "worst_month": -0.1}, good, good]), "Train 스트레스 하루 −15.1%면 실패")
print(f"합계: 실패 {len(fails)}")
sys.exit(1 if fails else 0)
