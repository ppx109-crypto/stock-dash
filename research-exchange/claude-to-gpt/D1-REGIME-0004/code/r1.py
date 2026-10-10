# R1: C0 장치 이웃(창 10 · 40일 · 40% 덜어내기 뺌) — 사전등록 PREREG-R1.md
import json, sys; sys.path.insert(0, "/home/user/stock-dash"); sys.path.insert(0, "/home/user/stock-dash/research")
import z080, z081
V = z080.VOL_DAY * 2
CASES = {"C0(창20 · 40%)": (20, {"cap": .4, "vol": V}), "창10": (10, {"cap": .4, "vol": V}), "창40": (40, {"cap": .4, "vol": V}), "40% 뺌": (20, {"vol": V})}
out = {}
for which in ("앞", "뒤"):
    gs = z081.ledgers(which, z081.holds_b0); out[which] = {}
    for name, (look, kw) in CASES.items():
        z080.LOOK = look
        r = z081.evaluate(gs, kw); out[which][name] = {k: r[k] for k in ("cagr", "cagr_spread", "worst_day", "worst_month", "mdd", "regime", "down_side", "down_side_spread")}
        print(f"[{which}] {name}: 연복리 {r['cagr']}(폭 {r['cagr_spread']}) · 하루 {r['worst_day']} · 달 {r['worst_month']} · 장별 {r['regime']} · 횡보+하락 {r['down_side']}(폭 {r['down_side_spread']})", flush=True)
    z080.LOOK = 20
ok = True
for w in out:
    base = out[w]["C0(창20 · 40%)"]
    for name, r in out[w].items():
        ok &= r["worst_day"][1] > -15 and r["worst_month"][1] > -15
        if name != "C0(창20 · 40%)":
            ok &= abs(r["down_side"] - base["down_side"]) <= base["down_side_spread"]
out["pass"] = ok
json.dump(out, open("/home/user/stock-dash/research-exchange/claude-to-gpt/D1-REGIME-0004/evidence/r1.json", "w"), ensure_ascii=False, indent=1)
print("R1 통과" if ok else "R1 실패(뾰족한 곳 있음)", flush=True)
