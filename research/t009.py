"""USINV-0039 — 미국 인버스 덧대기: 신호가 켜진 동안 계좌 20%를 기준 A에서 TIGER 미국S&P500선물인버스(H)(225030)로 옮김.
사전등록: research-exchange/claude-to-gpt/USINV-0039/PREREG.md
- 신호(t 종가까지 225030 원주가 + 분배금 현금만으로 이은 값 tri): 아래 9판(T · O · V 각 3) — 앞 기간(Train)에서만 고름.
- 체결: t 종가에 신호 → t+1 종가에 20% 옮김 · 꺼진 날 t' → t'+1 종가에 되돌림(같은 날 종가 매매 없음).
- 비용: 225030 편도 = 수수료 + k틱 ÷ 원주가(틱 5원 · 자료 기간 내내 2,000원 위) · 기준 A 쪽 옮긴 돈 편도 0.175%.
- 분배금: 예탁원 목록(분배락 = 기준일 바로 앞 거래일 · 세후 84.6%).
python3 research/t009.py            (T_TO=YYYYMMDD — 자르기 시험)"""
import csv
import hashlib
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = ROOT / "research-exchange/claude-to-gpt/USINV-0039"
SHA = json.loads((BOX / "sha256.json").read_text())
TO = os.getenv("T_TO", "")
INV, NAS = "225030", "409810"
W, A_COST, TICK, TAX = 0.20, 0.00175, 5.0, 0.154
MAIN, STRESS = (0.00015, 1), (0.0003, 3)
TRAIN, VALID = ("20170201", "20211230"), ("20220103", "20260916")
VARIANTS = ["T50", "T100", "T200", "O10", "O20", "O40", "V50", "V70", "V90"]
BLOCK, REPS, SEED, MIN_WIN = 6, 10000, 20261010, 3


def check():
    for rel, h in SHA.items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != h:
            sys.exit(f"해시 다름 {rel}")


def side(price, cost):
    fee, k = cost
    return fee + k * TICK / price


def load(code):
    d = json.loads((ROOT / f"etf-ohlc/{code}.json").read_text())
    raw = [x for x in d["raw"] if not TO or x[0] <= TO]
    days = [x[0] for x in raw]
    dist = {}
    for x in d["dividends"]:
        if TO and x["record_date"] > TO:
            continue
        prior = [t for t in days if t < x["record_date"]]
        if prior:
            dist[prior[-1]] = x["per_share_cash"]
    px = {x[0]: x[4] for x in raw}
    return days, px, dist


def tri_of(days, px, dist):
    """원주가 + 분배금(세전) 다시 넣은 값 — 앞으로만 이어서 만듦(수정주가처럼 뒤 분배금으로 앞을 고치지 않음)."""
    out, v = {}, 1.0
    for i, t in enumerate(days):
        if i:
            v *= (px[t] + dist.get(t, 0.0)) / px[days[i - 1]]
        out[t] = v
    return out


def pct_rank(past, x):
    return sum(1 for p in past if p < x) / len(past)


def signal(var, days, tri):
    """{t: 켜짐} — t 종가까지 값만. T: tri > N일 평균(미국 지수 아래로). O: 미국 20일 상승(1/tri) 앞 500일 위 10% → H일 켬.
    V: tri > 50일 평균 그리고 20일 변동성이 앞 250일 값들의 P백분위 위."""
    fam, n = var[0], int(var[1:])
    v = [tri[t] for t in days]
    on, hold_until = {}, -1
    lr = [0.0] + [math.log(v[i] / v[i - 1]) for i in range(1, len(v))]
    vol = [None] * len(v)
    for i in range(20, len(v)):
        vol[i] = statistics.pstdev(lr[i - 19:i + 1])
    up20 = [None] * len(v)
    for i in range(20, len(v)):
        up20[i] = v[i - 20] / v[i] - 1
    for i, t in enumerate(days):
        if fam == "T":
            if i >= n - 1:
                on[t] = v[i] > sum(v[i - n + 1:i + 1]) / n
        elif fam == "O":
            if i >= 520:
                past = up20[i - 500:i]
                if pct_rank(past, up20[i]) >= 0.9:
                    hold_until = i + n - 1
                on[t] = i <= hold_until
        else:
            if i >= 270:
                past = vol[i - 250:i]
                on[t] = v[i] > sum(v[i - 49:i + 1]) / 50 and pct_rank(past, vol[i]) >= n / 100
    return on


def base_nav():
    rows = csv.DictReader((BOX / "base_m1.csv").open(encoding="utf-8"))
    return {r["날"]: float(r["NAV"]) for r in rows if not TO or r["날"] <= TO}


def overlay(base, days, px, dist, on, cost):
    """기준 A 날짜축. 들고 있음(x 종가 뒤) = on[225030 기준 x 앞 날]. 돌려줌: 덧댄 NAV · A만 NAV.
    x 날 순서: 먼저 그날 수익을 굴리고, 그다음 x 종가에 옮김(들어갈 때 계좌 20% · 나올 때 인버스 몫 전부)."""
    idx = {t: i for i, t in enumerate(days)}
    bd = sorted(base)
    a, b, held, nav, alone = base[bd[0]], 0.0, False, [], []
    for k in range(1, len(bd)):
        x, p = bd[k], bd[k - 1]
        a *= base[x] / base[p]
        if held and x in idx and p in idx:
            b *= (px[x] + dist.get(x, 0.0) * (1 - TAX)) / px[p]
        # 225030 줄이 없는 날은 그 몫 값 그대로 · 옮기지 않음
        want = on.get(days[idx[x] - 1], False) if x in idx and idx[x] > 0 else held
        if want and not held:
            move = W * (a + b)
            a -= move * (1 + A_COST)
            b = move * (1 - side(px[x], cost))
            held = True
        elif held and not want:
            a += b * (1 - side(px[x], cost)) * (1 - A_COST)
            b, held = 0.0, False
        nav.append((x, a + b))
        alone.append((x, base[x]))
    return nav, alone


def windows_fix(base, days, px, dist, on, cost):
    """창별 순수익을 따로 깔끔하게 다시 셈(산 날 종가 · 비용 포함 → 판 날 종가 · 비용 포함 · 그 사이 분배금 세후)."""
    idx = {t: i for i, t in enumerate(days)}
    bd = [t for t in sorted(base) if t in idx]
    out, start = [], None
    for k in range(1, len(bd)):
        x = bd[k]
        want = on.get(days[idx[x] - 1], False) if idx[x] > 0 else False
        if want and start is None:
            start = x
        elif not want and start is not None:
            v = 1 - side(px[start], cost)
            for j in range(idx[start] + 1, idx[x] + 1):
                t = days[j]
                v *= (px[t] + dist.get(t, 0.0) * (1 - TAX)) / px[days[j - 1]]
            v *= 1 - side(px[x], cost)
            out.append((start, x, v - 1, base[x] / base[start] - 1))
            start = None
    return out, start


def risk(navs, lo, hi):
    before = [v for d, v in navs if d < lo]
    nv = [(d, v) for d, v in navs if lo <= d <= hi]
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
    return {"cagr": round(((nv[-1][1] / b0) ** (245 / len(rets)) - 1) * 100, 3), "worst_day": [wd[0], round(wd[1] * 100, 3)],
            "worst_month": [wm[0], round((wm[1] - 1) * 100, 3)], "mdd": round(mdd * 100, 3)}, rets


def boot_diff(r1, r0, lo, hi):
    """날마다 (덧댄 − A) 수익 · 달력 달 6달 블록 부트스트랩 평균 구간(%/일)."""
    m0 = dict(r0)
    by = defaultdict(list)
    for d, r in r1:
        by[d[:6]].append(r - m0[d])
    months = sorted(by)
    allx = [x for m in months for x in by[m]]
    rng = random.Random(SEED)
    nb = math.ceil(len(months) / BLOCK)
    ms = []
    for _ in range(REPS):
        xs = []
        for _ in range(nb):
            st = rng.randrange(0, len(months) - BLOCK + 1)
            for m in months[st:st + BLOCK]:
                xs += by[m]
        ms.append(sum(xs) / len(xs))
    q = lambda p: sorted(ms)[int(p * (len(ms) - 1))]
    return round(sum(allx) / len(allx) * 100, 5), [round(q(.025) * 100, 5), round(q(.975) * 100, 5)]


def years(r1, r0):
    m0 = dict(r0)
    y = defaultdict(lambda: [1.0, 1.0])
    for d, r in r1:
        y[d[:4]][0] *= 1 + r
        y[d[:4]][1] *= 1 + m0[d]
    return {k: round((v[0] - v[1]) * 100, 3) for k, v in sorted(y.items())}


def evaluate(var, base, inv, cost, lo, hi, boot=False):
    days, px, dist = inv
    tri = tri_of(days, px, dist)
    on = signal(var, days, tri)
    nav, alone = overlay(base, days, px, dist, on, cost)
    wins, open_ = windows_fix(base, days, px, dist, on, cost)
    r1, rets1 = risk(nav, lo, hi)
    r0, rets0 = risk(alone, lo, hi)
    w = [z for z in wins if lo <= z[0] and z[1] <= hi]
    held = sum(1 for t in days if lo <= t <= hi and on.get(t))
    out = {"windows": len(w), "on_days_share": round(held / max(1, sum(1 for t in days if lo <= t <= hi)), 4),
           "overlay": r1, "a_alone": r0, "cagr_gain": round(r1["cagr"] - r0["cagr"], 3),
           "win_inv_mean_pct": round(sum(z[2] for z in w) / len(w) * 100, 4) if w else None,
           "win_a_mean_pct": round(sum(z[3] for z in w) / len(w) * 100, 4) if w else None,
           "win_diff_mean_pct": round(sum(z[2] - z[3] for z in w) / len(w) * 100, 4) if w else None,
           "year_gain_pct": years(rets1, rets0)}
    if boot:
        out["daily_diff_mean_pct"], out["daily_diff_ci95_pct"] = boot_diff(rets1, rets0, lo, hi)
    return out, nav, wins, open_


def liquidity(inv, base, wins, lo, hi):
    """창 시작 날 옮긴 돈 ÷ 그날 앞 20거래일 거래대금 가운데값(참고 · 판정 아님)."""
    code = INV if inv is None else inv
    d = json.loads((ROOT / f"etf-ohlc/{code}.json").read_text())
    tv = {x[0]: x[6] for x in d["raw"]}
    ds = sorted(tv)
    out = []
    for s, _, _, _ in wins:
        if not (lo <= s <= hi) or s not in tv:
            continue
        i = ds.index(s)
        med = statistics.median(tv[t] for t in ds[max(0, i - 20):i]) if i else None
        if med:
            out.append(W * base[s] / med)
    return {"n": len(out), "median_share": round(statistics.median(out), 3) if out else None,
            "max_share": round(max(out), 3) if out else None}


def main():
    check()
    base = base_nav()
    inv = load(INV)
    res = {"task": "USINV-0039", "round": 1, "T_TO": TO or None, "train": {}, "valid": None}
    for v in VARIANTS:
        res["train"][v] = evaluate(v, base, inv, MAIN, *TRAIN)[0]
    ok = [v for v in VARIANTS if res["train"][v]["windows"] >= MIN_WIN]
    pick = max(ok, key=lambda v: (res["train"][v]["cagr_gain"], -VARIANTS.index(v))) if ok else None
    res["pick"] = pick
    res["pick_train_gain"] = res["train"][pick]["cagr_gain"] if pick else None
    if pick:
        _, nav, wins, open_ = evaluate(pick, base, inv, MAIN, *TRAIN)
        res["pick_trades"] = [[s, e, round(x * 100, 6), round(y * 100, 6)] for s, e, x, y in wins]
        res["pick_open"] = open_
        res["pick_nav"] = [[d, round(x, 6)] for d, x in nav]
    if pick and res["pick_train_gain"] > 0 and not TO:
        lo, hi = VALID
        m, _, wins, _ = evaluate(pick, base, inv, MAIN, lo, hi, boot=True)
        s, _, _, _ = evaluate(pick, base, inv, STRESS, lo, hi)
        mt = evaluate(pick, base, inv, MAIN, *TRAIN)[0]
        res["valid"] = {"main": m, "stress": s, "liquidity": liquidity(None, base, wins, lo, hi)}
        c1 = m["cagr_gain"] > 0 and s["cagr_gain"] > 0
        c2 = m["windows"] >= MIN_WIN and m["win_diff_mean_pct"] > 0
        c3 = m["daily_diff_ci95_pct"][0] > 0
        c4 = all(r["overlay"]["worst_day"][1] >= -15 and r["overlay"]["worst_month"][1] >= -15 for r in (m, mt))
        res["conditions"] = {"1_cagr_main_and_stress": c1, "2_window_diff": c2, "3_boot_ci": c3, "4_loss_limit": c4,
                             "5_cut": "따로(T_TO=20211230)"}
        # 나스닥 형제(409810 · 2021-12 상장) — 같은 규칙 · 참고만
        nas = load(NAS)
        res["nasdaq_reference"] = evaluate(pick, base, nas, MAIN, lo, hi)[0]
        res["verdict_before_cut"] = "EXPLORATORY_SIGNAL_CANDIDATE" if all((c1, c2, c3, c4)) else "REJECTED"
    elif not TO:
        res["verdict_before_cut"] = "REJECTED(Train 고른 판 증분 ≤ 0 · 뒤 기간 열지 않음)"
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
