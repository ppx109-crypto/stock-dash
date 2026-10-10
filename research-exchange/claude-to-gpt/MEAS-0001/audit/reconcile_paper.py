"""MEAS-0001 A — 스냅샷의 모의 기록 실제 대사(값 공개 없이 개수 · 일치 여부만). python reconcile_paper.py <저장소> <스냅샷> <out.json>"""
import json
import subprocess
import sys

REPO, SNAP, OUT = sys.argv[1:4]


def show(path):
    r = subprocess.run(["git", "-C", REPO, "show", f"{SNAP}:{path}"], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


res = {"snapshot": SNAP, "strategies": {}}
for name, book, state in (("1D", "daily-live/paper-orders.json", "daily-live/state.json"), ("15m", "m15-live/paper-orders.json", "m15-live/state.json"),
                          ("H1", "hourly-live/paper-orders.json", "hourly-live/state.json"), ("engine+inverse", "idle-live/paper-orders.json", "idle-live/state.json"),
                          ("basket", "basket-live/paper-orders.json", "basket-live/state.json")):
    b, s = show(book), show(state)
    r = {"kis_paper_order_book": "있음" if b is not None else "없음", "practice_state": "있음" if s is not None else "없음"}
    if b is not None:
        orders = b.get("orders") or []
        acc = [o for o in orders if str(o.get("status", "")).startswith("접수")]
        rej = [o for o in orders if str(o.get("status", "")).startswith("실패")]
        net = {}
        for o in acc:
            net[o["code"]] = net.get(o["code"], 0) + (o["qty"] if o["side"] == "buy" else -o["qty"])
        held = {k: v for k, v in (b.get("held") or {}).items() if v}
        r.update({"orders": len(orders), "accepted": len(acc), "rejected": len(rej), "reduced_by_buyable": sum(1 for o in acc if "줄임" in str(o.get("status"))),
                  "held_equals_accepted_net_qty": net == held, "first_order_at": min((o["at"] for o in orders), default=None),
                  "last_order_at": max((o["at"] for o in orders), default=None),
                  "fill_records": None, "fill_reason": "체결 조회 기록 없음 — 장부는 '접수' 때 수량을 더함(paper_trade.py:405 · idle_live.py:402)",
                  "cash_reconciliation": None, "cash_reason": "예수금 · 잔고 스냅샷 저장 없음(broker_kis.py:736-742 · 실행 안에서만 씀)",
                  "fees_taxes": None, "nav": None})
        if s is not None:
            pos = s.get("positions") or {}
            r["state_positions_match_held_codes"] = set(pos) == set(held)
            r["state_price_is_order_quote_not_fill"] = all(p.get("price") == next((o["price"] for o in acc if o["code"] == c), None) for c, p in pos.items())
    if s is not None:
        r["practice_positions"] = len(s.get("positions") or {})
        r["practice_closed"] = len(s.get("closed") or [])
        r["practice_last"] = s.get("last_day") or s.get("last_bar")
    res["strategies"][name] = r
open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps(res, ensure_ascii=False)[:1800])
