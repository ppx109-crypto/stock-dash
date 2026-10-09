"""D1-VOL2-VALIDATE — 후보(지금 규칙 + 흔들림 상한 × 2 · 덜어내기 없음)의 15:15 판단 확인(CLAUDE.md '종가에 사는 규칙은 15:15 값으로 판단해도 같은 결정인지').
흔들림 상한의 판단(오늘까지 20일 σ · 지금 주식 비중)을 '오늘 종가' 대신 15분봉 15:00 칸 종가(= 15:15 값)로 하고 실행은 종가로.
기간: 15분봉이 있는 2025-09-18 ~ 2026-08-31(뒤 반 안). 매매 줄(엔진 신호)은 같음 — 신호 쪽 15:15 확인은 새 84회차(95 ~ 99% 같음).
python3 research/z082.py   (Z_OUT)"""
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
import z080  # noqa: E402
import z081  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-VOL2-VALIDATE-0005/evidence"))
M15 = Path("/home/user/stock-dash/m15-kis")
START, END = "20250918", "20260831"
VOL = z080.VOL_DAY * 2


def load_pre():
    pre = {}
    for d in M15.iterdir():
        if not d.is_dir():
            continue
        got = {}
        for f in sorted(d.glob("*.csv")):
            for line in open(f, encoding="utf-8"):
                p = line.strip().split(",")
                if len(p) >= 5 and p[0][8:12] == "1500":
                    got[p[0][:8]] = float(p[4])
        if got:
            pre[d.name] = got
    return pre


def account(led, still, start, end, pre=None):
    """z080.account(vol=VOL, cap 없음)과 같은 셈. pre가 있으면 흔들림 상한 '판단'만 그날 15:00 칸 값으로(없는 종목은 종가) · 실행은 종가."""
    lanes = nrl.lanes
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
    navs, cuts, used_pre, decisions = [], 0, 0, []

    def px_dec(c, d):
        nonlocal used_pre
        if pre is not None and d >= START and c in pre and d in pre[c]:
            used_pre += 1
            return pre[c][d]
        return last[c]

    for d in days:
        for c in codes:
            if d in close[c]:
                last[c] = close[c][d]
        for k in sells[d]:
            cash += spent.pop(k) * (1 + pos[k]["손익"] / 100)
            del units[k]
        allowed = 1.0
        if units:
            w = defaultdict(float)
            for k, u in units.items():
                w[pos[k]["code"]] += u * px_dec(pos[k]["code"], d)
            tot = sum(w.values())
            rets, ok = [], tot > 0
            for c, v in w.items():
                ds, cs = series[c]
                i = bisect.bisect_right(ds, d) - 1
                if i - z080.LOOK < 0:
                    ok = False
                    break
                seq = [cs[j] / cs[j - 1] - 1 for j in range(i - z080.LOOK + 1, i)]
                seq.append(px_dec(c, d) / cs[i - 1] - 1 if ds[i] == d else cs[i] / cs[i - 1] - 1)
                rets.append((v / tot, seq))
            if ok:
                port = [sum(wt * r[t] for wt, r in rets) for t in range(z080.LOOK)]
                m = sum(port) / z080.LOOK
                s = math.sqrt(sum((x - m) ** 2 for x in port) / (z080.LOOK - 1))
                if s > 0:
                    allowed = min(1.0, VOL / s)
            nav_dec = cash + tot
            if tot > allowed * nav_dec + 1e-12:
                f = allowed * nav_dec / tot             # 판단 값으로 정한 덜어낼 비율을 종가에 실행
                sold = sum(units[k] * last[pos[k]["code"]] for k in units) * (1 - f)
                cash += sold * (1 - z080.COST)
                for k in units:
                    units[k] *= f
                    spent[k] *= f
                cuts += 1
        held = sum(u * last[pos[k]["code"]] for k, u in units.items())
        nav = cash + held
        for k in sorted(buys[d], key=order):
            room = max(0.0, allowed * nav - held)
            pay = max(0.0, min(pos[k]["자리"] / nrl.SLOTS * nav, cash, room))
            units[k], spent[k] = pay / close[pos[k]["code"]][d], pay
            cash -= pay
            held += pay
        nav = cash + sum(u * last[pos[k]["code"]] for k, u in units.items())
        navs.append((d, nav))
        if d >= START:
            decisions.append((d, round(allowed, 4)))
    return navs, cuts, used_pre, decisions


def window(navs):
    sel = [(d, v) for d, v in navs if START <= d <= END]
    prev = [v for d, v in navs if d < START][-1]
    rets = [(sel[0][0], sel[0][1] / prev - 1)] + [(sel[i][0], sel[i][1] / sel[i - 1][1] - 1) for i in range(1, len(sel))]
    month = defaultdict(lambda: 1.0)
    for d, r in rets:
        month[d[:6]] *= 1 + r
    tot = sel[-1][1] / prev - 1
    return {"period_return": round(tot * 100, 2), "worst_day": min(rets, key=lambda x: x[1]), "worst_month": min(month.items(), key=lambda x: x[1])}


def main():
    pre = load_pre()
    gs = z081.ledgers("뒤", z081.holds_b0)
    res = []
    chk = z080.account(gs[0]["led"], gs[0]["still"], gs[0]["since"], gs[0]["end"], vol=VOL)
    a0 = account(gs[0]["led"], gs[0]["still"], gs[0]["since"], gs[0]["end"])[0]
    assert abs(a0[-1][1] - chk["end_nav"]) < 1e-3, ("z080 셈과 다름", a0[-1][1], chk["end_nav"])    # 15:00 값 없이는 앞 셈과 같아야 함
    for g in gs:
        a, ca, _, da = account(g["led"], g["still"], g["since"], g["end"])
        b, cb, used, db = account(g["led"], g["still"], g["since"], g["end"], pre=pre)
        wa, wb = window(a), window(b)
        diff_days = sum(1 for (d1, x), (d2, y) in zip(da, db) if abs(x - y) > 0.01)
        res.append({"seed": g["seed"], "close": {"period_return": wa["period_return"], "worst_day": [wa["worst_day"][0], round(wa["worst_day"][1] * 100, 3)],
                                                 "worst_month": [wa["worst_month"][0], round((wa["worst_month"][1] - 1) * 100, 3)], "cuts": ca},
                    "p1515": {"period_return": wb["period_return"], "worst_day": [wb["worst_day"][0], round(wb["worst_day"][1] * 100, 3)],
                              "worst_month": [wb["worst_month"][0], round((wb["worst_month"][1] - 1) * 100, 3)], "cuts": cb},
                    "decision_days": len(da), "decision_days_diff_over_1pp": diff_days, "pre_price_uses": used})
        r = res[-1]
        print(f"씨앗 {g['seed']}: 종가 판단 기간 수익 {r['close']['period_return']}% · 하루 {r['close']['worst_day']} · 달 {r['close']['worst_month']} | "
              f"15:15 판단 {r['p1515']['period_return']}% · 하루 {r['p1515']['worst_day']} · 달 {r['p1515']['worst_month']} | "
              f"허용 비중이 1%p 넘게 다른 날 {diff_days}/{len(da)} · 15:00 값 쓴 횟수 {used}", flush=True)
    spread = max(x["close"]["period_return"] for x in res) - min(x["close"]["period_return"] for x in res)
    gap = max(abs(x["close"]["period_return"] - x["p1515"]["period_return"]) for x in res)
    limits = all(x["p1515"]["worst_day"][1] > -15 and x["p1515"]["worst_month"][1] > -15 for x in res)
    verdict = "PASS" if limits and gap <= spread else "FAIL"
    out = {"task": "D1-VOL2-VALIDATE 15:15", "period": [START, END], "seeds": res, "seed_spread_close": round(spread, 2),
           "max_gap_close_vs_1515": round(gap, 2), "limits_ok_1515": limits, "verdict": verdict}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "check1515.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"판정: 15:15 판단 한도 {limits} · 종가 대비 가장 큰 차 {gap:.2f}%p ≤ 씨앗 폭 {spread:.2f}%p → {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
