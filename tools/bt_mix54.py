"""MIX-0054 백테스트 재생(주문 없음): 10-12부터, 판단은 운영 코드 함수 그대로 · 사고팖은 그날 종가 · 비용 포함.
쓰는 법: python3 tools/bt_mix54.py <main 펼친 폴더> tools/bt_mix54_start   (시작 장부 = 10-12 직전 운영 장부 사본)
사용자 2026-11-03: "모의투자가 중간에 멈췄지만 안 멈췄다는 가정하에 결과값" · "이 누적 수익률 결과대로 계속 진행하자".
- 1일봉: reconcile/<날>.json의 '백테스트 판단'(운영 판단 코드) — 이 기간 사기 · 팔기가 모두 비어 있어 현금.
- 빈칸 엔진 · 코스닥 인버스: idle_live.step · 사건 바구니: basket_live.step · 레버리지 봇: overlay_live.states/TARGET/needs_rebalance.
- 레버리지 봇 크기 = min(목표 몫, 바탕 현금 비율)(운영 target_qty와 같음) · 바탕 봇이 돈이 모자라면 덧붙임을 먼저 팖(운영 yield_for).
- 계좌 흔들림 상한: 이 기간 운영 기록에서 덜어낸 날이 없어 셈에서 뺌.
- 비용: 사고팔 때 0.015% · 주식 팔 때 거래세 0.18%(ETF는 없음)."""
import os, sys, json, math
W, START = sys.argv[1], sys.argv[2]
os.chdir(W); sys.path[:0] = [W, os.path.join(W, "research")]
import numpy as np
import idle_live as IL, basket_live as BL, overlay_live as OV, study

FEE, TAX = 0.00015, 0.0018
etf_cache = {}
def etf(c):
    if c not in etf_cache:
        try:
            etf_cache[c] = {str(d): float(x) for d, x in json.load(open(f"etf-data/{c}.json")).get("closes", []) if x}
        except FileNotFoundError:
            etf_cache[c] = {}
    return etf_cache[c]
prices = study.load_prices(); names = {c: v["name"] for c, v in prices.items()}
stock = {c: {str(d): float(x) for d, x in v["rows"]} for c, v in prices.items()}
def close(code, day):
    return etf(code).get(day) or stock.get(code, {}).get(day)
is_etf = lambda c: bool(etf(c))

days_all = sorted(etf(IL.K200))
days = [d for d in days_all if "20261012" <= d]
pos_i = {d: k for k, d in enumerate(days_all)}

# 시작(10-08 장 끝): 실제 계좌 크기(약 1억 523만 원 · 한 주 단위로 사야 해서 실제 크기로 셈) · 빈칸 엔진 장부(코스닥 인버스 251340 36,116주) 그대로
NAV0 = 105_229_332.0
st_idle = json.load(open(os.path.join(START, "idle-live_state.json")))
st_b = json.load(open(os.path.join(START, "basket-live_state.json")))
p0 = close("251340", "20261008")
held = {"idle": {"251340": 36116}, "basket": {}, "ov": {}}
cash = NAV0 - 36116 * p0
ov = {"applied": None, "rebalanced_month": None}
log = []

def value(book, day):
    return sum(q * (close(c, day) or 0) for c, q in held[book].items())
def trade(book, code, side, qty, day):
    global cash
    px = close(code, day)
    if not px or qty <= 0:
        return 0.0
    amt = qty * px
    if side == "buy":
        cash -= amt * (1 + FEE)
        held[book][code] = held[book].get(code, 0) + qty
    else:
        cost = FEE + (0 if is_etf(code) else TAX)
        cash += amt * (1 - cost)
        held[book][code] = held[book].get(code, 0) - qty
        if held[book][code] <= 1e-9:
            held[book].pop(code)
    log.append((day, book, code, names.get(code, code), side, f"{amt / NAV0 * 100:.1f}%"))
    return amt

prev_nav = None
out = []
for day in days:
    i = pos_i[day]
    rec = json.load(open(f"reconcile/{day}.json")) if os.path.exists(f"reconcile/{day}.json") else {}
    b1 = rec.get("1일봉", {}).get("백테스트 판단", {})
    assert not b1.get("사기") and not b1.get("팔기"), f"{day} 1일봉 매매가 있음 — 이 재생은 1일봉 매매를 셈하지 않음"
    breadth = b1.get("breadth")
    nav = cash + value("idle", day) + value("basket", day) + value("ov", day)
    ov_val = value("ov", day)
    # 바탕 계좌(덧붙임을 빼고, 덧붙임에 쓴 돈은 현금으로 봄) — 운영 base_view와 같은 뜻
    cash_b = cash + ov_val
    # ── 사건 바구니(15:10) ──
    t0, before = days_all[i - 1], days_all[i - 2]
    react, inside = BL.reactions(prices, t0, before)
    ev = BL.todays_events(BL.load_events(), t0, before)
    ds = lambda d: (i - pos_i[d]) if d in pos_i else sum(1 for x in days_all[: i + 1] if x > d)
    npx = {c: close(c, day) for c in set([c for c, _ in ev] + list(held["basket"]))}
    bo, st_b, _ = BL.step(st_b, day, t0, ds, ev, react, inside, {c: math.floor(q) if q >= 1 else 1 for c, q in held["basket"].items()},
                         {k: v for k, v in npx.items() if v}, capital=nav * 0.3, avail=cash_b, names=names, others=set())
    for code, side, qty, _ in bo:
        if side == "sell":
            trade("basket", code, "sell", held["basket"].get(code, 0), day)
    for code, side, qty, _ in bo:
        if side == "buy":
            need = qty * close(code, day)
            if need > cash:                                   # 덧붙임이 자리를 내줌(운영 yield_for)
                sell_q = min(held["ov"].get(c, 0) for c in held["ov"]) if held["ov"] else 0
                for c in list(held["ov"]):
                    q = min(held["ov"][c], math.ceil((need - cash) / close(c, day) * 1.01))
                    trade("ov", c, "sell", q, day)
            trade("basket", code, "buy", qty, day)
    # ── 빈칸 엔진 · 코스닥 인버스(15:10) ──
    ov_val = value("ov", day); cash_b = cash + ov_val
    nav_b = cash_b + value("idle", day) + value("basket", day)
    used = value("basket", day) / nav_b if nav_b > 0 else 0.0
    px, now_price = {}, {}
    for code in IL.CODES:
        h = [x for d, x in sorted(etf(code).items()) if d < day]
        c = etf(code).get(day)
        if c:
            now_price[code] = c
        if c and len(h) >= 25:
            px[code] = np.array(h[-400:] + [c])
    held_i = {c: max(1, math.floor(q)) for c, q in held["idle"].items()}
    io, st_idle, _ = IL.step(st_idle, day, px, breadth, used, nav_b, cash_b, held_i, now_price, IL.week_end(day))
    for code, side, qty, _ in io:
        if side == "sell":
            trade("idle", code, "sell", held["idle"].get(code, 0), day)
    for code, side, qty, _ in io:
        if side == "buy":
            need = qty * close(code, day)
            if need > cash and held["ov"]:
                for c in list(held["ov"]):
                    q = min(held["ov"][c], math.ceil((need - cash) / close(c, day) * 1.01))
                    trade("ov", c, "sell", q, day)
            trade("idle", code, "buy", qty, day)
    # ── 레버리지 봇(15:13) ──
    rows = OV.closes(before=day)
    s = OV.states(rows)[rows[-1][0]] if rows else "횡보"
    nav = cash + value("idle", day) + value("basket", day) + value("ov", day)
    if OV.needs_rebalance(ov, s, day):
        for c in list(held["ov"]):
            if OV.TARGET[s][0] != c:
                trade("ov", c, "sell", held["ov"][c], day)
        code, fe = OV.TARGET[s]
        if code:
            cash_b = cash + value("ov", day)
            nav_b = cash_b + value("idle", day) + value("basket", day)
            f = min(fe, max(0.0, cash_b) / nav_b)
            want = math.floor(f * nav / close(code, day))
            have = held["ov"].get(code, 0)
            if want > have:
                trade("ov", code, "buy", want - have, day)
            elif want < have:
                trade("ov", code, "sell", have - want, day)
        ov.update(applied=s, rebalanced_month=day[:6])
    nav = cash + value("idle", day) + value("basket", day) + value("ov", day)
    r = (nav / prev_nav - 1) if prev_nav else (nav / NAV0 - 1)
    out.append((day, nav, r, s, {b: {names.get(c, c): round(q * close(c, day) / nav * 100, 1) for c, q in held[b].items()} for b in held}))
    prev_nav = nav

print("날 | 계좌(10-08 끝 = 100으로 환산) | 하루 | 국면 | 든 것(계좌 대비 %)")
for d, nav, r, s, h in out:
    print(d, f"{nav / NAV0 * 100:8.3f}", f"{r * 100:+6.2f}%", s, {k: v for k, v in h.items() if v})
print("\n매매:")
for x in log:
    print(*x)
nav12 = out[0][1] / (1 + out[0][2])
print(f"\n10-12 ~ {out[-1][0]} 누적: {(out[-1][1] / NAV0 - 1) * 100:+.2f}% (10-08 끝 기준) · 최악 하루 {min(r for _, _, r, _, _ in out) * 100:+.2f}%")
peak, mdd = 0, 0
for _, nav, _, _, _ in out:
    peak = max(peak, nav); mdd = min(mdd, nav / peak - 1)
print(f"고점 대비 최대 하락 {mdd * 100:.2f}%")
k = etf("069500"); print(f"같은 기간 KODEX 200: {(k[out[-1][0]] / k['20261008'] - 1) * 100:+.2f}%")
