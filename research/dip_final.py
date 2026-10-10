"""DIP-DEEP-0042 마지막 시험(H) — 잠근 후보 R2를 2023-01-02 ~ 2026-09-16에서 한 번 셈(FINAL-PREREG.md).
- 자료: dip_build.py를 DIP_CUT=20260916 · DIP_SNAP=/tmp/dip-h.pkl로 구운 스냅샷(해시는 h_snapshot.json에 고정 · 다르면 멈춤).
- 규칙(잠금 · dip_rules.py 'R1-hb60-br40'과 같은 식을 여기 옮겨 고정): 시총 100위 안 · 069500 앞 60일 |수익| < 3% · 종가 ≥ 앞 60일 최고 종가 ·
  시장 폭 ≥ 40 · 전날까지 5일 외국인 > 0 · 투신 > 0 → 2칸 · 순서 20일 상대 강세 큰 순 · +5 / −7 / 10일 · 왕복 0.25% · 씨앗 8 · settle_end.
- 모드: --repro-d(개발 스냅샷으로 D1 · D2를 다시 셈 → R2 기록과 같은지 · 옮긴 규칙 확인용) · --h(마지막 시험 · 한 번)
python3 research/dip_final.py --repro-d | --h"""
import bisect
import hashlib
import json
import math
import os
import pickle
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
sys.path.insert(0, str(ROOT))
BOX = ROOT / "research-exchange/claude-to-gpt/DIP-DEEP-0042"
import lab  # noqa: E402

COST, SLOTS, CAP, KIN = 0.25, 10, 130, 0.6
H = ("20230102", "20260916")
D1, D2 = ("20170102", "20191230"), ("20200102", "20221229")
SEEDS, BLOCK, REPS, BSEED = 8, 6, 10000, 20261010


def load(path, lockfile):
    blob = Path(path).read_bytes()
    want = json.loads((BOX / lockfile).read_text())["snapshot_sha256"]
    if hashlib.sha256(blob).hexdigest() != want:
        sys.exit(f"스냅샷 해시 다름 {path} — 셈하지 않음")
    return pickle.loads(blob)


class Data:
    def __init__(self, s):
        self.cut, self.prices, self.rows, self.BR, self.FLOW, self.IX = s["cut"], s["prices"], s["rows"], s["br"], s["flow"], s["ix"]
        self.IXD = sorted(self.IX)
        self.LANES = lab.lanes(self.prices)

    def flow_sum(self, r, n, col):
        got = self.FLOW.get(r["code"])
        if not got:
            return None
        days, acc, ok = got
        k = bisect.bisect_left(days, r["date"])
        lo = k - n
        if lo < 0 or ok[k] - ok[lo] < n:
            return None
        return acc[col][k] - acc[col][lo]

    def ret(self, r, n):
        c = self.LANES[r["code"]]["closes"]
        i = r["i"]
        return None if i < n or i >= len(c) else (c[i] / c[i - n] - 1) * 100

    def ix_ret(self, day, n):
        k = bisect.bisect_right(self.IXD, day) - 1
        return None if k < n else (self.IX[self.IXD[k]] / self.IX[self.IXD[k - n]] - 1) * 100

    # ── 잠근 규칙 R2 ──
    def holds(self, r):
        v = self.ix_ret(r["date"], 60)
        if v is None or abs(v) >= 3.0:
            return False
        c = self.LANES[r["code"]]["closes"]
        i = r["i"]
        if not (i >= 60 and c[i] >= max(c[i - 60:i])):
            return False
        if self.BR.get(r["date"], 0) < 40:
            return False
        f, t = self.flow_sum(r, 5, "외국인"), self.flow_sum(r, 5, "투신")
        return f is not None and t is not None and f > 0 and t > 0

    def rank(self, r):
        a, b = self.ret(r, 20), self.ix_ret(r["date"], 20)
        return -((a - b) if a is not None and b is not None else 0)


def exits(lane, start, price, step, peak, row=None):
    now = (lane["closes"][start + step] / price - 1) * 100
    return now >= 5 or now <= -7 or step >= 10


def seg_prices(d, hi):
    p = {c: {**b, "rows": [x for x in b["rows"] if x[0] <= hi]} for c, b in d.prices.items()}
    return {c: b for c, b in p.items() if b["rows"]}


def engine(d, lo, hi, tries=SEEDS):
    p = seg_prices(d, hi)
    lanes = lab.lanes(p)
    pool = [r for r in d.rows if lo <= r["date"] <= hi and r["code"] in lanes and r["i"] < len(lanes[r["code"]]["closes"])]
    holds = lambda r: r["date"] < hi and d.holds(r)
    g = lab.wobble(pool, p, holds, exits, tries=tries, rank=d.rank, slots=SLOTS, since=lo, per_day=None,
                   apart=lab.unlike(lab.moves(p), edge=KIN), realistic=True, cap=CAP, detail=True, size=lambda r: 2,
                   cost=COST, settle_end=True)
    return g, pool, lanes


def luck(led, since):
    years = max(1, int(max(t["판 날"] for t in led)[:4]) - int(since[:4]) + 1)
    w = sorted(t["손익"] * t["자리"] for t in led)
    return (round(sum(min(t["손익"], 30.0) * t["자리"] for t in led) / SLOTS / years, 2),
            round(sum(w[:-2]) / SLOTS / years, 2), years)


def nav(led, lanes, days):
    """씨앗 0 매매목록 → 날마다 평가 NAV. 산 날 종가에 (자리 ÷ 10) × 그날 NAV를 편도 0.125% 내고 삼 · 판 날 종가에 편도 0.125% 빼고 팖 ·
    종가 없는 날은 앞 종가 · 현금 이자 0. 나눠 팔기 없음(R2 팔기는 전량)."""
    by_buy, by_sell = defaultdict(list), defaultdict(list)
    for k, t in enumerate(led):
        by_buy[t["산 날"]].append(k)
        by_sell[t["판 날"]].append(k)
    px = {}
    for t in led:
        c = t["code"]
        if c not in px:
            px[c] = dict(zip(lanes[c]["날"], lanes[c]["closes"]))
    last = {}
    cash, held, out = 1.0, {}, []
    for day in days:
        for c in px:
            if day in px[c]:
                last[c] = px[c][day]
        for k in by_sell.get(day, []):
            if k in held:
                sh, c = held.pop(k)
                cash += sh * last[c] * (1 - COST / 200)
        value = cash + sum(sh * last[c] for sh, c in held.values())
        for k in by_buy.get(day, []):
            t = led[k]
            amt = value * t["자리"] / SLOTS
            amt = min(amt, cash)
            cash -= amt
            held[k] = (amt * (1 - COST / 200) / last[t["code"]], t["code"])
        out.append((day, cash + sum(sh * last[c] for sh, c in held.values())))
    return out


def twr(navs):
    rets = [(navs[i][0], navs[i][1] / navs[i - 1][1] - 1) for i in range(1, len(navs))]
    mon, yr = defaultdict(lambda: 1.0), defaultdict(lambda: 1.0)
    for d_, r in rets:
        mon[d_[:6]] *= 1 + r
        yr[d_[:4]] *= 1 + r
    wd = min(rets, key=lambda z: z[1])
    wm = min(mon.items(), key=lambda z: z[1])
    return {"worst_day": [wd[0], wd[1]], "worst_month": [wm[0], wm[1] - 1],
            "years": {k: v - 1 for k, v in sorted(yr.items())}, "end_nav": navs[-1][1]}


def control(led, pool, lanes, seed):
    """매매마다 같은 산 날 · 그날 Universe(시총 100위 안 · 그날 후보가 들고 있지 않은 종목)에서 1종목 무작위 · 같은 보유 일수 · 자리 · 비용."""
    rng = random.Random(seed)
    by_day = defaultdict(list)
    for r in pool:
        by_day[r["date"]].append(r)
    held_on = defaultdict(set)
    for t in led:
        lane = lanes[t["code"]]["날"]
        i0 = t["행"]["i"]
        for j in range(i0, min(i0 + t["들고"], len(lane) - 1) + 1):
            held_on[lane[j]].add(t["code"])
    w = []
    for t in sorted(led, key=lambda x: (x["산 날"], x["code"])):
        cands = sorted((r for r in by_day[t["산 날"]] if r["code"] not in held_on[t["산 날"]]), key=lambda r: r["code"])
        if not cands:
            continue
        r = rng.choice(cands)
        c = lanes[r["code"]]["closes"]
        j = min(r["i"] + t["들고"], len(c) - 1)
        w.append(((c[j] / c[r["i"]] - 1) * 100 - COST) * t["자리"])
    years = max(1, int(H[1][:4]) - int(H[0][:4]) + 1)
    return sum(w) / SLOTS / years


def boot(led):
    by = defaultdict(list)
    for t in led:
        by[t["판 날"][:6]].append(t["손익"])
    months = sorted(by)
    allx = [x for m in months for x in by[m]]
    rng = random.Random(BSEED)
    nb = math.ceil(len(months) / BLOCK)
    ms = []
    for _ in range(REPS):
        xs = []
        for _ in range(nb):
            s0 = rng.randrange(0, len(months) - BLOCK + 1)
            for m in months[s0:s0 + BLOCK]:
                xs += by[m]
        ms.append(sum(xs) / len(xs))
    ms.sort()
    return sum(allx) / len(allx), ms[int(.025 * (REPS - 1))], ms[int(.975 * (REPS - 1))]


def summary(g):
    return {k: g.get(k) for k in ("매매", "연수익", "폭", "최대낙폭", "골 폭", "가동률", "승률", "해마다")}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "--repro-d":
        d = Data(load("/tmp/dip-d.pkl", "snapshot.json"))
        out = {}
        for tag, (lo, hi) in (("D1", D1), ("D2", D2)):
            g, _, _ = engine(d, lo, hi)
            a, b, _ = luck(g["매매목록"], lo)
            out[tag] = {**summary(g), "행운뺌": a, "큰2건뺌": b}
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if mode != "--h":
        sys.exit("--repro-d 또는 --h")
    d = Data(load("/tmp/dip-h.pkl", "h_snapshot.json"))
    lo, hi = H
    g, pool, lanes = engine(d, lo, hi)
    res = {"task": "DIP-DEEP-0042", "phase": "H", "H": list(H)}
    if not g:
        res["verdict"] = "NEEDS_DATA(매매 60건 미만)"
        print(json.dumps(res, ensure_ascii=False))
        return 0
    led = g["매매목록"]                       # 씨앗 0 판
    a, b, years = luck(led, lo)
    days = [x for x in lab.trading_days(lanes) if lo <= x <= hi]
    navs = nav(led, lanes, days)
    tw = twr([("시작", 1.0)] + navs)          # 첫날 앞 NAV = 1(현금)
    ctl = [control(led, pool, lanes, s) for s in range(SEEDS)]
    m, bl, bu = boot(led)
    eng = summary(g)
    c0 = eng["매매"] >= 60
    c1 = eng["연수익"] > 0 and a > 0
    c2 = eng["연수익"] > statistics.median(ctl)
    c3 = tw["worst_day"][1] >= -0.15 and tw["worst_month"][1] >= -0.15
    c4 = sum(1 for v in tw["years"].values() if v > 0) >= 3
    c5 = bl > 0
    res.update({"engine": {**eng, "행운뺌": a, "큰2건뺌": b, "years_counted": years},
                "seed0_trades": len(led), "virtual_settle": {k: sum(1 for t in led if t.get("정산") == k) for k in {t.get("정산") for t in led if t.get("정산")}},
                "nav_twr": {"worst_day": tw["worst_day"], "worst_month": tw["worst_month"], "years": tw["years"], "end_nav": tw["end_nav"]},
                "control_annual": ctl, "control_median": statistics.median(ctl),
                "boot_trade_mean": [m, bl, bu],
                "conditions": {"0_trades_ge_60": c0, "1_annual_and_luck_gt0": c1, "2_beats_random_median": c2,
                               "3_twr_day_month_ge_-15": c3, "4_three_of_four_years": c4, "5_boot_lo_gt0": c5}})
    res["verdict"] = ("NEEDS_DATA" if not c0 else "EXPLORATORY_CANDIDATE" if all((c1, c2, c3, c4, c5)) else "REJECTED")
    res["ledger_seed0"] = [{k: t[k] for k in ("code", "산 날", "판 날", "들고", "자리", "손익")} | {"정산": t.get("정산")} for t in led]
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
