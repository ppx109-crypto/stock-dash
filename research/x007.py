"""재현 시험(사용자 2026-10-02 "운영에서 연구의 수익률 · 낙폭 값이 나오게") — 고친 운영 1일봉 판단(daily_live.decide · settle ·
kin_checker · exit_decision)을 과거 날마다 그대로 돌려, 연구 엔진(lab.run · 새 82회차 기준 · 순서 흔들기 없는 한 판)과
매매 · 연수익 · 골이 같은지 봄. '지금 값' 자리에 그날 종가를 넣음(운영은 15:20 값 — 그 차이는 일봉 새 84회차에서 95 ~ 99% 같음).
Q_PART=1 앞(2017 ~ 2020) · 2 뒤(2021 ~)."""
import bisect
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl
import lab
import rule
import daily_live as D

part = os.environ.get("Q_PART", "2")
pool, since = (nrl.early, rule.SINCE) if part == "1" else (nrl.inside, rule.MID)
SLOTS = nrl.SLOTS

# ── 연구: 순서 흔들기 없는 한 판(wobble의 '그대로')
res = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, slots=SLOTS, since=since, apart=nrl.kin, realistic=True,
              cap=130, detail=True, size=nrl.BASE_SIZE, rank=rule.order)

# ── 운영 판단으로 같은 날들을 돎
lane = nrl.lanes
picks = {}
for r in pool:
    if r["date"] >= since and nrl.BASE_HOLD(r):
        picks.setdefault(r["date"], []).append(r)
last = max(r["date"] for r in pool)
days = [d for d in lab.trading_days(lane) if min(picks) <= d <= last]
DATES = {c: lane[c]["날"] for c in lane}
steps = lab.moves(nrl.prices)
D.size_of = lambda c: c["칸"]                       # 크기는 연구 행의 값(nrl.BASE_SIZE)을 그대로 넘김
state = {"positions": {}, "closed": []}


def at(c, day):
    k = bisect.bisect_right(DATES[c], day) - 1
    return k if k >= 0 and DATES[c][k] == day else None


for day in days:
    held = state["positions"]
    todays = sorted(picks.get(day, []), key=rule.order)
    codes = set(held) | {r["code"] for r in todays}
    idx, close, rate = {}, {}, {}
    for c in codes:
        k = at(c, day)
        if k is None:
            continue
        cl = lane[c]["closes"]
        idx[c], close[c] = k, cl[k]
        rate[c] = (cl[k] / cl[k - 1] - 1) * 100 if k > 0 and cl[k - 1] else 0.0
        # 연구의 상한가 · 하한가 문턱(제한폭 × 0.95)에 맞춰 운영의 29.5% 판정이 같은 날 걸리게 값만 옮김
        edge = lab.limit_of(day) * 0.95 * 100
        if rate[c] >= edge:
            rate[c] = 30.0
        elif rate[c] <= -edge:
            rate[c] = -30.0
        else:
            rate[c] = max(min(rate[c], 29.0), -29.0)
    aligned = {c: bool(nrl.shape[c]["정배열"][idx[c]]) for c in held if c in idx}
    cands = [{"code": r["code"], "name": r["code"], "추세문": bool(rule.holds(r)), "추세 기울기": r.get("추세 기울기") or 0,
              "칸": max(int(nrl.BASE_SIZE(r)), 1)} for r in todays if r["code"] in idx]
    kin_ok = D.kin_checker(steps, idx, DATES, {c: p.get("bought") for c, p in held.items()})
    sells, buys = D.decide(state, cands, close, aligned, rate, kin_ok)
    D.settle(state, day, sells, buys, close)

mine = [(t["손익"], t["칸"]) for t in state["closed"]]
years = int(days[-1][:4]) - int(days[0][:4]) + 1
w_live = [g * k for g, k in mine]
live = {"매매": len(mine), "연수익": round(sum(w_live) / SLOTS / years, 2), "최대낙폭": round(lab.deepest(w_live, SLOTS), 1)}
rk = {(t["code"], str(t["산 날"])) for t in res["매매목록"]}
lk = {(t["code"], str(t["산 날"])) for t in state["closed"]}
print(f"== 재현 시험 x007({'앞 2017 ~ 2020' if part == '1' else '뒤 2021 ~'}): 연구 엔진 vs 고친 운영 판단 ==", flush=True)
print(f"  연구 lab.run(한 판): 매매 {res['매매']} · 연 {res['연수익']}% · 골 {res['최대낙폭']}%", flush=True)
print(f"  운영 판단 재현     : 매매 {live['매매']} · 연 {live['연수익']}% · 골 {live['최대낙폭']}% · 끝에 들고 있는 종목 {len(state['positions'])}", flush=True)
print(f"  같은 (종목 · 산 날): {len(rk & lk)} · 연구에만 {len(rk - lk)} · 운영에만 {len(lk - rk)}", flush=True)
only_r = sorted(rk - lk, key=lambda x: x[1])[:8]
only_l = sorted(lk - rk, key=lambda x: x[1])[:8]
print("  연구에만(앞 8): " + " · ".join(f"{c} {d}" for c, d in only_r), flush=True)
print("  운영에만(앞 8): " + " · ".join(f"{c} {d}" for c, d in only_l), flush=True)
print("끝", flush=True)
