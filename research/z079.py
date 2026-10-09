"""D1-CASH-BASELINE-0003 · H2 — '한 종목 최대 40%'를 들고 있는 동안에도 지킴(넘는 몫을 종가에 덜어 팖)(사전등록: research-exchange/claude-to-gpt/D1-CASH-BASELINE-0003/PREREG-H2.md).
V0 = 현금 한도 매수(z078과 같음 · 덜어내기 없음) · V1 = V0 + 날마다 종가로 40% 넘는 몫 덜어냄. 매매 줄(엔진)은 두 판이 같음.
python3 research/z079.py   (Z_OUT 환경 변수)"""
import bisect
import json
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
CAP = 0.40          # 사용자 결정 2026-09-29 '한 종목 최대 40%'
TRIM_COST = 0.0025  # 덜어낼 때 판 금액의 0.25%(lab.COST 왕복 어림을 매도 한 번에 다 매김 · 보수적)
CUTS = {"앞": ("20190630",), "뒤": ("20231231", "20250630")}


def account(led, still, start, end, cap=None, lanes=None, want_navs=False):
    """z078.cash_account와 같은 셈 + cap이 있으면 매도 뒤 · 매수 전에 종목별 평가액이 cap × NAV를 넘는 몫을 그날 종가에 팖."""
    lanes = lanes or nrl.lanes
    pos = [dict(t, open=False) for t in led] + [dict(t, open=True, 행=t.get("행")) for t in still]
    codes = {t["code"] for t in pos}
    close = {c: dict(zip(lanes[c]["날"], lanes[c]["closes"])) for c in codes}
    days = [d for d in lab.trading_days(lanes) if start <= d <= end]
    buys, sells = defaultdict(list), defaultdict(list)
    for k, t in enumerate(pos):
        buys[t["산 날"]].append(k)
        if not t["open"]:
            sells[t["판 날"]].append(k)
    order = lambda k: (rule.order(pos[k]["행"]) if pos[k].get("행") else 0, pos[k]["code"])
    cash, units, spent, last = 1.0, {}, {}, {}
    navs, capped, trims, trim_value = [], 0, 0, 0.0
    for d in days:
        for c in codes:
            if d in close[c]:
                last[c] = close[c][d]
        for k in sells[d]:
            cash += spent.pop(k) * (1 + pos[k]["손익"] / 100)
            del units[k]
        if cap is not None and units:
            nav = cash + sum(u * last[pos[k]["code"]] for k, u in units.items())
            by = defaultdict(list)
            for k in units:
                by[pos[k]["code"]].append(k)
            for c, ks in by.items():
                val = sum(units[k] * last[c] for k in ks)
                if val > cap * nav + 1e-12:
                    f = cap * nav / val
                    sold = val * (1 - f)
                    cash += sold * (1 - TRIM_COST)
                    for k in ks:
                        units[k] *= f
                        spent[k] *= f
                    trims += 1
                    trim_value += sold / nav
        nav = cash + sum(u * last[pos[k]["code"]] for k, u in units.items())
        for k in sorted(buys[d], key=order):
            want = pos[k]["자리"] / nrl.SLOTS * nav
            pay = min(want, max(cash, 0.0))
            if pay < want - 1e-12:
                capped += 1
            units[k], spent[k] = pay / close[pos[k]["code"]][d], pay
            cash -= pay
        navs.append((d, cash + sum(u * last[pos[k]["code"]] for k, u in units.items())))
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
           "mdd_daily": [mdd[0], round(mdd[1] * 100, 3)], "capped_buys": capped, "trims": trims,
           "trim_value_sum_nav": round(trim_value, 3), "days": len(navs)}
    return (out, navs) if want_navs else out


def cut_check(g, T, cap):
    """T 뒤에 판 줄을 'T에 아직 보유'로 바꾸고 일봉을 T까지 잘라 다시 센 NAV가 T까지 원래와 같은지."""
    _, full = account(g["led"], g["still"], g["since"], g["end"], cap, want_navs=True)
    led = [t for t in g["led"] if t["판 날"] <= T]
    still = [t for t in g["led"] if t["산 날"] <= T < t["판 날"]] + [t for t in g["still"] if t["산 날"] <= T]
    lanes_cut = {}
    for c, one in nrl.lanes.items():
        k = bisect.bisect_right(one["날"], T)
        lanes_cut[c] = {"날": one["날"][:k], "closes": one["closes"][:k]}
    _, cut = account(led, still, g["since"], T, cap, lanes=lanes_cut, want_navs=True)
    a = [v for d, v in full if d <= T]
    b = [v for d, v in cut]
    ok = len(a) == len(b) > 0 and all(abs(x - y) < 1e-12 for x, y in zip(a, b))
    return {"T": T, "days": len(a), "ok": ok, "max_diff": max((abs(x - y) for x, y in zip(a, b)), default=None)}


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def side(which, base_json):
    gs = z078.ledgers(which)
    res = {"V0": [], "V1": []}
    for g in gs:
        for name, cap in (("V0", None), ("V1", CAP)):
            a = account(g["led"], g["still"], g["since"], g["end"], cap)
            res[name].append({"seed": g["seed"], **a})
    # V0이 z078 기준 결과와 똑같은지(같은 셈인지) 확인
    b0 = [x["cagr"] for x in base_json[which]["seeds"]]
    same_v0 = [x["cagr"] for x in res["V0"]] == b0
    summ = {}
    for name in res:
        xs = res[name]
        summ[name] = {"cagr_median": med([x["cagr"] for x in xs]),
                      "cagr_spread": round(max(x["cagr"] for x in xs) - min(x["cagr"] for x in xs), 2),
                      "worst_day": min((x["worst_day"] for x in xs), key=lambda v: v[1]),
                      "worst_month": min((x["worst_month"] for x in xs), key=lambda v: v[1]),
                      "mdd": min((x["mdd_daily"] for x in xs), key=lambda v: v[1]),
                      "trims_median": med([x["trims"] for x in xs])}
    cuts = [cut_check(gs[0], T, CAP) for T in CUTS[which]]
    return {"seeds": res, "summary": summ, "v0_equals_baseline": same_v0, "cut_check_V1_seed0": cuts}


def main():
    base_json = json.loads((OUT / "baseline.json").read_text())
    out = {"task": "D1-CASH-BASELINE-0003 H2", "cap": CAP, "trim_cost": TRIM_COST}
    for which in ("앞", "뒤"):
        out[which] = side(which, base_json)
        for name in ("V0", "V1"):
            s = out[which]["summary"][name]
            print(f"[{which}] {name} 연복리 {s['cagr_median']}(폭 {s['cagr_spread']}) · 하루 최악 {s['worst_day']} · 달 최악 {s['worst_month']} · "
                  f"고점 대비 {s['mdd']} · 덜어낸 날(가운데) {s['trims_median']}", flush=True)
        print(f"[{which}] V0 = 기준(z078) 같음 {out[which]['v0_equals_baseline']} · 자르기 {out[which]['cut_check_V1_seed0']}", flush=True)
    v1 = {w: out[w]["summary"]["V1"] for w in ("앞", "뒤")}
    v0 = {w: out[w]["summary"]["V0"] for w in ("앞", "뒤")}
    limits = all(v1[w]["worst_day"][1] > -15 and v1[w]["worst_month"][1] > -15 for w in v1)
    positive = all(v1[w]["cagr_median"] > 0 for w in v1)
    cuts_ok = all(c["ok"] for w in ("앞", "뒤") for c in out[w]["cut_check_V1_seed0"])
    same = all(out[w]["v0_equals_baseline"] for w in ("앞", "뒤"))
    better = all(v1[w]["worst_day"][1] >= v0[w]["worst_day"][1] and v1[w]["worst_month"][1] >= v0[w]["worst_month"][1] for w in v1)
    if not same:
        verdict = "CODE_MISMATCH(V0이 기준과 다름 — 판정 안 함)"
    elif limits and positive and cuts_ok:
        verdict = "ADOPT_CANDIDATE(조건부 역사 비교 · 사용자 결정)"
    elif better:
        verdict = "NOT_ENOUGH(손실은 줄었으나 한도 밖)"
    else:
        verdict = "REJECTED"
    out.update({"limits_ok": limits, "positive": positive, "cuts_ok": cuts_ok, "better_than_v0": better, "verdict": verdict})
    (OUT / "h2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"판정: 한도 {limits} · 연복리 > 0 {positive} · 자르기 {cuts_ok} · V0보다 손실 줄음 {better} → {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
