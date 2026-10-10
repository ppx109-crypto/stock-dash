"""D1-CASH-BASELINE-0003 · H3 — H2(보유 중 40%) 위에 계좌 흔들림 상한(하루 1.0911% = 한 달 5% = 사용자 한도 15% ÷ 3)(사전등록 PREREG-H3.md).
V0 현금 한도 매수 · V1 = V0 + 40% 덜어내기 · V2 = V1 + 흔들림 상한. 매매 줄(엔진)은 세 판이 같음.
python3 research/z080.py   (Z_OUT 환경 변수)"""
import bisect
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
import z078  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-CASH-BASELINE-0003/evidence"))
CAP = 0.40
COST = 0.0025
VOL_DAY = 0.05 / math.sqrt(21)      # 한 달 5%(= 15% ÷ 3)를 하루로 = 1.0911%
LOOK = 20
CUTS = {"앞": ("20190630",), "뒤": ("20231231", "20250630")}


def account(led, still, start, end, cap=None, vol=None, lanes=None, want_navs=False):
    lanes = lanes or nrl.lanes
    pos = [dict(t, open=False) for t in led] + [dict(t, open=True, 행=t.get("행")) for t in still]
    codes = {t["code"] for t in pos}
    series = {c: (lanes[c]["날"], lanes[c]["closes"]) for c in codes}
    close = {c: dict(zip(*series[c])) for c in codes}
    days = [d for d in lab.trading_days(lanes) if start <= d <= end]
    buys, sells = defaultdict(list), defaultdict(list)
    for k, t in enumerate(pos):
        buys[t["산 날"]].append(k)
        if not t["open"]:
            sells[t["판 날"]].append(k)
    order = lambda k: (rule.order(pos[k]["행"]) if pos[k].get("행") else 0, pos[k]["code"])
    cash, units, spent, last = 1.0, {}, {}, {}
    navs, trims, vol_cuts, exp_min = [], 0, 0, 1.0

    def held_value():
        return sum(u * last[pos[k]["code"]] for k, u in units.items())

    def sell_share(ks, f):
        nonlocal cash
        sold = sum(units[k] * last[pos[k]["code"]] for k in ks) * (1 - f)
        cash += sold * (1 - COST)
        for k in ks:
            units[k] *= f
            spent[k] *= f

    def asset_sigma(d):
        """지금 보유 비중으로 오늘까지 LOOK거래일 하루 수익률 표준편차(그 종목들 종가만)."""
        w = defaultdict(float)
        for k, u in units.items():
            w[pos[k]["code"]] += u * last[pos[k]["code"]]
        tot = sum(w.values())
        if tot <= 0:
            return None
        rets = []
        for c, v in w.items():
            ds, cs = series[c]
            i = bisect.bisect_right(ds, d) - 1
            if i - LOOK < 0:
                return None
            rets.append((v / tot, [cs[j] / cs[j - 1] - 1 for j in range(i - LOOK + 1, i + 1)]))
        port = [sum(wt * r[t] for wt, r in rets) for t in range(LOOK)]
        m = sum(port) / LOOK
        return math.sqrt(sum((x - m) ** 2 for x in port) / (LOOK - 1))

    for d in days:
        for c in codes:
            if d in close[c]:
                last[c] = close[c][d]
        for k in sells[d]:
            cash += spent.pop(k) * (1 + pos[k]["손익"] / 100)
            del units[k]
        if cap is not None and units:
            nav = cash + held_value()
            by = defaultdict(list)
            for k in units:
                by[pos[k]["code"]].append(k)
            for c, ks in by.items():
                val = sum(units[k] * last[c] for k in ks)
                if val > cap * nav + 1e-12:
                    sell_share(ks, cap * nav / val)
                    trims += 1
        allowed = 1.0
        if vol is not None and units:
            s = asset_sigma(d)
            if s and s > 0:
                allowed = min(1.0, vol / s)
            nav = cash + held_value()
            h = held_value()
            if h > allowed * nav + 1e-12:
                sell_share(list(units), allowed * nav / h)
                vol_cuts += 1
        nav = cash + held_value()
        for k in sorted(buys[d], key=order):
            room = max(0.0, allowed * nav - held_value()) if vol is not None else float("inf")
            pay = max(0.0, min(pos[k]["자리"] / nrl.SLOTS * nav, cash, room))
            units[k], spent[k] = pay / close[pos[k]["code"]][d], pay
            cash -= pay
        nav = cash + held_value()
        exp_min = min(exp_min, held_value() / nav) if units else exp_min
        navs.append((d, nav))
    rets = [(navs[i][0], navs[i][1] / navs[i - 1][1] - 1) for i in range(1, len(navs))]
    month = defaultdict(lambda: 1.0)
    for d, r in rets:
        month[d[:6]] *= 1 + r
    peak, mdd = navs[0][1], (navs[0][0], 0.0)
    for d, v in navs:
        peak = max(peak, v)
        if v / peak - 1 < mdd[1]:
            mdd = (d, v / peak - 1)
    years = len(navs) / 245.0
    wd = min(rets, key=lambda x: x[1])
    wm = min(month.items(), key=lambda x: x[1])
    out = {"cagr": round((navs[-1][1] ** (1 / years) - 1) * 100, 2), "end_nav": round(navs[-1][1], 4),
           "worst_day": [wd[0], round(wd[1] * 100, 3)], "worst_month": [wm[0], round((wm[1] - 1) * 100, 3)],
           "mdd_daily": [mdd[0], round(mdd[1] * 100, 3)], "trims": trims, "vol_cuts": vol_cuts, "days": len(navs)}
    return (out, navs) if want_navs else out


def cut_check(g, T, **kw):
    _, full = account(g["led"], g["still"], g["since"], g["end"], want_navs=True, **kw)
    led = [t for t in g["led"] if t["판 날"] <= T]
    still = [t for t in g["led"] if t["산 날"] <= T < t["판 날"]] + [t for t in g["still"] if t["산 날"] <= T]
    lanes_cut = {}
    for c, one in nrl.lanes.items():
        k = bisect.bisect_right(one["날"], T)
        lanes_cut[c] = {"날": one["날"][:k], "closes": one["closes"][:k]}
    _, cut = account(led, still, g["since"], T, lanes=lanes_cut, want_navs=True, **kw)
    a = [v for d, v in full if d <= T]
    b = [v for d, v in cut]
    ok = len(a) == len(b) > 0 and all(abs(x - y) < 1e-12 for x, y in zip(a, b))
    return {"T": T, "days": len(a), "ok": ok, "max_diff": max((abs(x - y) for x, y in zip(a, b)), default=None)}


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


VARIANTS = {"V0": {}, "V1": {"cap": CAP}, "V2": {"cap": CAP, "vol": VOL_DAY}}


def side(which, prev):
    gs = z078.ledgers(which)
    res = {n: [] for n in VARIANTS}
    for g in gs:
        for n, kw in VARIANTS.items():
            res[n].append({"seed": g["seed"], **account(g["led"], g["still"], g["since"], g["end"], **kw)})
    same = ([x["cagr"] for x in res["V0"]] == [x["cagr"] for x in prev[which]["seeds"]["V0"]]
            and [x["cagr"] for x in res["V1"]] == [x["cagr"] for x in prev[which]["seeds"]["V1"]])
    summ = {n: {"cagr_median": med([x["cagr"] for x in xs]), "cagr_spread": round(max(x["cagr"] for x in xs) - min(x["cagr"] for x in xs), 2),
                "worst_day": min((x["worst_day"] for x in xs), key=lambda v: v[1]),
                "worst_month": min((x["worst_month"] for x in xs), key=lambda v: v[1]),
                "mdd": min((x["mdd_daily"] for x in xs), key=lambda v: v[1]),
                "vol_cuts_median": med([x["vol_cuts"] for x in xs])} for n, xs in res.items()}
    cuts = [cut_check(gs[0], T, **VARIANTS["V2"]) for T in CUTS[which]]
    return {"seeds": res, "summary": summ, "v0_v1_equal_h2": same, "cut_check_V2_seed0": cuts}


def main():
    prev = json.loads((OUT / "h2.json").read_text())
    out = {"task": "D1-CASH-BASELINE-0003 H3", "vol_day": VOL_DAY, "look": LOOK, "cap": CAP, "cost": COST}
    for which in ("앞", "뒤"):
        out[which] = side(which, prev)
        for n in VARIANTS:
            s = out[which]["summary"][n]
            print(f"[{which}] {n} 연복리 {s['cagr_median']}(폭 {s['cagr_spread']}) · 하루 최악 {s['worst_day']} · 달 최악 {s['worst_month']} · "
                  f"고점 대비 {s['mdd']} · 흔들림으로 줄인 날(가운데) {s['vol_cuts_median']}", flush=True)
        print(f"[{which}] V0 · V1 = H2 결과와 같음 {out[which]['v0_v1_equal_h2']} · 자르기 {out[which]['cut_check_V2_seed0']}", flush=True)
    v2 = {w: out[w]["summary"]["V2"] for w in ("앞", "뒤")}
    v1 = {w: out[w]["summary"]["V1"] for w in ("앞", "뒤")}
    same = all(out[w]["v0_v1_equal_h2"] for w in ("앞", "뒤"))
    limits = all(v2[w]["worst_day"][1] > -15 and v2[w]["worst_month"][1] > -15 for w in v2)
    positive = all(v2[w]["cagr_median"] > 0 for w in v2)
    cuts_ok = all(c["ok"] for w in ("앞", "뒤") for c in out[w]["cut_check_V2_seed0"])
    better = all(v2[w]["worst_day"][1] >= v1[w]["worst_day"][1] and v2[w]["worst_month"][1] >= v1[w]["worst_month"][1] for w in v2)
    if not same:
        verdict = "CODE_MISMATCH(V0 · V1이 H2와 다름 — 판정 안 함)"
    elif limits and positive and cuts_ok:
        verdict = "ADOPT_CANDIDATE(조건부 역사 비교 · 사용자 결정)"
    elif better:
        verdict = "NOT_ENOUGH(손실은 줄었으나 한도 밖)"
    else:
        verdict = "REJECTED"
    out.update({"limits_ok": limits, "positive": positive, "cuts_ok": cuts_ok, "better_than_v1": better, "verdict": verdict})
    (OUT / "h3.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"판정: 한도 {limits} · 연복리 > 0 {positive} · 자르기 {cuts_ok} · V1보다 손실 줄음 {better} → {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
