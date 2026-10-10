"""USINV-0039 — 미국 인버스 덧대기: 신호가 켜진 동안 계좌 20%를 기준 A에서 TIGER 미국S&P500선물인버스(H)(225030)로 옮김.
사전등록: research-exchange/claude-to-gpt/USINV-0039/PREREG.md
- 신호(t 종가까지 225030 원주가 + 분배금 현금만으로 이은 값 tri): 아래 9판(T · O · V 각 3) — 앞 기간(Train)에서만 고름.
- 체결: t 종가에 신호 → t+1 종가에 20% 옮김 · 꺼진 날 t' → t'+1 종가에 되돌림(같은 날 종가 매매 없음).
- 비용: 225030 편도 = 수수료 + k틱 ÷ 원주가(틱 5원 · 자료 기간 내내 2,000원 위) · 기준 A 쪽 옮긴 돈 편도 0.175%.
- 분배금: 예탁원 목록(분배락 = 기준일 바로 앞 거래일 · 세후 84.6%).
- round 2(GPT #184 6094761540): Train 고르기는 2021-12-30까지로 자른 자료로만 셈 · Validation은 2021-12-30 종가에 A만 100%로 새로 시작 ·
  고르기 · 문을 여는 잣대는 반올림 전 값 · 손실 조건은 Train · Validation × 기본 · 스트레스 네 경로.
python3 research/t009.py                       본 셈
T_TO=20211230 python3 research/t009.py         자르기 셈(Train 단계만)
python3 research/t009.py --compare 본.json 자르기.json   CUT_KEYS 칸이 한 칸도 다르지 않은지"""
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
CUT_KEYS = ["train", "pick", "pick_train_gain_raw", "pick_trades", "pick_open", "pick_nav", "pick_train_stress"]


def check():
    for rel, h in SHA.items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != h:
            sys.exit(f"해시 다름 {rel}")


def side(price, cost):
    fee, k = cost
    return fee + k * TICK / price


def load(code, to=""):
    d = json.loads((ROOT / f"etf-ohlc/{code}.json").read_text())
    raw = [x for x in d["raw"] if not to or x[0] <= to]
    days = [x[0] for x in raw]
    dist = {}
    for x in d["dividends"]:
        prior = [t for t in days if t < x["record_date"]]
        if prior and (not to or x["record_date"] <= to):
            dist[prior[-1]] = x["per_share_cash"]
    return days, {x[0]: x[4] for x in raw}, dist


def cut_inv(inv, to):
    """그날 뒤 줄 · 분배금을 물리적으로 버림(자료 자체를 자름)."""
    days, px, dist = inv
    keep = [t for t in days if t <= to]
    return keep, {t: px[t] for t in keep}, {t: v for t, v in dist.items() if t <= to}


def cut_base(base, to):
    return {d: v for d, v in base.items() if d <= to}


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
    return {r["날"]: float(r["NAV"]) for r in rows}


def overlay(base, days, px, dist, on, cost, start):
    """기준 A 날짜축(start 날부터). start 종가 = A만 100% · 인버스 0(시작 상태). 들고 있음(x 종가 뒤) = on[225030 기준 x 앞 날].
    x 날 순서: 먼저 그날 수익을 굴리고, 그다음 x 종가에 옮김(들어갈 때 계좌 20% · 나올 때 인버스 몫 전부). 돌려줌: 덧댄 NAV · A만 NAV(start 날 포함)."""
    idx = {t: i for i, t in enumerate(days)}
    bd = [d for d in sorted(base) if d >= start]
    a, b, held = base[bd[0]], 0.0, False
    nav, alone = [(bd[0], a)], [(bd[0], a)]
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


def windows_fix(base, days, px, dist, on, cost, start):
    """창별 순수익(산 날 종가 · 비용 포함 → 판 날 종가 · 비용 포함 · 그 사이 분배금 세후) · 같은 기간 A 수익. 열린 창은 따로."""
    idx = {t: i for i, t in enumerate(days)}
    bd = [t for t in sorted(base) if t in idx and t >= start]
    out, st = [], None
    for k in range(1, len(bd)):
        x = bd[k]
        want = on.get(days[idx[x] - 1], False) if idx[x] > 0 else False
        if want and st is None:
            st = x
        elif not want and st is not None:
            v = 1 - side(px[st], cost)
            for j in range(idx[st] + 1, idx[x] + 1):
                t = days[j]
                v *= (px[t] + dist.get(t, 0.0) * (1 - TAX)) / px[days[j - 1]]
            v *= 1 - side(px[x], cost)
            out.append((st, x, v - 1, base[x] / base[st] - 1))
            st = None
    return out, st


def risk(navs, lo, hi):
    """반올림 전 값(raw)과 보고용 반올림 값을 함께 돌려줌."""
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
    cagr = (nv[-1][1] / b0) ** (245 / len(rets)) - 1
    raw = {"cagr": cagr, "worst_day": wd[1], "worst_month": wm[1] - 1, "mdd": mdd}
    rep = {"cagr": round(cagr * 100, 3), "worst_day": [wd[0], round(wd[1] * 100, 3)],
           "worst_month": [wm[0], round((wm[1] - 1) * 100, 3)], "mdd": round(mdd * 100, 3)}
    return rep, raw, rets


def boot_diff(r1, r0):
    """날마다 (덧댄 − A) 수익 · 달력 달 6달 블록 부트스트랩 평균 구간. 반올림 전 값."""
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
    ms.sort()
    return sum(allx) / len(allx), (ms[int(.025 * (REPS - 1))], ms[int(.975 * (REPS - 1))])


def years(r1, r0):
    m0 = dict(r0)
    y = defaultdict(lambda: [1.0, 1.0])
    for d, r in r1:
        y[d[:4]][0] *= 1 + r
        y[d[:4]][1] *= 1 + m0[d]
    return {k: round((v[0] - v[1]) * 100, 3) for k, v in sorted(y.items())}


def evaluate(var, base, inv, cost, lo, hi, start, boot=False):
    """base · inv는 부르는 쪽이 이미 자른 자료. 돌려줌: 보고 dict · 판정용 raw dict · NAV · 창 · 열린 창."""
    days, px, dist = inv
    on = signal(var, days, tri_of(days, px, dist))
    nav, alone = overlay(base, days, px, dist, on, cost, start)
    wins, open_ = windows_fix(base, days, px, dist, on, cost, start)
    r1, x1, rets1 = risk(nav, lo, hi)
    r0, x0, rets0 = risk(alone, lo, hi)
    w = [z for z in wins if lo <= z[0] and z[1] <= hi]
    held = sum(1 for t in days if lo <= t <= hi and on.get(t))
    diff = sum(z[2] - z[3] for z in w) / len(w) if w else None
    raw = {"cagr_gain": x1["cagr"] - x0["cagr"], "windows": len(w), "win_diff": diff,
           "worst_day": x1["worst_day"], "worst_month": x1["worst_month"]}
    out = {"windows": len(w), "on_days_share": round(held / max(1, sum(1 for t in days if lo <= t <= hi)), 4),
           "overlay": r1, "a_alone": r0, "cagr_gain": round(raw["cagr_gain"] * 100, 3),
           "win_inv_mean_pct": round(sum(z[2] for z in w) / len(w) * 100, 4) if w else None,
           "win_a_mean_pct": round(sum(z[3] for z in w) / len(w) * 100, 4) if w else None,
           "win_diff_mean_pct": round(diff * 100, 4) if w else None, "year_gain_pct": years(rets1, rets0)}
    if boot:
        m, (l, u) = boot_diff(rets1, rets0)
        raw["boot_lo"] = l
        out["daily_diff_mean_pct"], out["daily_diff_ci95_pct"] = round(m * 100, 5), [round(l * 100, 5), round(u * 100, 5)]
    return out, raw, nav, wins, open_


def choose(raws):
    """창 MIN_WIN개 이상인 판 가운데 반올림 전 연복리 증분이 가장 큰 판 · 원시값이 정확히 같을 때만 표의 앞 판."""
    ok = [v for v in VARIANTS if v in raws and raws[v]["windows"] >= MIN_WIN]
    if not ok:
        return None
    best = max(raws[v]["cagr_gain"] for v in ok)
    return [v for v in ok if raws[v]["cagr_gain"] == best][0]


def loss_ok(raws):
    """네 경로(Train · Validation × 기본 · 스트레스) 모두 하루 · 달력 달 TWR ≥ −15%(반올림 전 값)."""
    return all(r["worst_day"] >= -0.15 and r["worst_month"] >= -0.15 for r in raws)


def liquidity(code, base, wins, lo, hi):
    """창 시작 날 옮긴 돈(그날 덧댄 NAV 대신 A NAV × 20% 근사) ÷ 그 앞 20거래일 거래대금 가운데값(참고 · 판정 아님)."""
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


def train_phase(base, inv):
    """Train 고르기 — 2021-12-30 뒤 자료를 물리적으로 버린 뒤에만 셈(지표 앞 자료는 그대로)."""
    base_t, inv_t = cut_base(base, TRAIN[1]), cut_inv(inv, TRAIN[1])
    start = min(base_t)
    res, raws = {"train": {}}, {}
    for v in VARIANTS:
        res["train"][v], raws[v], _, _, _ = evaluate(v, base_t, inv_t, MAIN, *TRAIN, start)
    pick = choose(raws)
    res["pick"] = pick
    res["pick_train_gain_raw"] = raws[pick]["cagr_gain"] if pick else None
    if pick:
        _, _, nav, wins, open_ = evaluate(pick, base_t, inv_t, MAIN, *TRAIN, start)
        res["pick_trades"] = [[s, e, round(x * 100, 6), round(y * 100, 6)] for s, e, x, y in wins]
        res["pick_open"] = open_
        res["pick_nav"] = [[d, round(x, 6)] for d, x in nav]
        st, sraw, _, _, _ = evaluate(pick, base_t, inv_t, STRESS, *TRAIN, start)
        res["pick_train_stress"] = st
        raws["_pick_stress"] = sraw
    return res, raws


def valid_phase(pick, base, inv, nas, train_raws):
    """고른 한 판만. 2021-12-30 종가에 A만 100% · 인버스 0으로 새로 시작(Train 끝 포지션 · NAV는 이어받지 않음).
    신호 지표는 그 앞 자료를 그대로 씀(앞 날 값만). 첫 진입도 같은 규칙: x 종가 들고 있음 = on[x 앞 날]."""
    lo, hi = VALID
    base_v, inv_v = cut_base(base, hi), cut_inv(inv, hi)
    start = max(d for d in base_v if d <= TRAIN[1])
    m, mraw, _, wins, open_ = evaluate(pick, base_v, inv_v, MAIN, lo, hi, start, boot=True)
    s, sraw, _, _, _ = evaluate(pick, base_v, inv_v, STRESS, lo, hi, start)
    out = {"start": start, "main": m, "stress": s, "open_at_end": open_, "liquidity": liquidity(INV, base_v, wins, lo, hi)}
    c1 = mraw["cagr_gain"] > 0 and sraw["cagr_gain"] > 0
    c2 = mraw["windows"] >= MIN_WIN and mraw["win_diff"] is not None and mraw["win_diff"] > 0
    c3 = mraw["boot_lo"] > 0
    c4 = loss_ok([train_raws[pick], train_raws["_pick_stress"], mraw, sraw])
    out["conditions"] = {"1_cagr_main_and_stress": c1, "2_window_diff": c2, "3_boot_ci": c3,
                         "4_loss_limit_4paths": c4, "5_cut": "--compare로 따로"}
    out["loss_paths_pct"] = {k: [round(r["worst_day"] * 100, 3), round(r["worst_month"] * 100, 3)] for k, r in
                             (("train_main", train_raws[pick]), ("train_stress", train_raws["_pick_stress"]),
                              ("valid_main", mraw), ("valid_stress", sraw))}
    if nas:
        out["nasdaq_reference"] = evaluate(pick, base_v, cut_inv(nas, hi), MAIN, lo, hi, start)[0]
    out["verdict_before_cut"] = "EXPLORATORY_SIGNAL_CANDIDATE" if all((c1, c2, c3, c4)) else "REJECTED"
    return out


def run(base, inv, nas=None, to=""):
    if to:   # 자르기 셈: 원자료를 그날까지 버리고 Train 단계만
        base, inv = cut_base(base, to), cut_inv(inv, to)
    res, raws = train_phase(base, inv)
    res = {"task": "USINV-0039", "round": 2, "T_TO": to or None, **res, "valid": None}
    if to:
        return res
    if res["pick"] and res["pick_train_gain_raw"] > 0:
        res["valid"] = valid_phase(res["pick"], base, inv, nas, raws)
        res["verdict_before_cut"] = res["valid"]["verdict_before_cut"]
    else:
        res["verdict_before_cut"] = "REJECTED(Train 고른 판 증분 ≤ 0 또는 고를 판 없음 · Validation 열지 않음)"
    return res


def compare(a, b):
    x, y = json.loads(Path(a).read_text()), json.loads(Path(b).read_text())
    bad = [k for k in CUT_KEYS if x.get(k) != y.get(k)]
    print(json.dumps({"cut_keys": CUT_KEYS, "different": bad, "same": not bad}, ensure_ascii=False))
    return 0 if not bad else 1


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--compare":
        return compare(sys.argv[2], sys.argv[3])
    check()
    res = run(base_nav(), load(INV), load(NAS), TO)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
