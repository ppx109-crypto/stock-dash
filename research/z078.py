"""D1-CASH-BASELINE-0003 — 1일봉 '새 82'(조용함 문턱 그 달 앞 자료만 = B0)을 운영과 같은 '현금 한도 안 매수'로 다시 잼(새 규칙 시험 아님 · 고르기 없음).
운영 paper_trade.py:348: 매수 금액 = min(계좌 총액 × 칸/10, 남은 현금). 이 셈으로 씨앗 8판 각각의 날마다 NAV를 만들어
연복리 수익 · 하루 TWR 최악 · 달력월 TWR 최악 · 일별 MTM 고점 대비를 두 반에서 냄. 엔진 '연수익'(칸 몫 단순 합)도 나란히 적음.
python3 research/z078.py   (Z_OUT 환경 변수)"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
sys.path.insert(0, "/home/user/stock-dash/research")
import z077  # noqa: E402  (B0 holds · use · 기간 셈 그대로)

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-CASH-BASELINE-0003/evidence"))
SEEDS = 8
NUDGE = 0.05        # lab.wobble 기본값과 같음


def ledgers(which):
    """lab.wobble과 같은 씨앗 8판(0번은 흔들지 않음)을 따로따로 돌려 매매목록을 모두 돌려줌."""
    pool, since = (nrl.early, rule.SINCE) if which == "앞" else (nrl.inside, rule.MID)
    kw = dict(slots=nrl.SLOTS, since=since, apart=nrl.kin, realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE)
    out = []
    with z077.use(z077.make_holds(5, rule.SLOPE)):
        for seed in range(SEEDS):
            rank = rule.order if seed == 0 else lab.jitter(rule.order, NUDGE, seed)
            g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, rank=rank, **kw)
            out.append({"seed": seed, "연수익": g["연수익"], "골": g["최대낙폭"], "매매": g["매매"],
                        "led": g["매매목록"], "still": g["남은자리"], "end": g["끝날"], "since": since})
    return out


def cash_account(led, still, start, end, lanes=None):
    """운영과 같은 현금 한도 매수의 날마다 NAV. 같은 날: 매도 먼저 → 매수는 후보 순서(rule.order, 운영과 같음)대로
    매수 금액 = min(칸/10 × 그날 매수 전 NAV, 남은 현금). 빚 없음(현금 ≥ 0). 정수 주식 · 98% 여유는 두지 않음(연구 단순화)."""
    lanes = lanes or nrl.lanes
    pos = [dict(t, open=False) for t in led] + [dict(t, open=True, 행=None) for t in still]
    codes = {t["code"] for t in pos}
    close = {c: dict(zip(lanes[c]["날"], lanes[c]["closes"])) for c in codes}
    days = [d for d in lab.trading_days(lanes) if start <= d <= end]
    buys, sells = defaultdict(list), defaultdict(list)
    for k, t in enumerate(pos):
        buys[t["산 날"]].append(k)
        if not t["open"]:
            sells[t["판 날"]].append(k)
    # 같은 날 산 줄들(반익 줄 포함)은 같은 종목이면 한 묶음 — 순서는 후보 순서(가파른 기울기 먼저), 같으면 종목 코드
    order = lambda k: (rule.order(pos[k]["행"]) if pos[k].get("행") else 0, pos[k]["code"])
    cash, units, spent, last = 1.0, {}, {}, {}
    navs, capped, short_max, frac_min = [], 0, 0.0, 1.0
    for d in days:
        for c in codes:
            if d in close[c]:
                last[c] = close[c][d]
        for k in sells[d]:
            cash += spent.pop(k) * (1 + pos[k]["손익"] / 100)
            del units[k]
        nav = cash + sum(u * last[pos[k]["code"]] for k, u in units.items())
        for k in sorted(buys[d], key=order):
            want = pos[k]["자리"] / nrl.SLOTS * nav
            pay = min(want, max(cash, 0.0))
            if pay < want - 1e-12:
                capped += 1
                short_max = max(short_max, (want - pay) / nav)
                frac_min = min(frac_min, pay / want if want else 1.0)
            units[k], spent[k] = (pay / close[pos[k]["code"]][d], pay)
            cash -= pay
        held = sum(u * last[pos[k]["code"]] for k, u in units.items())
        navs.append((d, cash + held))
    assert min(0.0, cash) > -1e-12
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
    return {"cagr": round((navs[-1][1] ** (1 / years) - 1) * 100, 2), "end_nav": round(navs[-1][1], 4),
            "worst_day": [wd[0], round(wd[1] * 100, 3)], "worst_month": [wm[0], round((wm[1] - 1) * 100, 3)],
            "mdd_daily": [mdd[0], round(mdd[1] * 100, 3)], "capped_buys": capped, "max_shortfall_pct": round(short_max * 100, 2),
            "min_funded_share": round(frac_min, 4), "days": len(navs), "years": round(years, 2)}


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def side(which):
    got = []
    for g in ledgers(which):
        acc = cash_account(g["led"], g["still"], g["since"], g["end"])
        got.append({"seed": g["seed"], "engine_연수익": g["연수익"], "engine_골": g["골"], "매매": g["매매"], **acc})
        print(f"[{which}] 씨앗 {g['seed']} 엔진 연 {g['연수익']} 골 {g['골']} | 현금 한도 NAV 연복리 {acc['cagr']}% · 하루 최악 {acc['worst_day']} · "
              f"달 최악 {acc['worst_month']} · 고점 대비 {acc['mdd_daily']} · 현금 모자라 줄인 매수 {acc['capped_buys']}건", flush=True)
    summ = {k: {"median": med([x[k] for x in got]), "spread": round(max(x[k] for x in got) - min(x[k] for x in got), 2)}
            for k in ("engine_연수익", "cagr")}
    summ["worst_day_min"] = min((x["worst_day"] for x in got), key=lambda v: v[1])
    summ["worst_month_min"] = min((x["worst_month"] for x in got), key=lambda v: v[1])
    summ["mdd_min"] = min((x["mdd_daily"] for x in got), key=lambda v: v[1])
    summ["capped_buys_median"] = med([x["capped_buys"] for x in got])
    return {"seeds": got, "summary": summ}


def main():
    out = {"task": "D1-CASH-BASELINE-0003", "rule": "새 82 + 조용함 문턱 그 달 앞 자료만(B0)", "sizing": "min(칸/10 × NAV, 현금) — paper_trade.py:348과 같음",
           "앞": side("앞"), "뒤": side("뒤")}
    for h in ("앞", "뒤"):
        s = out[h]["summary"]
        print(f"[{h}] 요약 엔진 연 {s['engine_연수익']} · NAV 연복리 {s['cagr']} · 하루 최악 {s['worst_day_min']} · 달 최악 {s['worst_month_min']} · "
              f"고점 대비 {s['mdd_min']} · 줄인 매수(가운데) {s['capped_buys_median']}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "baseline.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
