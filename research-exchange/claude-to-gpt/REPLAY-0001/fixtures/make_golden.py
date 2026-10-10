# golden.json을 손으로 정한 값 그대로 적는 도우미(계산 없음: 시각 문자열 만들기만)
import json, sys
D = {"D1": "2026-01-05", "D2": "2026-01-06", "D3": "2026-01-07", "D4": "2026-01-08",
     "J29": "2026-01-29", "J30": "2026-01-30"}
def t(d, hm): return f"{D[d]}T{hm}:00+09:00"
def dep(i, d, amt, hm="08:00"): return {"id": i, "type": "DEPOSIT", "at": t(d, hm), "amount": amt}
def wd(i, d, amt, hm="08:00"): return {"id": i, "type": "WITHDRAW", "at": t(d, hm), "amount": amt}
def fill(i, d, hm, side, qty, px, sec="S1", trade="T1", strat="A", order=None, fid=None, seq=None, **kw):
    e = {"id": i, "type": "FILL", "at": t(d, hm), "fill_id": fid or i, "order_id": order or ("o_" + i),
         "trade_id": trade, "strategy_id": strat, "security_id": sec, "side": side, "qty": qty,
         "price": px, "evidence": "MODEL_FILL"}
    if seq is not None: e["seq"] = seq
    e.update(kw); return e
def price(i, d, prices, asof_hm="15:30", avail=None, version=1):
    av = avail or t(d, "15:45")
    return {"id": i, "type": "PRICE", "at": av, "prices": prices, "as_of": t(d, asof_hm),
            "available_at": av, "version": version, "source": "SYNTH_FIXTURE", "session": "REGULAR_CLOSE"}
def mark(i, d, hm="16:00"): return {"id": i, "type": "MARK", "at": t(d, hm), "date": D[d]}
def ev(i, typ, d, hm, seq=None, **kw):
    e = {"id": i, "type": typ, "at": t(d, hm)}
    if seq is not None: e["seq"] = seq
    e.update(kw); return e
BASE = {"source_mode": "SYNTHETIC", "cost": {"buy_fee": "0.001", "sell_fee": "0.001", "sell_tax": "0.002"}}
cases = []
def case(cid, subs): cases.append({"case": cid, "subs": subs})
def sub(sid, events, expect, config=None):
    c = json.loads(json.dumps(BASE));
    if config: c.update(config)
    return {"sub": sid, "config": c, "events": events, "expect": expect}

# C1
case("C1", [
 sub("C1", [dep("c1_d", "D1", 1000000),
            ev("c1_i", "ORDER_INTENT", "D1", "09:00", seq=1, order_id="o1", trade_id="T1", strategy_id="A",
               security_id="S1", side="BUY", qty=10, price=50000, model_fill=False),
            ev("c1_a", "ORDER_ACCEPTED", "D1", "09:00", seq=2, order_id="o1"),
            price("c1_p", "D1", {"S1": 50000}), mark("c1_m", "D1")],
     {"status": "OK", "cash": 1000000, "positions": {}, "orderable_cash": 499500,
      "navs": {D["D1"]: {"nav": 1000000}}, "orders": {"o1": {"state": "OPEN", "remaining": 10, "filled": 0}},
      "fills_count": 0}),
 sub("C1b", [dep("c1b_d", "D1", 1000000),
             fill("c1b_f", "D1", "09:10", "BUY", 1, 1000, evidence="OBSERVED"),
             mark("c1b_m", "D1")],
     {"status": "OK", "cash": 1000000, "positions": {}, "navs": {D["D1"]: {"nav": 1000000}},
      "rejections": [{"event_id": "c1b_f", "reason": "MISSING_EVIDENCE"}]},
     config={"source_mode": "OBSERVED_KIS_PAPER"}),
])
# C2
def intent(i, d, hm, seq, oid, qty=10, px=50000, **kw):
    return ev(i, "ORDER_INTENT", d, hm, seq=seq, order_id=oid, trade_id="T_" + oid, strategy_id="A",
              security_id="S1", side="BUY", qty=qty, price=px, model_fill=False, **kw)
case("C2", [sub("C2", [dep("c2_d", "D1", 1000000),
    intent("c2_i1", "D1", "09:00", 1, "o1"), ev("c2_r1", "ORDER_REJECTED", "D1", "09:00", seq=2, order_id="o1"),
    intent("c2_i2", "D1", "09:00", 3, "o2"), ev("c2_a2", "ORDER_ACCEPTED", "D1", "09:00", seq=4, order_id="o2"),
    ev("c2_c2", "ORDER_CANCELLED", "D1", "10:00", order_id="o2"),
    intent("c2_i3", "D1", "09:00", 5, "o3"), ev("c2_a3", "ORDER_ACCEPTED", "D1", "09:00", seq=6, order_id="o3"),
    ev("c2_x3", "ORDER_EXPIRED", "D1", "15:30", order_id="o3"),
    price("c2_p", "D1", {"S1": 50000}), mark("c2_m", "D1")],
    {"status": "OK", "cash": 1000000, "positions": {}, "orderable_cash": 1000000,
     "navs": {D["D1"]: {"nav": 1000000}},
     "orders": {"o1": {"state": "REJECTED"}, "o2": {"state": "CANCELLED"}, "o3": {"state": "EXPIRED"}},
     "fills_count": 0})])
# C3
case("C3", [sub("C3", [dep("c3_d", "D1", 1000000),
    ev("c3_i", "ORDER_INTENT", "D1", "09:00", seq=1, order_id="o1", trade_id="T1", strategy_id="A",
       security_id="S1", side="BUY", qty=50, price=2000, model_fill=False),
    ev("c3_a", "ORDER_ACCEPTED", "D1", "09:00", seq=2, order_id="o1"),
    fill("c3_f", "D1", "09:10", "BUY", 20, 2000, order="o1"),
    ev("c3_s", "SNAPSHOT", "D1", "09:30"),
    ev("c3_c", "ORDER_CANCELLED", "D1", "10:00", order_id="o1"),
    price("c3_p", "D1", {"S1": 2000}), mark("c3_m", "D1")],
    {"status": "OK", "cash": 959960, "positions": {"S1": 20}, "orderable_cash": 959960,
     "snapshots": [{"event_id": "c3_s", "cash": 959960, "orderable_cash": 899900}],
     "navs": {D["D1"]: {"nav": 999960}},
     "orders": {"o1": {"state": "CANCELLED", "filled": 20, "remaining": 0, "cancelled_qty": 30}},
     "fills": [{"fill_id": "c3_f", "notional": 40000, "fee": 40, "tax": 0}]})])
# C4
case("C4", [sub("C4", [dep("c4_d", "D1", 1000000),
    fill("c4_f1", "D1", "09:10", "BUY", 10, 10000, fid="f1", order="o1", seq=1),
    fill("c4_f1dup", "D1", "09:10", "BUY", 10, 10000, fid="f1", order="o1", seq=2),
    fill("c4_f1bad", "D1", "09:10", "BUY", 11, 10000, fid="f1", order="o1", seq=3),
    price("c4_p", "D1", {"S1": 10000}), mark("c4_m", "D1")],
    {"status": "OK", "cash": 899900, "positions": {"S1": 10}, "duplicates_ignored": 1,
     "rejections": [{"event_id": "c4_f1bad", "reason": "FILL_ID_CONFLICT"}],
     "navs": {D["D1"]: {"nav": 999900}}, "fills_count": 1})])
# C5
def bad(i, seq, side, qty, px):
    return fill(i, "D1", "09:20", side, qty, px, seq=seq)
case("C5", [sub("C5", [dep("c5_d", "D1", 1000000),
    fill("c5_f", "D1", "09:10", "BUY", 10, 10000),
    bad("c5_r1", 1, "SELL", 11, 10000), bad("c5_r2", 2, "BUY", -5, 10000), bad("c5_r3", 3, "BUY", "1.5", 10000),
    bad("c5_r4", 4, "BUY", 1, 0), bad("c5_r5", 5, "BUY", 1, -100), bad("c5_r6", 6, "BUY", 100, 10000),
    price("c5_p", "D1", {"S1": 10000}), mark("c5_m", "D1")],
    {"status": "OK", "cash": 899900, "positions": {"S1": 10}, "navs": {D["D1"]: {"nav": 999900}},
     "rejections": [{"event_id": "c5_r1", "reason": "OVERSELL"}, {"event_id": "c5_r2", "reason": "BAD_QTY"},
                    {"event_id": "c5_r3", "reason": "BAD_QTY"}, {"event_id": "c5_r4", "reason": "BAD_PRICE"},
                    {"event_id": "c5_r5", "reason": "BAD_PRICE"}, {"event_id": "c5_r6", "reason": "INSUFFICIENT_CASH"}],
     "fills_count": 1})])
# C6, C7
def mintent(i, d, hm, oid, sec, px, alloc, nav_ref, seq=None, trade=None, strat="A", side="BUY", **kw):
    return ev(i, "ORDER_INTENT", d, hm, seq=seq, order_id=oid, trade_id=trade or ("T_" + oid), strategy_id=strat,
              security_id=sec, side=side, price=px, alloc_won=alloc, nav_ref_won=nav_ref, model_fill=True, **kw)
case("C6", [sub("C6", [dep("c6_d", "D1", 1000000),
    mintent("c6_i", "D1", "09:00", "o1", "S1", 1000, 1000000, 1000000),
    price("c6_p", "D1", {"S1": 1000}), mark("c6_m", "D1")],
    {"status": "OK", "cash": 1, "positions": {"S1": 999}, "navs": {D["D1"]: {"nav": 999001}},
     "sizing": [{"order_id": "o1", "naive_qty": 1000, "qty": 999, "reason": "REDUCED_FOR_COST"}],
     "fills": [{"notional": 999000, "fee": 999, "tax": 0}]})])
case("C7", [sub("C7", [dep("c7_d", "D1", 1000),
    mintent("c7_i", "D1", "09:00", "o1", "S1", 1000, 1000, 1000),
    price("c7_p", "D1", {"S1": 1000}), mark("c7_m", "D1")],
    {"status": "OK", "cash": 1000, "positions": {}, "navs": {D["D1"]: {"nav": 1000}}, "fills_count": 0,
     "sizing": [{"order_id": "o1", "naive_qty": 1, "qty": 0, "reason": "ZERO_CANNOT_AFFORD_ONE_WITH_COST"}]})])
# C8
secs = [f"S{k:02d}" for k in range(1, 13)]
ev8 = [dep("c8_d", "D1", 1000000)]
for k, s in enumerate(secs, 1):
    ev8.append(mintent(f"c8_i{k:02d}", "D1", "09:00", f"o{k:02d}", s, 1000, 100000, 1000000, seq=k))
ev8 += [price("c8_p", "D1", {s: 1000 for s in secs}), mark("c8_m", "D1")]
sz8 = [{"order_id": f"o{k:02d}", "naive_qty": 100, "qty": 99, "reason": "REDUCED_FOR_COST"} for k in range(1, 11)]
sz8 += [{"order_id": "o11", "naive_qty": 100, "qty": 9, "reason": "REDUCED_BY_CASH", "shortfall_won": 90990},
        {"order_id": "o12", "naive_qty": 100, "qty": 0, "reason": "ZERO_BY_CASH", "shortfall_won": 99999}]
pos8 = {s: 99 for s in secs[:10]}; pos8["S11"] = 9
case("C8", [sub("C8", ev8, {"status": "OK", "cash": 1, "positions": pos8, "total_qty": 999,
    "navs": {D["D1"]: {"nav": 999001}}, "sizing": sz8, "min_cash": 1, "max_gross_exposure": "999000/999001"})])
# C9
case("C9", [sub("C9", [dep("c9_d", "D1", 1000000),
    fill("c9_f1", "D1", "09:10", "BUY", 100, 5000), fill("c9_f2", "D1", "14:00", "SELL", 100, 5100),
    price("c9_p", "D1", {"S1": 5100}), mark("c9_m", "D1")],
    {"status": "OK", "cash": 1007970, "positions": {}, "navs": {D["D1"]: {"nav": 1007970}},
     "returns": {D["D1"]: "0.00797"}, "trades": {"T1": {"realized": 7970, "open_qty": 0}},
     "fills": [{"fill_id": "c9_f1", "notional": 500000, "fee": 500, "tax": 0},
               {"fill_id": "c9_f2", "notional": 510000, "fee": 510, "tax": 1020}]})])
# C10
case("C10", [
 sub("C10", [dep("c10_d", "D1", 1000000),
             fill("c10_f1", "D1", "10:00", "BUY", 10, 10000), fill("c10_f2", "D1", "10:00", "SELL", 10, 10000),
             price("c10_p", "D1", {"S1": 10000}), mark("c10_m", "D1")],
     {"status": "AMBIGUOUS", "ambiguous_ids": ["c10_f1", "c10_f2"], "navs": {}}),
 sub("C10b", [dep("c10b_d", "D1", 1000000),
              fill("c10b_f1", "D1", "10:00", "BUY", 10, 10000, seq=1),
              fill("c10b_f2", "D1", "10:00", "SELL", 10, 10000, seq=2),
              price("c10b_p", "D1", {"S1": 10000}), mark("c10b_m", "D1")],
     {"status": "OK", "cash": 999600, "positions": {}, "navs": {D["D1"]: {"nav": 999600}}}),
])
# C11
case("C11", [sub("C11", [dep("c11_d", "D1", 1000000),
    fill("c11_f1", "D1", "09:10", "BUY", 50, 10000), fill("c11_f2", "D1", "10:00", "SELL", 20, 10000),
    fill("c11_f3", "D1", "11:00", "SELL", 30, 10000),
    price("c11_p", "D1", {"S1": 10000}), mark("c11_m", "D1")],
    {"status": "OK", "cash": 998000, "positions": {}, "navs": {D["D1"]: {"nav": 998000}},
     "trades": {"T1": {"entry_fills": 1, "exit_fills": 2, "realized": -2000, "open_qty": 0,
                       "exits": [{"fill_id": "c11_f2", "cost_alloc": 200200, "realized": -800},
                                 {"fill_id": "c11_f3", "cost_alloc": 300300, "realized": -1200}]}},
     "trades_count": 1})])
# C12
case("C12", [sub("C12", [dep("c12_d", "D1", 1000000),
    fill("c12_f1", "D1", "09:10", "BUY", 100, 1000),
    price("c12_p1", "D1", {"S1": 1000}), mark("c12_m1", "D1"),
    price("c12_p2", "D2", {"S1": 1000}), mark("c12_m2", "D2"),
    fill("c12_f2", "D3", "10:00", "SELL", 100, 1000),
    price("c12_p3", "D3", {"S1": 1000}), mark("c12_m3", "D3")],
    {"status": "OK", "cash": 999600, "positions": {},
     "navs": {D["D1"]: {"nav": 999900}, D["D2"]: {"nav": 999900}, D["D3"]: {"nav": 999600}},
     "returns": {D["D1"]: "-0.0001", D["D2"]: "0", D["D3"]: "-300/999900"},
     "costs_by_date": {D["D1"]: 100, D["D3"]: 300}, "months": {"2026-01": {"ret": "-0.0004", "partial": True}}})])
# C13
case("C13", [sub("C13", [dep("c13_d", "D1", 1000000),
    fill("c13_f", "D1", "09:10", "BUY", 1, 100500, ref_price=100000, slippage_in_price=True),
    price("c13_p", "D1", {"S1": 100000}), mark("c13_m", "D1")],
    {"status": "OK", "cash": 899399, "positions": {"S1": 1}, "navs": {D["D1"]: {"nav": 999399}},
     "fills": [{"notional": 100500, "fee": 101, "tax": 0, "slippage_info_won": 500}]},
    config={"slippage": {"bps": "50", "included_in_fill_price": True}})])
# C14
case("C14", [sub("C14", [dep("c14_d", "D1", 1000000),
    fill("c14_f1", "D1", "09:10", "BUY", 100, 5000),
    price("c14_p1", "D1", {"S1": 5000}), mark("c14_m1", "D1"),
    fill("c14_f2", "D2", "10:00", "SELL", 100, 5150, ledger_pnl_pct="3.0"),
    price("c14_p2", "D2", {"S1": 5150}), mark("c14_m2", "D2")],
    {"status": "OK", "cash": 1012955, "positions": {},
     "navs": {D["D1"]: {"nav": 999500}, D["D2"]: {"nav": 1012955}},
     "trades": {"T1": {"realized": 12955}},
     "discrepancies": [{"trade_id": "T1", "ledger_ret": "0.03", "fill_net_ret": "2591/100100"}]})])
# C15
case("C15", [sub("C15", [dep("c15_d1", "D1", 1000000),
    fill("c15_f", "D1", "09:10", "BUY", 50, 10000),
    price("c15_p1", "D1", {"S1": 11000}), mark("c15_m1", "D1"),
    dep("c15_d2", "D2", 1000000), price("c15_p2", "D2", {"S1": 10000}), mark("c15_m2", "D2"),
    wd("c15_w3", "D3", 500000), price("c15_p3", "D3", {"S1": 10000}), mark("c15_m3", "D3")],
    {"status": "OK", "cash": 999500, "positions": {"S1": 50},
     "navs": {D["D1"]: {"nav": 1049500}, D["D2"]: {"nav": 1999500}, D["D3"]: {"nav": 1499500}},
     "returns": {D["D1"]: "0.0495", D["D2"]: "-50000/2049500", D["D3"]: "0"},
     "twr_total": "195901/8198000", "net_flows": 1500000, "money_pnl": -500,
     "risk": {"mdd": "-50000/2049500", "raw_nav_mdd": None, "raw_nav_mdd_reason": "FLOWS_PRESENT"}})])
# C16
c16_0 = {"cost": {"buy_fee": "0", "sell_fee": "0", "sell_tax": "0"}}
def c16(sid, p2, dep_amt, qty, px, cfg, exp):
    return sub(sid, [dep(sid + "_d", "J29", dep_amt), fill(sid + "_f", "J29", "09:10", "BUY", qty, px),
                     price(sid + "_p1", "J29", {"S1": px}), mark(sid + "_m1", "J29"),
                     price(sid + "_p2", "J30", {"S1": p2}), mark(sid + "_m2", "J30")], exp, config=cfg)
case("C16", [
 c16("C16a", 8500, 1000000, 100, 10000, c16_0,
     {"status": "OK", "cash": 0, "returns": {D["J29"]: "0", D["J30"]: "-0.15"},
      "months": {"2026-01": {"ret": "-0.15", "partial": True}},
      "risk": {"day": "-0.15", "month": "-0.15", "mdd": "-0.15", "verdict_day": "PASS",
               "verdict_month": "PASS", "verdict_mdd": "PASS", "verdict": "PASS"}}),
 c16("C16b", 8490, 1000000, 100, 10000, c16_0,
     {"status": "OK", "returns": {D["J30"]: "-0.151"},
      "risk": {"day": "-0.151", "month": "-0.151", "mdd": "-0.151", "verdict_day": "FAIL",
               "verdict_month": "FAIL", "verdict_mdd": "FAIL", "verdict": "FAIL"}}),
 c16("C16c", 850, 1001000, 1000, 1000, {"cost": {"buy_fee": "0.001", "sell_fee": "0.001", "sell_tax": "0.002"}},
     {"status": "OK", "cash": 0, "navs": {D["J29"]: {"nav": 1000000}, D["J30"]: {"nav": 850000}},
      "returns": {D["J29"]: "-1/1001", D["J30"]: "-0.15"},
      "months": {"2026-01": {"ret": "-151000/1001000", "partial": True}},
      "risk": {"day": "-0.15", "month": "-151000/1001000", "mdd": "-151000/1001000", "verdict_day": "PASS",
               "verdict_month": "FAIL", "verdict_mdd": "FAIL", "verdict": "FAIL"}}),
])
# C17
case("C17", [sub("C17", [dep("c17_d", "D1", 1000000),
    fill("c17_f", "D1", "09:10", "BUY", 10, 10000),
    price("c17_pbad", "D1", {"S9": 1}, asof_hm="15:30", avail=t("D1", "15:00")),
    price("c17_p1", "D1", {"S1": 10000}), mark("c17_m1", "D1"),
    price("c17_p1v2", "D1", {"S1": 9000}, avail=t("D2", "10:00"), version=2),
    price("c17_p2", "D2", {"S1": 12000}), mark("c17_m2", "D2")],
    {"status": "OK", "cash": 899900, "navs": {D["D1"]: {"nav": 999900}, D["D2"]: {"nav": 1019900}},
     "corrections_after_snapshot": [{"security": "S1", "as_of": t("D1", "15:30"), "version": 2, "price": 9000,
                                     "snapshot_date": D["D1"]}],
     "rejections": [{"event_id": "c17_pbad", "reason": "BAD_PRICE_TIME"}]})])
# C18
case("C18", [
 sub("C18a", [dep("c18a_d", "D1", 1000000), fill("c18a_f", "D1", "09:10", "BUY", 10, 5000, sec="S2"),
              mark("c18a_m", "D1")],
     {"status": "OK", "cash": 949950, "navs": {D["D1"]: {"nav": None, "reason": "MISSING_PRICE:S2"}},
      "risk": {"verdict": "INCOMPLETE"}}),
 sub("C18b", [dep("c18b_d", "D1", 1000000), fill("c18b_f", "D1", "09:10", "BUY", 10, 10000),
              price("c18b_p1", "D1", {"S1": 10000}), mark("c18b_m1", "D1"), mark("c18b_m2", "D2"),
              price("c18b_p3", "D3", {"S1": 11000}), mark("c18b_m3", "D3")],
     {"status": "OK", "navs": {D["D1"]: {"nav": 999900}, D["D2"]: {"nav": None, "reason": "STALE_PRICE:S1"},
                               D["D3"]: {"nav": 1009900}},
      "returns": {D["D1"]: "-0.0001", D["D2"]: None, D["D3"]: None},
      "risk": {"verdict_day": "INCOMPLETE", "verdict_month": "INCOMPLETE", "verdict_mdd": "INCOMPLETE",
               "verdict": "INCOMPLETE"}}),
 sub("C18c", [dep("c18c_d", "D1", 1000000), mark("c18c_m1", "D1"), wd("c18c_w", "D2", 1000000),
              mark("c18c_m2", "D2"), mark("c18c_m3", "D3")],
     {"status": "OK", "cash": 0, "navs": {D["D1"]: {"nav": 1000000}, D["D2"]: {"nav": 0}, D["D3"]: {"nav": 0}},
      "returns": {D["D1"]: "0", D["D2"]: None, D["D3"]: None},
      "return_reasons": {D["D2"]: "NONPOSITIVE_BASE", D["D3"]: "NONPOSITIVE_BASE"},
      "risk": {"verdict": "INCOMPLETE"}}),
 sub("C18d", [dep("c18d_d", "D1", 1000000), fill("c18d_f", "D1", "09:10", "BUY", 10, 10000),
              price("c18d_p1", "D1", {"S1": 10000}), mark("c18d_m1", "D1"),
              ev("c18d_ca", "CORP_ACTION", "D2", "08:00", security_id="S1", kind="SPLIT"),
              price("c18d_p2", "D2", {"S1": 5000}), mark("c18d_m2", "D2")],
     {"status": "OK", "navs": {D["D1"]: {"nav": 999900},
                               D["D2"]: {"nav": None, "reason": "UNSUPPORTED_CORP_ACTION:S1"}}}),
])
# C19
case("C19", [sub("C19", [dep("c19_d", "D1", 1000000),
    fill("c19_fa", "D1", "09:10", "BUY", 50, 10000, trade="A1", strat="A"),
    fill("c19_fb", "D1", "09:20", "BUY", 30, 10000, trade="B1", strat="B"),
    price("c19_p1", "D1", {"S1": 10000}), mark("c19_m1", "D1"),
    fill("c19_fa2", "D2", "10:00", "SELL", 50, 11000, trade="A1", strat="A"),
    price("c19_p2", "D2", {"S1": 11000}), mark("c19_m2", "D2"),
    fill("c19_fa3", "D3", "10:00", "SELL", 10, 11000, trade="A1", strat="A"),
    price("c19_p3", "D3", {"S1": 11000}), mark("c19_m3", "D3"),
    price("c19_p4", "D4", {"S1": 11000}), mark("c19_m4", "D4")],
    {"status": "OK", "cash": 747550, "settled_cash": 747550, "positions": {"S1": 30},
     "navs": {D["D1"]: {"nav": 999200, "cash_td": 199200, "settled": 1000000, "payable": 800800, "receivable": 0},
              D["D2"]: {"nav": 1077550, "cash_td": 747550, "settled": 1000000, "payable": 800800, "receivable": 548350},
              D["D3"]: {"nav": 1077550, "cash_td": 747550, "settled": 199200, "payable": 0, "receivable": 548350},
              D["D4"]: {"nav": 1077550, "cash_td": 747550, "settled": 747550, "payable": 0, "receivable": 0}},
     "trades": {"A1": {"realized": 47850, "open_qty": 0}, "B1": {"realized": 0, "open_qty": 30, "open_cost": 300300}},
     "attribution": {"A": 47850, "B": 29700},
     "rejections": [{"event_id": "c19_fa3", "reason": "OVERSELL"}]})])
# C20
c20cfg = {"cost": {"buy_fee": "0.00015", "sell_fee": "0.00015", "sell_tax": "0.002"}}
def c20(sid, cap, exp):
    return sub(sid, [dep(sid + "_d", "D1", cap),
                     mintent(sid + "_i", "D1", "09:00", "o1", "S1", 12345, cap // 10, cap, trade="T1"),
                     price(sid + "_p1", "D1", {"S1": 12345}), mark(sid + "_m1", "D1"),
                     ev(sid + "_s", "ORDER_INTENT", "D2", "10:00", order_id="o2", trade_id="T1", strategy_id="A",
                        security_id="S1", side="SELL", price=13000, sizing="ALL_HELD", model_fill=True),
                     price(sid + "_p2", "D2", {"S1": 13000}), mark(sid + "_m2", "D2")], exp, config=c20cfg)
case("C20", [
 c20("C20_10M", 10000000, {"status": "OK", "cash": 10050016, "positions": {},
     "sizing": [{"order_id": "o1", "qty": 80}],
     "fills": [{"notional": 987600, "fee": 148, "tax": 0}, {"notional": 1040000, "fee": 156, "tax": 2080}],
     "navs": {D["D1"]: {"nav": 9999852, "cash_td": 9012252}, D["D2"]: {"nav": 10050016}}}),
 c20("C20_100M", 100000000, {"status": "OK", "cash": 100505785, "positions": {},
     "sizing": [{"order_id": "o1", "qty": 809}],
     "fills": [{"notional": 9987105, "fee": 1498, "tax": 0}, {"notional": 10517000, "fee": 1578, "tax": 21034}],
     "navs": {D["D1"]: {"nav": 99998502, "cash_td": 90011397}, D["D2"]: {"nav": 100505785}}}),
])
assert len(cases) == 20, len(cases)
asis = [
 {"id": "X8", "pairs_with": "C8", "days": ["2026-01-02", D["D1"], D["D2"]],
  "ledger": [[s, D["D1"], D["D2"], 0.0, 1] for s in secs],
  "prices": {s: {"rows": [[D["D1"], 1000], [D["D2"], 1000]]} for s in secs},
  "expect_defect": {"min_cash_rel": "-0.2", "max_exposure": "1.2"}},
 {"id": "X9", "pairs_with": "C9", "days": ["2026-01-02", D["D1"]],
  "ledger": [["S1", D["D1"], D["D1"], 2.0, 10]], "prices": {"S1": {"rows": [[D["D1"], 5000]]}},
  "expect_defect": {"returns": ["0", "0"], "kernel_day_return": "0.00797"}},
 {"id": "X14", "pairs_with": "C14", "days": ["2026-01-02", D["D1"], D["D2"]],
  "ledger": [["S1", D["D1"], D["D2"], 3.0, 10]],
  "prices": {"S1": {"rows": [[D["D1"], 5000], [D["D2"], 5150]]}},
  "expect_defect": {"returns": ["0", "0", "0.03"], "kernel_total_return": "12955/1000000"}},
]
json.dump({"task": "REPLAY-0001", "input_pr": 16, "input_head": "49d5bafae17c02f7ffc4f7dd2a2162cca7de214c",
           "note": "합성 골든. 비용률은 시험용 값이며 실제 국내 거래비용이 아님. 기대값은 PREREG-LOCK.md 표와 같음(손셈).",
           "cases": cases, "asis_contrast": asis}, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print("cases", len(cases), "subs", sum(len(c["subs"]) for c in cases))
