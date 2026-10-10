"""BACKTEST-REPAIR-0002 합성 회귀 검사(kernel2만 · 자료 · 네트워크 없음). python3 -I test_kernel.py → JSON 결과."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel2 as KN  # noqa: E402


class FakeCC:
    class UnknownTax(ValueError):
        pass

    @staticmethod
    def adv_series(code):
        return () if code == "NOADV" else (("20200101", 5e9),)

    @staticmethod
    def sell_tax_rate(day, kind, market, scen):
        if day > "20991231":
            raise FakeCC.UnknownTax("밖")
        return 0.002


def acct(cash=1e8, mult=1.0):
    return KN.Account(KN.Costs(FakeCC, lambda c: "KOSDAQ", mult, "stock"), cash)


R = {}


def check(name, ok, detail=None):
    R[name] = {"pass": bool(ok), "detail": detail}


# 1) 나눠 팔기: 진입은 한 번 · 매수 비용은 미래 분할과 무관 · 수량 보존
a, b = acct(), acct()
qa = a.buy("p", "A", 10000.0, "20200102", "20200102", value=4e7, slots=4)
qb = b.buy("p", "A", 10000.0, "20200102", "20200102", value=4e7, slots=4)
cost_a, cost_b = a.pos["p"]["buy_cost"], b.pos["p"]["buy_cost"]
a.sell("p", 10500.0, "20200110", "20200109")
half = math.floor(b.pos["p"]["qty"] * 2 / 4)
b.sell("p", 10500.0, "20200106", "20200105", qty=half)
b.sell("p", 10500.0, "20200110", "20200109")
sold_b = sum(1 for f in b.fills if f["side"] == "sell")
check("partial_exit_entry_cost_independent_of_future_split", qa == qb and cost_a == cost_b and not a.pos and not b.pos and sold_b == 2,
      {"buy_cost_unsplit": round(cost_a, 2), "buy_cost_split": round(cost_b, 2), "qty": qa})
pf = lambda c: (10500.0, False)
ga, gb = a.check(pf), b.check(pf)
check("cash_and_nav_identity_after_partial", max(ga + gb) < 1e-6, {"gaps": [ga, gb]})
check("position_grouped_once", len(a.closed) == 1 and len(b.closed) == 1 and b.closed[0]["n_sells"] == 2,
      {"closed_rows": len(b.closed)})

# 2) 못 산 매수: 값 없음 → 포지션 · 현금 변화 없음 · 기록
c = acct()
got = c.buy("q", "A", None, "20200102", "20200101", value=1e7)
check("unfilled_buy_no_ghost", got == 0 and not c.pos and c.cash == 1e8 and c.fills[-1]["status"] == "UNFILLED", c.fills[-1]["reason"])

# 3) 현금 축소: 실제 금액으로 비용 · 수량을 함께 풂
d = acct(cash=1_000_000.0)
want = math.floor(5e6 / 7000.0)
q = d.buy("r", "A", 7000.0, "20200102", "20200101", value=5e6)
tot = lambda n: n * 7000.0 * (1 + d.costs.rate("buy", "A", "20200102", n * 7000.0)[0])
check("cash_reduced_exact_solve", q < want and d.cash >= -1e-9 and tot(q + 1) > 1_000_000.0 and d.fills[-1]["status"] == "REDUCED",
      {"want": want, "got": q, "cash_left": round(d.cash, 4)})

# 4) 끝 열린 포지션: 주 결과 MTM · 청산 시나리오는 같은 날 비용까지
e = acct()
e.buy("s", "A", 10000.0, "20200102", "20200101", value=2e7)
pf2 = lambda c: (11000.0, False)
nav, inv = e.mtm(pf2)
liq, liq_cost = e.liquidation_nav(pf2, "20200103")
check("end_open_mtm_and_liquidation", abs(nav - (e.cash + inv)) < 1e-6 and abs((nav - liq) - liq_cost) < 1e-6 and liq_cost > 0,
      {"nav": round(nav, 2), "liq_nav": round(liq, 2), "liq_cost": round(liq_cost, 2), "open_rows": len(e.open_rows(pf2))})

# 5) ADV 없음 · 세금 계약 밖은 건수로 드러남(0으로 숨기지 않음)
f = acct()
f.buy("t", "NOADV", 1000.0, "20200102", "20200101", value=1e6)
f.sell("t", 1000.0, "21000102", "21000101")
check("unknown_adv_tax_counted", f.counts.get("adv_missing_fills") == 2 and f.counts.get("tax_unknown_fills") == 1, dict(f.counts))

# 6) −15% 경계 · 첫날 손익 포함 · Sortino 식
cal = [f"202001{d:02d}" for d in range(2, 31)] + [f"202002{d:02d}" for d in range(3, 28)]
navs, v = [], 1e8 * 0.99                       # 첫날 −1%(처음 현금 대비)
for i, day in enumerate(cal):
    if day == "20200110":
        v *= 0.85                              # 정확히 −15% → 넘지 않음
    if day == "20200210":
        v *= 1 - 0.1500001                     # −15.00001% → 넘음
    navs.append((day, v, 0.0))
rep = KN.report(navs, [], cal, periods=(("전체", "00000000", "99999999"),))["전체"]
check("loss_boundary_strict", rep["day_breach_-15"] == 1 and rep["base"] == "처음 현금 1억", {"day_breach": rep["day_breach_-15"],
                                                                                          "worst_day": rep["worst_day"]})
flat = KN.report([(d, 0.99e8, 0.0) for d in cal], [], cal, periods=(("전체", "00000000", "99999999"),))["전체"]
check("first_day_included", flat["worst_day"] == -1.0 and flat["CAGR"] < 0, {"worst_day": flat["worst_day"], "CAGR": flat["CAGR"]})
r = [-0.01, 0.02, -0.03, 0.0]
manual = (sum(r) / 4) / math.sqrt(sum(min(x, 0) ** 2 for x in r) / 4) * math.sqrt(252)
check("sortino_rms_target0", abs(KN.sortino(r) - manual) < 1e-12, {"sortino": KN.sortino(r)})
mon = KN.report([(d, 1e8 * (0.84 if d >= "20200203" else 1.0), 0.0) for d in cal], [], cal, periods=(("전체", "00000000", "99999999"),))["전체"]
check("month_breach_strict", mon["month_breach_-15"] == 1 and mon["worst_month_at"] == "202002", {"worst_month": mon["worst_month"]})

ok = all(x["pass"] for x in R.values())
print(json.dumps({"all_pass": ok, "n": len(R), "results": R}, ensure_ascii=False, indent=1))
sys.exit(0 if ok else 1)
