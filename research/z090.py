"""D1-BEAR-0011 — 하락장 피하기 3: 흔들림 상한으로 덜어낼 때 '절반만 팔고 그 돈으로 코스피200 인버스(114800)'.
바탕 = 사용자 선택 후보 '지금 규칙 + 흔들림 상한 × 2'(결함 고친 z087.account). 순 시장 노출(주식 − 인버스)은 B0과 같은 E × NAV로 맞춤.
- 허용 비중 E: z087과 같음(전날까지 값 · 주식 바구니의 20일 σ). 인버스는 σ 셈에 넣지 않음.
- 그날 종가: 매도 → 순 노출(주식 − 인버스) > E × NAV면 넘는 몫 x의 절반 s = x/2 를 주식에서 덜어내고, 판 돈(비용 뺀)으로 인버스를 삼(현금 그대로).
  순 노출 < E × NAV이고 인버스가 있으면 모자란 만큼(최대 전부) 인버스를 팖. → 새 매수(여유 = E × NAV − 순 노출).
- 비용: 주식 덜어내기 · 인버스 사고팔기 모두 0.25%(z087 COST와 같음 · ETF에는 넉넉함).
사전등록: research-exchange/claude-to-gpt/D1-BEAR-0011/PREREG.md · Z_TAG=raw|adj"""
import bisect
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import nrl  # noqa: E402
import rule  # noqa: E402
import z081  # noqa: E402
import z087  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-BEAR-0011/evidence"))
TAG = os.environ.get("Z_TAG", "raw")
INV = {str(d): float(c) for d, c in json.loads(Path("/home/user/stock-dash/etf-data/114800.json").read_text())["closes"] if c}
INVD = sorted(INV)
CAL, LOOK, COST, VOL = z087.CAL, z087.LOOK, z087.COST, z087.VOL


def inv_px(d):
    i = bisect.bisect_right(INVD, d) - 1        # 그날(없으면 앞 값)
    return INV[INVD[i]]


def account(led, still, start, end, hedge=True, want_navs=False):
    lanes = nrl.lanes
    pos = [dict(t, open=False) for t in led] + [dict(t, open=True, 행=t.get("행")) for t in still]
    codes = {t["code"] for t in pos}
    close = {c: dict(zip(lanes[c]["날"], lanes[c]["closes"])) for c in codes}
    days = [d for d in CAL if start <= d <= end]
    buys, sells = defaultdict(list), defaultdict(list)
    for k, t in enumerate(pos):
        buys[t["산 날"]].append(k)
        if not t["open"]:
            sells[t["판 날"]].append(k)
    order = lambda k: (rule.order(pos[k]["행"]) if pos[k].get("행") else 0, pos[k]["code"])
    cash, units, spent, last = 1.0, {}, {}, {}
    inv_u = 0.0
    navs, cuts, hedge_days, inv_turn = [], 0, 0, 0.0
    prev_val = {}

    def held():
        return sum(u * last[pos[k]["code"]] for k, u in units.items())

    for d in days:
        # 아침 판단: 전날까지 값만(z087과 같은 셈)
        allowed = 1.0
        if prev_val:
            tot = sum(prev_val.values())
            ci = bisect.bisect_left(CAL, d)
            win = CAL[ci - LOOK - 1:ci] if ci - LOOK - 1 >= 0 else None
            if tot > 0 and win:
                rets, ok = [], True
                by = defaultdict(float)
                for k, v in prev_val.items():
                    by[pos[k]["code"]] += v
                for c, v in by.items():
                    seq, lp = [], None
                    for x in win:
                        p = close[c].get(x, lp)
                        seq.append(p)
                        lp = p
                    if any(p is None for p in seq):
                        ok = False
                        break
                    rets.append((v / tot, [seq[j] / seq[j - 1] - 1 for j in range(1, LOOK + 1)]))
                if ok and rets:
                    port = [sum(w * r[t] for w, r in rets) for t in range(LOOK)]
                    m = sum(port) / LOOK
                    sd = math.sqrt(sum((x - m) ** 2 for x in port) / (LOOK - 1))
                    if sd > 0:
                        allowed = min(1.0, VOL / sd)
        # 그날 종가
        for c in codes:
            if d in close[c]:
                last[c] = close[c][d]
        ip = inv_px(d)
        for k in sells[d]:
            cash += spent.pop(k) * (1 + pos[k]["손익"] / 100)
            del units[k]
        h = held()
        v = inv_u * ip
        nav = cash + h + v
        net = h - v
        if net > allowed * nav + 1e-12 and h > 0:
            x = net - allowed * nav
            s = min(h, x / 2 if hedge else x)
            f = (h - s) / h
            for k in units:
                units[k] *= f
                spent[k] *= f
            got = s * (1 - COST)
            if hedge:
                b = got / (1 + COST)                 # 판 돈으로 인버스(현금 그대로)
                inv_u += b / ip
                inv_turn += b
            else:
                cash += got
            cuts += 1
        elif hedge and v > 0 and net < allowed * nav - 1e-12:
            u = min(v, allowed * nav - net)
            inv_u -= u / ip
            cash += u * (1 - COST)
            inv_turn += u
        h = held()
        v = inv_u * ip
        nav = cash + h + v
        hedge_days += v > 0
        for k in sorted(buys[d], key=order):
            room = max(0.0, allowed * nav - (h - v))
            pay = max(0.0, min(pos[k]["자리"] / nrl.SLOTS * nav, cash, room))
            units[k], spent[k] = pay / close[pos[k]["code"]][d], pay
            cash -= pay
            h += pay
        nav = cash + held() + inv_u * ip
        navs.append((d, nav))
        prev_val = {k: u * last[pos[k]["code"]] for k, u in units.items() if u > 0}
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
           "mdd_daily": [mdd[0], round(mdd[1] * 100, 3)], "vol_cuts": cuts, "hedge_days": hedge_days,
           "inv_turnover_x_nav0": round(inv_turn, 3), "days": len(navs)}
    return (out, navs) if want_navs else out


def cut_check(g, T):
    _, full = account(g["led"], g["still"], g["since"], g["end"], want_navs=True)
    led = [t for t in g["led"] if t["판 날"] <= T]
    still = [t for t in g["led"] if t["산 날"] <= T < t["판 날"]] + [t for t in g["still"] if t["산 날"] <= T]
    _, cut = account(led, still, g["since"], T, want_navs=True)
    a = [v for d, v in full if d <= T]
    b = [v for d, v in cut]
    return {"T": T, "ok": len(a) == len(b) > 0 and all(abs(x - y) < 1e-12 for x, y in zip(a, b))}


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def main():
    out = {"task": "D1-BEAR-0011", "tag": TAG}
    for which in ("앞", "뒤"):
        gs = z081.ledgers(which, z081.holds_b0)
        out[which] = {}
        for name, hg in (("B0 후보 ×2", False), ("H 절반 인버스", True)):
            seeds = []
            for g in gs:
                a, navs = account(g["led"], g["still"], g["since"], g["end"], hedge=hg, want_navs=True)
                if not hg:                               # 셈 덧붙임 확인: z087과 씨앗마다 같아야 함
                    ref = z087.account(g["led"], g["still"], g["since"], g["end"])
                    assert abs(ref["end_nav"] - a["end_nav"]) < 1e-3, ("z087과 다름", g["seed"], ref["end_nav"], a["end_nav"])
                mr = z081.monthly(navs)
                seeds.append({**a, "regime": {k: z081.ann([x for m, x in mr.items() if z081.regime_of(m) == k]) for k in ("상승", "횡보", "하락")},
                              "down_side": z081.ann([x for m, x in mr.items() if z081.regime_of(m) != "상승"])})
            r = {"cagr": med([s["cagr"] for s in seeds]), "cagr_spread": round(max(s["cagr"] for s in seeds) - min(s["cagr"] for s in seeds), 2),
                 "worst_day": min((s["worst_day"] for s in seeds), key=lambda x: x[1]), "worst_month": min((s["worst_month"] for s in seeds), key=lambda x: x[1]),
                 "mdd": min((s["mdd_daily"] for s in seeds), key=lambda x: x[1]),
                 "regime": {k: med([s["regime"][k] for s in seeds]) for k in ("상승", "횡보", "하락")}, "down_side": med([s["down_side"] for s in seeds]),
                 "hedge_days": med([s["hedge_days"] for s in seeds]), "inv_turnover": med([s["inv_turnover_x_nav0"] for s in seeds])}
            out[which][name] = r
            print(f"[{TAG} · {which}] {name}: 연복리 {r['cagr']}(폭 {r['cagr_spread']}) · 하루 {r['worst_day']} · 달 {r['worst_month']} · 고점 대비 {r['mdd']} · "
                  f"장별 {r['regime']} · 횡보+하락 {r['down_side']} · 인버스 든 날 {r['hedge_days']}", flush=True)
        out[which]["cut_check"] = [cut_check(gs[0], T) for T in (("20190630",) if which == "앞" else ("20231231", "20250630"))]
        print(f"[{TAG} · {which}] 자르기 {out[which]['cut_check']}", flush=True)
    b = {w: out[w]["B0 후보 ×2"] for w in ("앞", "뒤")}
    v = {w: out[w]["H 절반 인버스"] for w in ("앞", "뒤")}
    judge = {"bear_better_both": all(v[w]["regime"]["하락"] > b[w]["regime"]["하락"] for w in v),
             "limits": all(v[w]["worst_day"][1] > -15 and v[w]["worst_month"][1] > -15 for w in v),
             "cagr_ok": all(v[w]["cagr"] >= b[w]["cagr"] - 2 * b[w]["cagr_spread"] for w in v),
             "cuts_ok": all(x["ok"] for w in ("앞", "뒤") for x in out[w]["cut_check"])}
    judge["pass"] = all(judge.values())
    judge["mdd_report_only"] = {w: [b[w]["mdd"][1], v[w]["mdd"][1]] for w in v}
    print(f"[{TAG}] 판정 {judge}", flush=True)
    out["judge"] = judge
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"hedge_{TAG}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
