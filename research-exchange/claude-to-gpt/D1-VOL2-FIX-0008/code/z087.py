"""D1-VOL2-FIX-0008 — 사용자가 고른 '지금 규칙 + 흔들림 상한 × 2(1일봉 계좌 100% 셈)'를 GPT 지적 결함을 고쳐 다시 잼.
고친 것(z080.account 대비): ① σ는 전체 거래일 달력의 **전날까지** 21날 종가로(종목 값 없는 날은 앞 값 = 수익 0) ② 보유 비중도 **전날 종가 평가액**
③ 시점: 허용 비중 E는 전날까지 값으로 아침에 정함. 거래 필요 여부(보유 > E × NAV)와 덜어낼 · 살 정확한 금액은 **그날 종가**의 NAV · 보유액으로 셈해 같은 종가에 체결한다고 봄(이 실행 계약은 검증 안 됨). 매수 크기 = min(NAV × 칸/10, 현금, E × NAV − 보유).
Z_TAG=raw|adj(NRL_CACHE · CAPS_ADJ로 자료 고름) · python3 research/z087.py"""
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
import z081  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-VOL2-FIX-0008/evidence"))
TAG = os.environ.get("Z_TAG", "raw")
VOL = 0.05 / math.sqrt(21) * 2      # 2.1822% = (15% ÷ 3) × 2(1일봉 몫 50%) ÷ √21
LOOK = 20
COST = 0.0025
CAL = lab.trading_days(nrl.lanes)


def account(led, still, start, end, vol=VOL, want_navs=False, market_cap=None, cushion=None):
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
    navs, cuts = [], 0
    prev_val = {}                                   # 전날 종가 평가액(비중용)

    def held():
        return sum(u * last[pos[k]["code"]] for k, u in units.items())

    for d in days:
        # 아침 판단: 전날까지 값만
        allowed = 1.0
        if vol is not None and prev_val:
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
                        allowed = min(1.0, vol / sd)
        if market_cap is not None:                       # 시장 신호 상한(전날까지 값만 · D1-BEAR-0009)
            allowed = min(allowed, market_cap(d))
        if cushion is not None and navs:                 # 손실 쿠션(전날까지 NAV 고점 대비 · D1-BEAR-0010)
            hw = max(v for _, v in navs)
            dd = 1 - navs[-1][1] / hw
            allowed = min(allowed, max(0.0, min(1.0, cushion[0] * (cushion[1] - dd))))
        # 그날 종가
        for c in codes:
            if d in close[c]:
                last[c] = close[c][d]
        for k in sells[d]:
            cash += spent.pop(k) * (1 + pos[k]["손익"] / 100)
            del units[k]
        h = held()
        nav = cash + h
        if (vol is not None or market_cap is not None or cushion is not None) and h > allowed * nav + 1e-12:     # 아침에 정한 비중을 종가에 실행
            f = allowed * nav / h
            cash += h * (1 - f) * (1 - COST)
            for k in units:
                units[k] *= f
                spent[k] *= f
            cuts += 1
        h = held()
        nav = cash + h
        for k in sorted(buys[d], key=order):
            room = max(0.0, allowed * nav - h) if (vol is not None or market_cap is not None or cushion is not None) else float("inf")
            pay = max(0.0, min(pos[k]["자리"] / nrl.SLOTS * nav, cash, room))
            units[k], spent[k] = pay / close[pos[k]["code"]][d], pay
            cash -= pay
            h += pay
        nav = cash + held()
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
           "mdd_daily": [mdd[0], round(mdd[1] * 100, 3)], "vol_cuts": cuts, "days": len(navs)}
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
    out = {"task": "D1-VOL2-FIX-0008", "tag": TAG, "vol_day": VOL}
    for which in ("앞", "뒤"):
        gs = z081.ledgers(which, z081.holds_b0)
        res = {}
        for name, v in (("지금 규칙", None), ("후보 ×2(고침)", VOL)):
            seeds = []
            for g in gs:
                a, navs = account(g["led"], g["still"], g["since"], g["end"], vol=v, want_navs=True)
                mr = z081.monthly(navs)
                reg = {k: z081.ann([x for m, x in mr.items() if z081.regime_of(m) == k]) for k in ("상승", "횡보", "하락")}
                seeds.append({**a, "regime": reg, "down_side": z081.ann([x for m, x in mr.items() if z081.regime_of(m) != "상승"])})
            r = {"cagr": med([s["cagr"] for s in seeds]), "cagr_spread": round(max(s["cagr"] for s in seeds) - min(s["cagr"] for s in seeds), 2),
                 "worst_day": min((s["worst_day"] for s in seeds), key=lambda x: x[1]),
                 "worst_month": min((s["worst_month"] for s in seeds), key=lambda x: x[1]),
                 "mdd": min((s["mdd_daily"] for s in seeds), key=lambda x: x[1]),
                 "regime": {k: med([s["regime"][k] for s in seeds]) for k in ("상승", "횡보", "하락")},
                 "down_side": med([s["down_side"] for s in seeds])}
            res[name] = r
            print(f"[{TAG} · {which}] {name}: 연복리 {r['cagr']}(폭 {r['cagr_spread']}) · 하루 {r['worst_day']} · 달 {r['worst_month']} · 고점 대비 {r['mdd']} · "
                  f"장별 {r['regime']} · 횡보+하락 {r['down_side']}", flush=True)
        res["cut_check"] = [cut_check(gs[0], T) for T in (("20190630",) if which == "앞" else ("20231231", "20250630"))]
        print(f"[{TAG} · {which}] 자르기 {res['cut_check']}", flush=True)
        out[which] = res
    c = {w: out[w]["후보 ×2(고침)"] for w in ("앞", "뒤")}
    out["day_month_ok"] = all(c[w]["worst_day"][1] > -15 and c[w]["worst_month"][1] > -15 for w in c)
    out["mdd_ok"] = all(c[w]["mdd"][1] > -15 for w in c)
    out["cuts_ok"] = all(x["ok"] for w in ("앞", "뒤") for x in out[w]["cut_check"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"fix_{TAG}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"[{TAG}] 하루 · 달 한도 {out['day_month_ok']} · 고점 대비 한도 {out['mdd_ok']} · 자르기 {out['cuts_ok']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
