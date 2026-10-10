"""BULL-OOS-0040 — ENG-BULL-0019(오름장에 놀던 돈을 KODEX 200에)를 개발에 안 쓴 2003 ~ 2016에서 다시 잼(지수판 1판).
사전등록: research-exchange/claude-to-gpt/BULL-OOS-0040/PREREG.md
- 신호(t 종가까지 069500 원주가만): 50일 단순평균 > 200일 단순평균이면 '오름장'(원래 규칙의 시장 폭 = 100위 종목 가운데 50일선 > 200일선 몫을 지수 하나로 줄인 것).
- 계좌: 현금 1에서 시작 · 신호가 켜지면 다음 날(t+1) 종가에 계좌의 50%로 069500을 삼 · 꺼지면 다음 날 종가에 다 팖 · 현금 이자 0.
- 수익 두 경계: adj(한투 수정주가 날마다 비율 = 분배금 세전 재투자) · zero(원주가만 · 분배금 0). 둘 다 통과해야 함.
- 비용: 편도 수수료 + k틱 ÷ 원주가(틱 5원 · 기간 내내 6,800원 위).
python3 research/t010.py                       본 셈
T_TO=20091230 python3 research/t010.py         자르기 셈(앞 반까지만)
python3 research/t010.py --compare 본.json 자르기.json"""
import hashlib
import json
import math
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = ROOT / "research-exchange/claude-to-gpt/BULL-OOS-0040"
TO = os.getenv("T_TO", "")
CODE, W, TICK = "069500", 0.50, 5.0
FAST, SLOW = 50, 200
MAIN, STRESS = (0.00015, 1), (0.0003, 3)
P = {"H1": ("20030801", "20091230"), "H2": ("20100104", "20161230"), "ALL": ("20030801", "20161230")}
END = "20161230"
BLOCK, REPS, SEED = 6, 10000, 20261010
CUT_KEYS = ["H1"]


def check():
    for rel, h in json.loads((BOX / "sha256.json").read_text()).items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != h:
            sys.exit(f"해시 다름 {rel}")


def side(price, cost):
    return cost[0] + cost[1] * TICK / price


def load(to=""):
    """2016-12-30 뒤는 물리적으로 버림(이 시험은 2017 ~ 를 보지 않음). to가 있으면 그날까지."""
    d = json.loads((ROOT / f"etf-ohlc/{CODE}.json").read_text())
    lim = min(END, to) if to else END
    raw = [x for x in d["raw"] if x[0] <= lim]
    adj = {x[0]: x[4] for x in d["adjusted"] if x[0] <= lim}
    days = [x[0] for x in raw]
    return days, {x[0]: x[4] for x in raw}, adj


def signal(days, px):
    """{t: 오름장} — t 종가까지 원주가만."""
    v = [px[t] for t in days]
    out = {}
    for i, t in enumerate(days):
        if i >= SLOW - 1:
            out[t] = sum(v[i - FAST + 1:i + 1]) / FAST > sum(v[i - SLOW + 1:i + 1]) / SLOW
    return out


def account(days, px, adj, on, cost, mode, w=W, gate=True):
    """돌려줌: [(날, 계좌)] · 창 [(산 날, 판 날)]. x 날: 먼저 수익을 굴리고 x 종가에 사고팖. gate=False면 첫날부터 늘 w 보유(대조)."""
    cash, b, held, nav, wins, st = 1.0, 0.0, False, [], [], None
    for i, x in enumerate(days):
        if i and held:
            b *= (adj[x] / adj[days[i - 1]]) if mode == "adj" else (px[x] / px[days[i - 1]])
        want = (on.get(days[i - 1], False) if i else False) if gate else True
        if want and not held:
            amt = w * (cash + b)
            cash -= amt
            b = amt * (1 - side(px[x], cost))
            held, st = True, x
        elif held and not want:
            cash += b * (1 - side(px[x], cost))
            b, held = 0.0, False
            wins.append((st, x))
        nav.append((x, cash + b))
    return nav, wins


def risk(nav, lo, hi):
    before = [v for d, v in nav if d < lo]
    nv = [(d, v) for d, v in nav if lo <= d <= hi]
    b0 = before[-1] if before else nv[0][1]
    rets, last = [], b0
    for d, v in nv:
        rets.append((d, v / last - 1))
        last = v
    mon = defaultdict(lambda: 1.0)
    for d, r in rets:
        mon[d[:6]] *= 1 + r
    peak, mdd = b0, 0.0
    for _, v in nv:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    wd = min(rets, key=lambda z: z[1])
    wm = min(mon.items(), key=lambda z: z[1])
    cagr = (nv[-1][1] / b0) ** (245 / len(rets)) - 1
    raw = {"cagr": cagr, "worst_day": wd[1], "worst_month": wm[1] - 1}
    rep = {"cagr": round(cagr * 100, 3), "worst_day": [wd[0], round(wd[1] * 100, 3)],
           "worst_month": [wm[0], round((wm[1] - 1) * 100, 3)], "mdd": round(mdd * 100, 3)}
    return rep, raw, rets


def boot(rets):
    """날마다 계좌 수익(= 현금 대비 초과 · 현금 이자 0) 평균 · 달력 달 6달 블록 부트스트랩 95% 구간."""
    by = defaultdict(list)
    for d, r in rets:
        by[d[:6]].append(r)
    months = sorted(by)
    allx = [x for m in months for x in by[m]]
    rng = random.Random(SEED)
    nb = math.ceil(len(months) / BLOCK)
    ms = []
    for _ in range(REPS):
        xs = []
        for _ in range(nb):
            s = rng.randrange(0, len(months) - BLOCK + 1)
            for m in months[s:s + BLOCK]:
                xs += by[m]
        ms.append(sum(xs) / len(xs))
    ms.sort()
    return sum(allx) / len(allx), ms[int(.025 * (REPS - 1))], ms[int(.975 * (REPS - 1))]


def years(rets):
    y = defaultdict(lambda: 1.0)
    for d, r in rets:
        y[d[:4]] *= 1 + r
    return {k: round((v - 1) * 100, 2) for k, v in sorted(y.items())}


def period(days, px, adj, on, lo, hi, with_boot=False):
    out, raws = {}, {}
    for mode in ("adj", "zero"):
        for cn, cost in (("main", MAIN), ("stress", STRESS)):
            nav, wins = account(days, px, adj, on, cost, mode)
            rep, raw, rets = risk(nav, lo, hi)
            key = f"{mode}_{cn}"
            out[key] = rep
            raws[key] = raw
            if key == "adj_main":
                out["windows"] = len([w for w in wins if lo <= w[0] and w[1] <= hi])
                out["on_share"] = round(sum(1 for t in days if lo <= t <= hi and on.get(t)) / sum(1 for t in days if lo <= t <= hi), 4)
                out["years_pct"] = years(rets)
                if with_boot:
                    m, l, u = boot(rets)
                    out["boot_daily_pct"] = [round(m * 100, 5), round(l * 100, 5), round(u * 100, 5)]
                    raws["boot_lo"] = l
        # 대조(판정 아님): 늘 50% 보유
        nav, _ = account(days, px, adj, on, MAIN, mode, gate=False)
        out[f"{mode}_always50"] = risk(nav, lo, hi)[0]
    return out, raws


def run(to=""):
    days, px, adj = load(to)
    on = signal(days, px)
    res = {"task": "BULL-OOS-0040", "round": 1, "T_TO": to or None, "first_signal": min(on) if on else None,
           "last_day": days[-1]}
    res["H1"], r1 = period(days, px, adj, on, *P["H1"])
    if to:
        return res
    res["H2"], r2 = period(days, px, adj, on, *P["H2"])
    res["ALL"], ra = period(days, px, adj, on, *P["ALL"], with_boot=True)
    c1 = all(r[k]["cagr"] > 0 for r in (r1, r2) for k in ("adj_main", "adj_stress", "zero_main", "zero_stress"))
    c2 = ra["boot_lo"] > 0
    c3 = all(r[k]["worst_day"] >= -0.15 and r[k]["worst_month"] >= -0.15
             for r in (r1, r2) for k in ("adj_main", "adj_stress", "zero_main", "zero_stress"))
    res["conditions"] = {"1_cagr_gt_cash_both_halves_8paths": c1, "2_boot_lo_gt0": c2, "3_loss_limit_8paths": c3,
                         "4_cut": "--compare로 따로"}
    res["verdict_before_cut"] = "EXPLORATORY_CANDIDATE" if all((c1, c2, c3)) else "REJECTED"
    res["signals"] = sorted([t, v] for t, v in on.items())
    return res


def compare(a, b):
    x, y = json.loads(Path(a).read_text()), json.loads(Path(b).read_text())
    bad = [k for k in CUT_KEYS if x.get(k) != y.get(k)]
    xs = [s for s in x["signals"] if s[0] <= "20091230"]
    ys = dict(signal(*load("20091230")[:2]).items())
    sig_same = all(ys.get(t) == v for t, v in xs)
    print(json.dumps({"cut_keys": CUT_KEYS, "different": bad, "signals_same_to_cut": sig_same, "same": not bad and sig_same}, ensure_ascii=False))
    return 0 if not bad and sig_same else 1


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--compare":
        return compare(sys.argv[2], sys.argv[3])
    check()
    print(json.dumps(run(TO), ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
