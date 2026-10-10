"""REV-DOWN-0047 합성 시험 — 작은 가짜 굽기로 사고팖 · 비용 · 몫 · 국면 · 정산 · 판정 · 영수증 순서."""
import json, pickle, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/home/user/stock-dash/research")
import rev_down as R
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
tmp = Path(tempfile.mkdtemp())
days = [f"2010{m:02d}{d:02d}" for m in range(1, 13) for d in range(1, 29)][:200]
def snap(ix_fn, codes=10, gap=None, price=None):
    prices, rows = {}, []
    for n in range(codes):
        c = f"{n:06d}"
        xs = [price(n, t) if price else 100.0 for t in range(len(days))]
        rs = [(d, x) for t, (d, x) in enumerate(zip(days, xs)) if not (gap and gap(c, t))]
        prices[c] = {"name": c, "rows": rs}
    for c, b in prices.items():
        for i, (d, x) in enumerate(b["rows"]):
            if i >= 120:
                rows.append({"code": c, "date": d, "i": i, "price": x, "거래대금20": 1.0})
    s = {"prices": prices, "rows": rows, "ix": {d: ix_fn(t) for t, d in enumerate(days)}, "flow": {}, "br": {}}
    p = tmp / f"s{len(list(tmp.iterdir()))}.pkl"
    p.write_bytes(pickle.dumps(s))
    return str(p)
up = lambda t: 100 * 1.001 ** t
p = snap(up)
sim = R.simulate((p, days[0], days[-1]))
check("1 오름장(069500 60일 +6%)에는 사지 않음 · NAV 1.0 그대로", sim["trades"] == 0 and all(abs(v - 1) < 1e-12 for v in sim["nav"].values()))
down_from = 150
dn = lambda t: 100 * (0.998 ** max(0, t - 60))            # 60일 수익 −11%대 → 내림
first_down = next(t for t in range(len(days)) if t >= 60 and dn(t) / dn(t - 60) - 1 < -0.05)
# 0번 종목만 5일 동안 가장 많이 떨어짐 → 위 20%(10종목 → 2종목)는 0번 · 1번
price = lambda n, t: 100.0 * (0.9 if (n in (0, 1) and t >= 118) else 1.0)
p2 = snap(dn, price=price)
sim2 = R.simulate((p2, days[0], days[-1]))
c0 = sim2["cohorts"][0]
check("2 내림 날 무리 = S2 위 20%(10종목 중 2) · 첫 무리 날 = 대상이 생긴 첫 내림 날", c0["n"] == 2 and c0["day"] == days[120])
check("3 무리 몫 = 그날 NAV의 1/10 · 산 비용 0.05% · 판 비용 0.25% → 값이 같으면 무리 순손익 = (1−0.0005)(1−0.0025) − 1",
      abs(c0["spent"] - 0.1) < 1e-12 and abs(c0["back"] / c0["spent"] - (1 - 0.0005) * (1 - 0.0025)) < 1e-12)
# 사고팖 날 확인: 첫 무리를 판 날의 NAV 변화
nav = sim2["nav"]
check("4 판단 다음 날 종가에 삼(판단 날 NAV는 현금 그대로 1.0)", abs(nav[days[120]] - 1.0) < 1e-12 and nav[days[121]] < 1.0)
# 10줄 뒤 팖: 첫 무리 돈이 days[131]에 돌아옴 → 그날 현금 늘어남
check("5 산 줄에서 10줄 뒤 종가에 팖(무리 수 > 1 · 매매 수 = 무리 × 2)", sim2["trades"] == 2 * len(sim2["cohorts"]))
# 다음 날 값이 없으면 그 종목 몫은 현금
gap = lambda c, t: c == "000000" and t == 121
p3 = snap(dn, price=price, gap=gap)
sim3 = R.simulate((p3, days[0], days[-1]))
check("6 다음 날 그 종목 값이 없으면 그 몫은 사지 않음(현금)", abs(sim3["cohorts"][0]["spent"] - 0.05) < 1e-12)
# 끝 정산
check("7 기간 끝에 남은 것은 마지막 값으로 정산(end_open > 0이면 무리에 end_settled)", sim2["end_open"] > 0 and any(c.get("end_settled") for c in sim2["cohorts"]))
# 판정
st = {"cohorts": 100, "annual_pct": 5.0, "worst_day": ["d", -3.0], "worst_month": ["m", -10.0], "years_pct": {"2008": 10.0, "2009": -1.0, "2010": 0.0, "2011": 2.0}}
c, v, med, yp = R.judge(st, [1, 2, 3, 4, 6, 7, 8, 9], [0.1, 0.5])
check("8 모두 넘으면 IMPLEMENTABLE_IN_SEEN_DATA · 대조 가운데값 = 4 · 6 평균 5 → 5.0 > 5 아님이면 탈락", v == "REJECTED" and med == 5.0 and not c["2_beats_random_median"])
c, v, med, yp = R.judge(dict(st, annual_pct=5.5), [1, 2, 3, 4, 6, 7, 8, 9], [0.1, 0.5])
check("9 대조 가운데값 넘고 모두 통과 → IMPLEMENTABLE_IN_SEEN_DATA · 매매한 해만 셈(0인 해 뺌) 2/3", v == "IMPLEMENTABLE_IN_SEEN_DATA" and yp == "2/3")
c, v, _, _ = R.judge(dict(st, annual_pct=5.5, worst_month=["m", -15.01]), [0] * 8, [0.1, 0.5])
check("10 달 −15.01% → 탈락(조건 ③)", v == "REJECTED" and not c["3_day_month_ge_-15"])
c, v, _, _ = R.judge(dict(st, annual_pct=5.5), [0] * 8, [-0.01, 0.5])
check("11 부트스트랩 아래 끝 ≤ 0 → 탈락(조건 ⑤)", v == "REJECTED")
c, v, _, _ = R.judge(dict(st, cohorts=59), [0] * 8, [0.1, 0.5])
check("12 무리 59개 → NEEDS_DATA", v == "NEEDS_DATA")
c, v, _, yp = R.judge(dict(st, annual_pct=5.5, years_pct={"2008": 1.0, "2009": -1.0, "2010": -1.0}), [0] * 8, [0.1, 0.5])
check("13 매매한 해 가운데 + 1/3(< 60%) → 탈락(조건 ④)", v == "REJECTED" and yp == "1/3")
# stats: 달 TWR
fake = {"nav": {"20100104": 1.0, "20100105": 0.9, "20100201": 0.9, "20100202": 0.99}, "cohorts": [{"day": "20100104", "spent": 1, "back": 1.1}], "trades": 1}
s = R.stats(fake)
check("14 가장 나쁜 하루 −10% · 가장 나쁜 달(1월) −10% · 무리 평균 +10%", s["worst_day"] == ["20100105", -10.0] and s["worst_month"] == ["201001", -10.0] and s["cohort_mean_net_pct"] == 10.0)
# 무작위 대조: 같은 날 같은 수
simr = R.simulate((p2, days[0], days[-1]), "random", 3)
check("15 무작위 대조는 같은 날 · 같은 수를 고름", [(c["day"], c["n"]) for c in simr["cohorts"]] == [(c["day"], c["n"]) for c in sim2["cohorts"]])
# 영수증 순서
R.LOCK = tmp / "l.json"; R.RECEIPT = tmp / "r.json"
R.LOCK.write_text(json.dumps({"x": 1}))
try:
    R.run(); why = ""
except SystemExit as e:
    why = str(e)
check("16 잠금이 다르면 셈 전에 멈춤 · 영수증 없음", "잠금이 다름" in why and not R.RECEIPT.exists())
R.LOCK.write_text(json.dumps(R.lock_body()))
calls = []
real = R.simulate
def spy(*a, **k):
    calls.append(R.RECEIPT.exists())
    raise RuntimeError("멈춤(시험)")
R.simulate = spy
R.RECEIPT.write_text("{}")
try:
    R.run(); why = ""
except SystemExit as e:
    why = str(e)
check("17 영수증이 이미 있으면 셈 전에 멈춤", "영수증이 이미 있음" in why and calls == [])
R.RECEIPT = tmp / "r2.json"
try:
    R.run()
except RuntimeError:
    pass
check("18 새 영수증은 계좌 셈 첫 호출 때 이미 있음", calls == [True])
sys.argv = ["rev_down.py"]
try:
    R.main(); why = ""
except SystemExit as e:
    why = str(e)
check("19 깃발 없이 돌리면 셈 없이 거부", "영수증 없는 성과 셈은 없음" in why and calls == [True])
R.simulate = real
src = Path(R.__file__).read_text()
check("20 앞날 줄 있는지 미리 보는 셈 없음(len(…x) 비교 없음)", "len(ln[\"x\"])" not in src and "len(lane" not in src)
print(f"모두 {ok}개 통과")
