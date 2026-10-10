"""OVN-0032(NEW-BOT-0027 C5-ETF) — KODEX 200(069500) 오버나이트: t 종가에 사서 다음 거래일 시가에 팖(N · 주가설 하나).
대조: D = 같은 날 시가에 사서 종가에 팖(사전 고정 대조) · 현금 · 069500 매수 · 보유(분배금 포함 · 산 비용 · 판 비용 1번씩).
사전등록: research-exchange/claude-to-gpt/OVN-0032/PREREG.md
- 가격: etf-ohlc/069500.json의 원주가(raw · FID_ORG_ADJ_PRC=1) 시가 · 종가. 거래일 = 그 파일의 날(다음 줄 = 다음 거래일).
- 분배금: OVN-0032/dist.json(분배락 날 · 1주당 현금). N이 분배락 날 앞날 종가에 들고 있으면(= 분배락 날 시가에 팖) 현금을 받음.
  주 판정은 세후(배당소득세 15.4% 원천징수 → 84.6%) 현금 · 보조표는 가격만(분배금 0) · 세전.
- 비용(편도, 그날 체결 가격 P 원주가): 수수료 0.015% + 미끄러짐 k호가 × 호가 상한(그해) ÷ P. 주 k = 1 · 스트레스 k = 3(수수료 0.03%).
  호가 상한 = 그해 원주가 시가 · 고가 · 저가 · 종가 전부의 최대공약수(호가 단위는 모든 체결 가격을 나누므로 단위 ≤ 최대공약수):
  2002 ~ 2004 10원 · 2005 ~ 5원(2025 ~ 2026은 최대공약수 1이지만 5원으로 둠 · 더 보수적). ETF 매도 거래세 없음(국내 주식형 ETF 면제).
- 2002 ~ 2010 분배금(한투 수정 계수 역산 · 독립 원천 없음)은 두 가지로 셈: est = 역산값 · zero = 0원. 판정은 둘 다 통과해야 함(GPT #167 6092887504 (c)).
- 계좌 NAV: N은 날마다 '앞날 종가 → 오늘 시가' 한 번 · 그 밖은 현금(이자 0). 하루 수익은 판 날(오늘)에 둠.
python3 research/t004.py            (T_TO=YYYYMMDD면 가격 · 분배금(분배락 날 기준)을 그날까지만 읽음 — 자르기 시험)"""
import hashlib
import json
import math
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "etf-ohlc/069500.json"
DIST = ROOT / "research-exchange/claude-to-gpt/OVN-0032/dist.json"
SHA = json.loads((ROOT / "research-exchange/claude-to-gpt/OVN-0032/sha256.json").read_text())
TO = os.getenv("T_TO", "")
FEE = 0.00015
MAIN, STRESS = (FEE, 1), (0.0003, 3)
TAX = 0.154
PERIODS = {"A": ("20021014", "20121231"), "B": ("20130101", "20191231"), "C": ("20200101", "20260930"), "ALL": ("20021014", "20260930")}
BLOCK, REPS, SEED = 6, 10000, 20261010


def check():
    for p, h in ((SRC, SHA["etf-ohlc/069500.json"]), (DIST, SHA["dist.json"])):
        g = hashlib.sha256(p.read_bytes()).hexdigest()
        if g != h:
            sys.exit(f"해시 다름 {p.name} {g}")


def load():
    raw = [x for x in json.loads(SRC.read_text())["raw"] if not TO or x[0] <= TO]
    rows = [x for x in json.loads(DIST.read_text())["rows"] if not TO or x["ex_date"] <= TO]
    dist = {"est": {x["ex_date"]: x["cash"] for x in rows},
            "zero": {x["ex_date"]: x["cash"] for x in rows if x["record_date"] is not None}}  # 2002 ~ 2010 역산분 0원
    for x in raw:
        if not (x[1] and x[1] > 0 and x[4] > 0):
            sys.exit(f"NEEDS_DATA: 시가 · 종가 없음 {x[0]}")
    return raw, dist


def tick(day):
    """그해 호가 단위 상한(원) — PREREG 3절 · 해마다 원주가 값들의 최대공약수에서."""
    return 10.0 if day < "20050101" else 5.0


def side(price, cost, day):
    fee, ticks = cost
    return fee + ticks * tick(day) / price


def trades(raw, dist, cost, mode):
    """mode: 'N'(앞날 종가 → 오늘 시가) · 'D'(오늘 시가 → 오늘 종가). 결과 [(산 날, 판 날, 순수익)].
    분배금: N은 오늘이 분배락 날이면 현금(세후 · 'pre'면 세전 · 'price'면 0)을 받음. D는 받지 않음."""
    out = []
    for i in range(1, len(raw)):
        y, t = raw[i - 1], raw[i]
        if mode.startswith("N"):
            b, s = y[4], t[1]
            cash = dist.get(t[0], 0.0)
            cash = 0.0 if mode == "N_price" else cash if mode == "N_pre" else cash * (1 - TAX)
            ret = (s * (1 - side(s, cost, t[0])) + cash) / (b * (1 + side(b, cost, y[0]))) - 1
            out.append((y[0], t[0], ret))
        else:
            b, s = t[1], t[4]
            out.append((t[0], t[0], s * (1 - side(s, cost, t[0])) / (b * (1 + side(b, cost, t[0]))) - 1))
    return out


def hold(raw, dist, lo, hi, cost):
    """매수 · 보유: 기간 첫날 종가에 사고(산 비용 1번) 날마다 종가 평가 · 분배금 세후 현금으로 쌓음(이자 0) · 끝날 판 비용."""
    rows = [x for x in raw if lo <= x[0] <= hi]
    if not rows:
        return []
    b = rows[0][4] * (1 + side(rows[0][4], cost, rows[0][0]))
    cash, nav = 0.0, []
    for n, x in enumerate(rows):
        if n and x[0] in dist:
            cash += dist[x[0]] * (1 - TAX)
        px = x[4] * (1 - side(x[4], cost, x[0])) if n == len(rows) - 1 else x[4]
        nav.append((x[0], (px + cash) / b))
    return nav


def within(rows, lo, hi):
    return [r for r in rows if lo <= r[0] and r[1] <= hi]


def nav_of(ts, raw, lo, hi):
    """기간 안 매매로 현금 1에서: 날마다(그 기간 거래일) 그날 판 매매 수익을 곱함 · 매매 없는 날은 그대로."""
    by = {s: r for _, s, r in ts}
    v, out = 1.0, []
    for x in raw:
        if lo <= x[0] <= hi:
            v *= 1 + by.get(x[0], 0.0)
            out.append((x[0], v))
    return out


def risk(navs):
    rets, last = [], 1.0
    for d, v in navs:
        rets.append((d, v / last - 1))
        last = v
    mon = defaultdict(lambda: 1.0)
    for d, r in rets:
        mon[d[:6]] *= 1 + r
    peak, mdd = 1.0, 0.0
    for _, v in navs:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    yrs = len(rets) / 245
    wd = min(rets, key=lambda x: x[1])
    wm = min(mon.items(), key=lambda x: x[1])
    return {"cagr": round((navs[-1][1] ** (1 / yrs) - 1) * 100, 3), "worst_day": [wd[0], round(wd[1] * 100, 3)],
            "worst_month": [wm[0], round((wm[1] - 1) * 100, 3)], "mdd": round(mdd * 100, 3), "end": round(navs[-1][1], 6)}


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def summary(xs):
    return {"n": len(xs), "mean_pct": round(sum(xs) / len(xs) * 100, 5), "median_pct": round(median(xs) * 100, 5),
            "win_pct": round(sum(1 for x in xs if x > 0) / len(xs) * 100, 2)}


def boot(pairs):
    """달력 달 블록 부트스트랩(6달 · 10,000번 · 씨앗 20261010). pairs: [(판 날, a, b)] — a 평균과 a − b 평균의 95% 구간."""
    bm = defaultdict(list)
    for d, a, b in pairs:
        bm[d[:6]].append((a, b))
    months = sorted(bm)
    rng = random.Random(SEED)
    nb = math.ceil(len(months) / BLOCK)
    ma, md = [], []
    for _ in range(REPS):
        xs = []
        for _ in range(nb):
            s = rng.randrange(0, len(months) - BLOCK + 1)
            for m in months[s:s + BLOCK]:
                xs += bm[m]
        ma.append(sum(a for a, _ in xs) / len(xs))
        md.append(sum(a - b for a, b in xs) / len(xs))
    q = lambda v, p: sorted(v)[int(p * (len(v) - 1))]
    return [round(q(ma, .025) * 100, 5), round(q(ma, .975) * 100, 5)], [round(q(md, .025) * 100, 5), round(q(md, .975) * 100, 5)]


def evaluate(raw, dist):
    out = {}
    n, ns, d_ = trades(raw, dist, MAIN, "N"), trades(raw, dist, STRESS, "N"), trades(raw, dist, MAIN, "D")
    npx, npre = trades(raw, dist, MAIN, "N_price"), trades(raw, dist, MAIN, "N_pre")
    dmap = {s: r for _, s, r in d_}
    for p, (lo, hi) in PERIODS.items():
        a, s, dd = within(n, lo, hi), within(ns, lo, hi), within(d_, lo, hi)
        if not a:
            continue
        ci_n, ci_nd = boot([(x[1], x[2], dmap.get(x[1], 0.0)) for x in a])
        hn = hold(raw, dist, max(lo, a[0][0]), hi, MAIN)
        hret = {hn[i][0]: hn[i][1] / hn[i - 1][1] - 1 for i in range(1, len(hn))}
        _, ci_nh = boot([(x[1], x[2], hret.get(x[1], 0.0)) for x in a])
        out[p] = {"N": summary([x[2] for x in a]), "N_stress": summary([x[2] for x in s]), "D": summary([x[2] for x in dd]),
                  "N_price_only": summary([x[2] for x in within(npx, lo, hi)]), "N_pre_tax": summary([x[2] for x in within(npre, lo, hi)]),
                  "N_mean_ci95_pct": ci_n, "N_minus_D_ci95_pct": ci_nd, "N_minus_hold_daily_ci95_pct": ci_nh,
                  "risk_N": risk(nav_of(a, raw, lo, hi)), "risk_N_stress": risk(nav_of(s, raw, lo, hi)),
                  "risk_D": risk(nav_of(dd, raw, lo, hi)), "risk_hold": risk(hn)}
    return out, n


def main():
    check()
    raw, dists = load()
    out = {"task": "OVN-0032", "round": 2, "first": raw[0][0], "last": raw[-1][0], "T_TO": TO or None, "days": len(raw),
           "dist_used": {k: len(v) for k, v in dists.items()}, "sha256": SHA}
    for k in ("est", "zero"):
        out[k], n = evaluate(raw, dists[k])
        out[k]["trades_N"] = [[b, s_, round(x * 100, 7)] for b, s_, x in n]
        out[k]["navs_all_N"] = [[d, round(v, 12)] for d, v in nav_of(n, raw, raw[0][0], raw[-1][0])]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
