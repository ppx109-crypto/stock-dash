"""CC-0038 — 횡보장 커버드콜: 달마다 첫 거래일 t에 '횡보'면 TIGER 200커버드콜5%OTM(166400)을 t+1 종가에 사서 다음 달 같은 자리(t'+1 종가)에 팖.
사전등록: research-exchange/claude-to-gpt/CC-0038/PREREG.md
- 횡보(t까지 069500 원주가 · 분배금 무관 값만): |60일 수익| < 5%  그리고  20일 실현 변동성 < 앞 250거래일 20일 변동성들의 가운데값.
- 수익: 원주가 시가 · 종가 + 분배금 현금(세후 84.6%) — 분배락 날 앞날 종가에 들고 있으면 받음. 2022-04 전 분배금은 예탁원 목록이 없어
  한투 수정 계수 역산(est) · 0원(zero) 두 가정(판정은 둘 다 통과). 비용은 OVN-0032와 같은 날마다 호가 상한 + 수수료(t004.side 꼴 · 종목별 원주가).
- 대조: 같은 달 069500 보유(분배금 같은 방식) · 166400 늘 보유 · 현금.
python3 research/t008.py            (T_TO=YYYYMMDD — 자르기 시험)"""
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
BOX = ROOT / "research-exchange/claude-to-gpt/CC-0038"
SHA = json.loads((BOX / "sha256.json").read_text())
TO = os.getenv("T_TO", "")
CC, IX = "166400", "069500"
R60, VMED, VWIN, LIM = 60, 250, 20, 0.05
FEE, TAX = 0.00015, 0.154
MAIN, STRESS = (FEE, 1), (0.0003, 3)
PERIODS = {"A": ("20131001", "20191231"), "B": ("20200101", "20260916"), "ALL": ("20131001", "20260916")}
BLOCK, REPS, SEED = 6, 10000, 20261010
BASE = BOX / "base_m1.csv"   # ACCT-NAV-0035 A(MAXRET-0026 m1 · 흔들림 상한 1배 · 20170201 ~ 20260916)
BANDS = (1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000)


def check():
    for rel, h in SHA.items():
        g = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if g != h:
            sys.exit(f"해시 다름 {rel}")


def old_stock_tick(p):
    for lim, t in ((1000, 1), (5000, 5), (10000, 10), (50000, 50), (100000, 100), (500000, 500)):
        if p < lim:
            return t
    return 1000


def ticks(raw):
    out = {}
    for x in raw:
        v = [int(round(t)) for t in x[1:5] if t]
        g = 0
        for t in v:
            g = math.gcd(g, t)
        if any(min(v) < b <= max(v) for b in BANDS):
            g = max(g, old_stock_tick(max(v)))
        out[x[0]] = float(g)
    return out


def side(price, cost, tick):
    fee, k = cost
    return fee + k * tick / price


def dist_table(d):
    """(est, zero) {분배락 날: 1주당 현금}. 예탁원 목록(기준일 바로 앞 거래일 = 분배락) + 그 첫 해 전은 수정 계수 역산(est만)."""
    a = {x[0]: x for x in d["adjusted"]}
    r = {x[0]: x for x in d["raw"]}
    days = sorted(a)
    k = {t: r[t][4] / a[t][4] for t in days}

    def fac(i):
        pre = sum(k[days[j]] for j in range(i - 3, i)) / 3
        post = sum(k[days[j]] for j in range(i, i + 3)) / 3
        return post / pre
    ksd = {}
    for x in d["dividends"]:
        prior = [j for j, t in enumerate(days) if t < x["record_date"]]
        if prior:
            ksd[days[prior[-1]]] = x["per_share_cash"]
    first = min(ksd) if ksd else "99999999"
    est = dict(ksd)
    for i in range(4, len(days) - 3):
        t = days[i]
        if t >= first[:4] + "0101":
            break
        if abs(fac(i) - 1) > 1e-3 and abs(k[t] / k[days[i - 1]] - 1) > 1e-3 and not any(abs(days.index(e) - i) <= 2 for e in est if e < first):
            est[t] = round(r[days[i - 1]][4] * (1 - fac(i)), 1)
    return est, dict(ksd)


def load(code):
    d = json.loads((ROOT / f"etf-ohlc/{code}.json").read_text())
    if TO:   # 원자료까지 절단(분배금 표도 자른 자료로만 만듦 · round 1 고침)
        d = dict(d, raw=[x for x in d["raw"] if x[0] <= TO], adjusted=[x for x in d["adjusted"] if x[0] <= TO],
                 dividends=[x for x in d["dividends"] if x["record_date"] <= TO])
    raw = d["raw"]
    est, zero = dist_table(d)
    return raw, ticks(raw), est, zero


def sideways(ix, days):
    """{신호 날 t: 횡보 여부} — t까지 069500 원주가 종가만(t 종가 확정 뒤 판단 · 체결은 t+1)."""
    px = {x[0]: x[4] for x in ix}
    ds = [d for d in days if d in px]
    lr = {ds[i]: math.log(px[ds[i]] / px[ds[i - 1]]) for i in range(1, len(ds))}
    vol = {}
    for i in range(VWIN, len(ds)):
        w = [lr[ds[j]] for j in range(i - VWIN + 1, i + 1)]
        vol[ds[i]] = statistics.pstdev(w)
    out = {}
    for i in range(max(R60, VWIN + VMED), len(ds)):
        t = ds[i]
        if ds[i - 1][:6] == t[:6]:
            continue
        past = [vol[ds[j]] for j in range(i - VMED, i) if ds[j] in vol]
        if len(past) < VMED or t not in vol:
            continue
        r60 = px[t] / px[ds[i - R60]] - 1
        out[t] = abs(r60) < LIM and vol[t] < statistics.median(past)
    return out


def hold(raw, tk, dist, b_i, s_i, cost, tax=True):
    """b_i 칸 종가에 사서 s_i 칸 종가에 팜(s_i가 None이면 열린 채 마지막 날까지 · 판 비용 없음) · 그 사이 분배락 날 현금 받음."""
    b = raw[b_i][4] * (1 + side(raw[b_i][4], cost, tk[raw[b_i][0]]))
    cash, path = 0.0, [(raw[b_i][0], raw[b_i][4] / b)]
    end = s_i if s_i is not None else len(raw) - 1
    for x in range(b_i + 1, end + 1):
        d = raw[x][0]
        if d in dist:
            cash += dist[d] * ((1 - TAX) if tax else 1)
        px = raw[x][4] * (1 - side(raw[x][4], cost, tk[d])) if x == s_i else raw[x][4]
        path.append((d, (px + cash) / b))
    return path


def windows(sig, days):
    """[(신호 t, 산 날 = t+1, 판 날 = 다음 신호 +1)] — 판 날이 없으면 열린 채로 빼고, 산 날 = 앞 판 날이면 같은 종가."""
    ts = sorted(sig)
    idx = {d: i for i, d in enumerate(days)}
    out = []
    for k in range(len(ts)):
        bi = idx[ts[k]] + 1
        if bi >= len(days):
            break
        si = idx[ts[k + 1]] + 1 if k + 1 < len(ts) else None
        # 판 날이 자료 밖이면 열린 구간(판 날 None) — NAV는 마지막 날까지 적고 매매 목록에는 넣지 않음(round 1 고침)
        out.append((ts[k], days[bi], days[si] if si is not None and si < len(days) else None, sig[ts[k]]))
    return out


def run(code_raw, tk, dist, wins, cost, which):
    """which: 'on'(횡보 달만) · 'all'(늘). [(산 날, 판 날, 순수익, 횡보)] · NAV(날마다 · 현금 날 포함)."""
    days = [x[0] for x in code_raw]
    idx = {d: i for i, d in enumerate(days)}
    trades, nav, V = [], [], 1.0
    for t, b, s, on in wins:
        if b not in idx or (s is not None and s not in idx):
            continue
        si = idx[s] if s is not None else None
        end = si if si is not None else len(days) - 1
        if which == "on" and not on:
            for x in range(idx[b] + (0 if not nav or nav[-1][0] != b else 1), end + 1):
                nav.append((days[x], V))
            continue
        path = hold(code_raw, tk, dist, idx[b], si, cost)
        start = V
        for d, v in path:
            if nav and nav[-1][0] == d:
                nav[-1] = (d, start * v)
            else:
                nav.append((d, start * v))
        V = start * path[-1][1]
        if s is not None:
            trades.append((b, s, path[-1][1] - 1, on))
    assert all(nav[z][0] < nav[z + 1][0] for z in range(len(nav) - 1)), "NAV 날짜 순서"
    return trades, nav


def risk(navs, lo, hi):
    before = [v for d, v in navs if d < lo]
    base0 = before[-1] if before else 1.0
    nv = [(d, v / base0) for d, v in navs if lo <= d <= hi]
    rets, last = [], 1.0
    for d, v in nv:
        rets.append((d, v / last - 1))
        last = v
    mon = defaultdict(lambda: 1.0)
    for d, r in rets:
        mon[d[:6]] *= 1 + r
    peak, mdd = 1.0, 0.0
    for _, v in nv:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    wd = min(rets, key=lambda x: x[1])
    wm = min(mon.items(), key=lambda x: x[1])
    return {"cagr": round((nv[-1][1] ** (245 / len(rets)) - 1) * 100, 3), "worst_day": [wd[0], round(wd[1] * 100, 3)],
            "worst_month": [wm[0], round((wm[1] - 1) * 100, 3)], "mdd": round(mdd * 100, 3)}


def months_between(lo, hi):
    y, m = int(lo[:4]), int(lo[4:6])
    out = []
    while f"{y:04d}{m:02d}" <= hi[:6]:
        out.append(f"{y:04d}{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def paired(a, c, lo, hi):
    """같은 산 날 짝 (CC − 069500). 부트스트랩: 기간의 **달력 달 전체**(짝 없는 달 포함)에서 연속 6달 블록을
    ceil(달 수 ÷ 6)개 뽑아(시작 달은 0 ~ 달 수 − 6에서 고르게) 그 블록들에 든 짝만 합쳐 평균(조건부 평균).
    짝이 0인 복제는 버리고 수를 적음 · 버린 복제가 5% 넘으면 구간 없음(None = 조건 실패). round 1 고침."""
    cm = {r[0]: r[2] for r in c}
    pairs = [(r[0], r[2] - cm[r[0]]) for r in a if r[0] in cm]
    by = defaultdict(list)
    for d, x in pairs:
        by[d[:6]].append(x)
    months = months_between(lo, hi)
    if not pairs or len(months) < BLOCK:
        return None, None, len(pairs), None
    rng = random.Random(SEED)
    nb = math.ceil(len(months) / BLOCK)
    ms, empty = [], 0
    for _ in range(REPS):
        xs = []
        for _ in range(nb):
            st = rng.randrange(0, len(months) - BLOCK + 1)
            for m in months[st:st + BLOCK]:
                xs += by.get(m, [])
        if xs:
            ms.append(sum(xs) / len(xs))
        else:
            empty += 1
    mean = round(sum(x for _, x in pairs) / len(pairs) * 100, 4)
    if empty > 0.05 * REPS:
        return mean, None, len(pairs), empty
    q = lambda v, p: sorted(v)[int(p * (len(v) - 1))]
    return mean, [round(q(ms, .025) * 100, 4), round(q(ms, .975) * 100, 4)], len(pairs), empty


def combined(navc, buys, lo, hi):
    """기준 A 80% + 후보 20% · 후보 산 날마다 되돌림(옮긴 돈 편도 0.065%) · LOAN-0037 t007.combine과 같은 시간축 규칙."""
    import csv
    base = {r["날"]: float(r["NAV"]) for r in csv.DictReader(BASE.open(encoding="utf-8")) if not TO or r["날"] <= TO}
    lo = max(lo, min(base))
    bdays = sorted(base)
    days = [d for d in bdays if lo <= d <= hi]
    cmap, cv, last = dict(navc), {}, 1.0
    for d in bdays:
        if d in cmap:
            last = cmap[d]
        cv[d] = last
    prev = [d for d in bdays if d < lo]
    p0 = prev[-1] if prev else days[0]
    a, b, pa, pc, out = 0.8, 0.2, base[p0], cv[p0], []
    for d in days:
        a *= base[d] / pa
        b *= cv[d] / pc
        pa, pc = base[d], cv[d]
        if d in buys:
            tot = a + b
            tot -= abs(b - 0.2 * tot) * 0.00065
            a, b = 0.8 * tot, 0.2 * tot
        out.append((d, a + b))
    return out


def main():
    check()
    craw, ctk, cest, czero = load(CC)
    iraw, itk, iest, izero = load(IX)
    days = [x[0] for x in craw]
    sig = sideways(iraw, days)
    wins = windows(sig, days)
    out = {"task": "CC-0038", "round": 2, "T_TO": TO or None, "signals": len(sig), "sideways_months": sum(sig.values()),
           "windows": len(wins), "first_signal": min(sig) if sig else None}
    for k, (cd, idd) in {"est": (cest, iest), "zero": (czero, izero)}.items():
        on, navon = run(craw, ctk, cd, wins, MAIN, "on")
        ons, navs = run(craw, ctk, cd, wins, STRESS, "on")
        ixo = run(iraw, itk, idd, [w for w in wins if w[3]], MAIN, "all")[0]
        alw, navall = run(craw, ctk, cd, wins, MAIN, "all")
        out[k] = {}
        for p, (lo, hi) in PERIODS.items():
            a = [r for r in on if lo <= r[0] and r[1] <= hi]
            s_ = [r for r in ons if lo <= r[0] and r[1] <= hi]
            c_ = [r for r in ixo if lo <= r[0] and r[1] <= hi]
            if not a:
                out[k][p] = {"n": 0}
                continue
            m, ci, n, empty = paired(a, c_, lo, hi)
            out[k][p] = {"n": len(a), "cc_mean_pct": round(sum(r[2] for r in a) / len(a) * 100, 4),
                         "cc_stress_mean_pct": round(sum(r[2] for r in s_) / len(s_) * 100, 4),
                         "ix_same_months_mean_pct": round(sum(r[2] for r in c_) / len(c_) * 100, 4) if c_ else None,
                         "cc_minus_ix_mean_pct": m, "cc_minus_ix_ci95_pct": ci, "pairs": n, "boot_empty_reps": empty,
                         "risk_on": risk(navon, lo, hi), "risk_on_stress": risk(navs, lo, hi), "risk_always_cc": risk(navall, lo, hi),
                         "risk_combined": risk(combined(navon, {r[0] for r in on}, lo, hi), max(lo, "20170201"), hi),
                         "risk_combined_stress": risk(combined(navs, {r[0] for r in ons}, lo, hi), max(lo, "20170201"), hi)}
        out[k]["trades_on"] = [[b, s, round(x * 100, 6)] for b, s, x, _ in on]
        out[k]["navs_on"] = [[d, round(v, 12)] for d, v in navon]
    out["signals_list"] = sorted([t, v] for t, v in sig.items())
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
