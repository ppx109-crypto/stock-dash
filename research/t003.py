"""STR-0030(NEW-BOT-0027 C1) — 종목 단기 반전: 5거래일마다, 전날 기준 시총 100위(상장폐지 포함 · public-daily) 가운데
전날까지 5거래일 시총 변화가 가장 나쁜 10종목을 그날 종가에 똑같이 사서 다음 바꿔 담는 날(5거래일 뒤) 종가에 팖.
- 대상 Universe(t) = t−1 거래일 public-daily 시총 순위 100위(모집단: 6자리 숫자 코드 · 끝자리 5/7/9 제외 · KOSPI + KOSDAQ). t−1 장 끝 뒤 자료라 t에 씀.
- 신호 r5 = 시총(t−1) ÷ 시총(t−6) − 1(두 날 모두 위 400에 있어야 함). 수익 = 시총(판 날) ÷ 시총(산 날)(쪼개기에 흔들리지 않음 · 증자는 부풀림 — 한계).
- 산 날 시총이 없거나 거래량 0(정지)인 종목은 건너뛰고 다음 순위로 채움. 판 날(또는 들고 있는 날) 시총이 없으면 두 가정: lo = 그 몫 0원 · hi = 마지막으로 값이 있는 날 값.
- 대조: 같은 Universe(t) 전체를 똑같이(같은 날 · 같은 비용 · 같은 결손 가정).
- 비용: 왕복 0.35%(편도 c = 1 − √(1 − 왕복)) · 스트레스 0.60%. 날마다 평가 NAV · 하루 · 달력 월 TWR.
- 달력: TOM-0028 규칙 달력(가격 파일과 따로 · sha256 고정). 자료: public-daily/*.csv(sha256 고정).
사전등록: research-exchange/claude-to-gpt/STR-0030/PREREG.md
python3 research/t003.py            (T_TO=YYYYMMDD면 public-daily를 그날까지만 읽음 — 자르기 시험)"""
import csv
import hashlib
import json
import math
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAL = ROOT / "research-exchange/claude-to-gpt/TOM-0028/calendar.json"
PD = ROOT / "public-daily"
SHA = {"calendar.json": "533806486ea09430e12fc0a67549d8f5a54b20be014b24457ec675a3e9cd7939"}
SHA_PD = json.loads((ROOT / "research-exchange/claude-to-gpt/STR-0030/public_daily_sha256.json").read_text())
TO = os.getenv("T_TO", "")
TOP, PICK, LOOK, STEP = 100, 10, 5, 5
COST, STRESS = 0.0035, 0.0060
START, END = "20200102", "20260930"
PERIODS = {"A": ("20200102", "20221231"), "B": ("20230101", "20260930"), "ALL": ("20200102", "20260930")}
BLOCK, REPS, SEED = 3, 10000, 20261010


def side(c):
    return 1 - math.sqrt(1 - c)


def pop(code):
    return bool(re.fullmatch(r"[0-9]{6}", code)) and not code.endswith(("5", "7", "9"))


def check():
    got = hashlib.sha256(CAL.read_bytes()).hexdigest()
    if got != SHA["calendar.json"]:
        sys.exit(f"달력 해시 다름 {got}")
    for name, h in SHA_PD.items():
        g = hashlib.sha256((PD / name).read_bytes()).hexdigest()
        if g != h:
            sys.exit(f"public-daily 해시 다름 {name} {g}")


def load():
    cap, vol, rank_rows = defaultdict(dict), defaultdict(dict), defaultdict(list)
    for name in sorted(SHA_PD):
        with (PD / name).open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                d = r["날"]
                if TO and d > TO:
                    continue
                c = r["코드"]
                v = float(r["시가총액(억)"])
                if v > 0:
                    cap[d][c] = v
                    vol[d][c] = float(r["거래량"])
                    if pop(c):
                        rank_rows[d].append((v, c))
    top = {d: [c for _, c in sorted(xs, key=lambda x: (-x[0], x[1]))[:TOP]] for d, xs in rank_rows.items()}
    cal = [d for d in json.loads(CAL.read_text())["days"] if START <= d <= max(cap)]
    return cap, vol, top, cal


def schedule(cal, cap):
    """바꿔 담는 날: 달력 칸 6부터 5칸마다. 그 칸 날 자료가 통째로 없으면(달력에 없는 휴장 · 예: 20260717) 자료 있는 다음 칸으로 미룸."""
    out = []
    for i in range(LOOK + 1, len(cal), STEP):
        while i < len(cal) and cal[i] not in cap:
            i += 1
        if i < len(cal) and (not out or i > out[-1]):
            out.append(i)
    return out


def back(cal, cap, i):
    """칸 i 이하에서 자료가 있는 가장 가까운 칸."""
    while i >= 0 and cal[i] not in cap:
        i -= 1
    return i


def cohorts(cap, vol, top, cal):
    """[(산 날 칸, 판 날 칸, 고른 종목, 대조 종목)]. 다음 바꿔 담는 날이 없으면 열린 채로(판 날 None).
    전날 = 산 날 앞에서 자료 있는 가장 가까운 칸 · 기준날 = 그 칸에서 달력 5칸 앞(자료 없으면 그 앞 가장 가까운 칸)."""
    out = []
    idx = schedule(cal, cap)
    for k, i in enumerate(idx):
        p = back(cal, cap, i - 1)
        q = back(cal, cap, p - LOOK)
        if p < 0 or q < 0:
            continue
        t, prev, base = cal[i], cal[p], cal[q]
        uni = top.get(prev, [])
        r5 = [(cap[prev][c] / cap[base][c] - 1, c) for c in uni if c in cap[base]]
        ok = lambda c: c in cap[t] and vol[t][c] > 0  # 산 날 하루 내내 거래 없음(정지) = 못 삼 → 건너뜀(장중에 알 수 있음)
        picks = [c for _, c in sorted(r5) if ok(c)][:PICK]
        ctl = [c for c in uni if ok(c)]
        j = idx[k + 1] if k + 1 < len(idx) else None
        out.append((i, j, picks, ctl))
    return out


def basket_path(cap, cal, i, j, names, mode, last):
    """산 날 i 종가 1.0에서 날마다 바구니 값(똑같이 · 결손: lo = 0, hi = 마지막 값). j가 None이면 last 칸까지."""
    end = j if j is not None else last
    vals = []
    for c in names:
        b = cap[cal[i]][c]
        seq, lastv = [], 1.0
        for x in range(i + 1, end + 1):
            d = cal[x]
            if d not in cap:
                seq.append(lastv)  # 자료가 통째로 없는 날 = 휴장으로 봄(그 종목 결손 아님)
            elif c in cap[d]:
                lastv = cap[d][c] / b
                seq.append(lastv)
            else:
                seq.append(0.0 if mode == "lo" else lastv)
        vals.append(seq)
    n = len(names)
    return [sum(v[s] for v in vals) / n for s in range(end - i)] if n else [1.0] * (end - i)


def trade_ret(path, c):
    k = side(c)
    return path[-1] * (1 - k) * (1 - k) - 1


def run(cap, cal, cos, c, mode, which):
    """기간마다 쓸 매매 목록 [(산 날, 판 날, 순수익)]과 날마다 NAV(전체)."""
    last = len(cal) - 1
    while cal[last] not in cap:
        last -= 1
    trades, nav, v = [], [], 1.0
    k = side(c)
    for i, j, picks, ctl in cos:
        names = picks if which == "pick" else ctl
        path = basket_path(cap, cal, i, j, names, mode, last)
        if j is not None:
            trades.append((cal[i], cal[j], trade_ret(path, c)))
        v *= 1 - k
        start = v
        for s, x in enumerate(path):
            day = cal[i + 1 + s]
            v = start * x
            if j is not None and i + 1 + s == j:
                v *= 1 - k
            if day in cap:
                nav.append((day, v))
        if j is None:
            break
    return trades, nav


def within(rows, lo, hi):
    return [r for r in rows if lo <= r[0] and r[1] <= hi]


def nav_period(cap, cal, cos, c, mode, lo, hi):
    """그 기간 안에서 산 날 · 판 날이 모두 든 바구니만으로 현금 1에서 다시(기간 경계 넘는 바구니는 뺌)."""
    sub = [x for x in cos if x[1] is not None and lo <= cal[x[0]] and cal[x[1]] <= hi]
    return run(cap, cal, sub, c, mode, "pick")[1]


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
    return {"cagr": round((navs[-1][1] ** (1 / yrs) - 1) * 100, 3), "worst_day": round(min(r for _, r in rets) * 100, 3),
            "worst_month": round((min(mon.values()) - 1) * 100, 3), "mdd": round(mdd * 100, 3), "end": round(navs[-1][1], 6)}


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def summary(xs):
    return {"n": len(xs), "mean_pct": round(sum(xs) / len(xs) * 100, 4), "median_pct": round(median(xs) * 100, 4),
            "win_pct": round(sum(1 for x in xs if x > 0) / len(xs) * 100, 2)}


def boot(t, ctl):
    months = sorted({r[0][:6] for r in t})
    bt, bc = defaultdict(list), defaultdict(list)
    for r in t:
        bt[r[0][:6]].append(r[2])
    for r in ctl:
        bc[r[0][:6]].append(r[2])
    rng = random.Random(SEED)
    nb = math.ceil(len(months) / BLOCK)
    mt, df = [], []
    for _ in range(REPS):
        xs, ys = [], []
        for _ in range(nb):
            s = rng.randrange(0, len(months) - BLOCK + 1)
            for m in months[s:s + BLOCK]:
                xs += bt[m]
                ys += bc[m]
        if xs and ys:
            a = sum(xs) / len(xs)
            mt.append(a)
            df.append(a - sum(ys) / len(ys))
    q = lambda v, p: sorted(v)[int(p * (len(v) - 1))]
    return {"pick_mean_ci95_pct": [round(q(mt, .025) * 100, 4), round(q(mt, .975) * 100, 4)],
            "diff_ci95_pct": [round(q(df, .025) * 100, 4), round(q(df, .975) * 100, 4)]}


def main():
    check()
    cap, vol, top, cal = load()
    cos = cohorts(cap, vol, top, cal)
    out = {"task": "STR-0030", "round": 1, "first": min(cap), "last": max(cap), "T_TO": TO or None, "cohorts": len(cos),
           "calendar_days_without_data": sorted(d for d in cal if d <= max(cap) and d not in cap)}
    miss = {"lo": 0, "hi": 0}
    for mode in ("lo", "hi"):
        tp, _ = run(cap, cal, cos, COST, mode, "pick")
        tps, _ = run(cap, cal, cos, STRESS, mode, "pick")
        tc, _ = run(cap, cal, cos, COST, mode, "ctl")
        out[mode] = {}
        for p, (lo, hi) in PERIODS.items():
            a, s, c = within(tp, lo, hi), within(tps, lo, hi), within(tc, lo, hi)
            if not a:
                continue
            ma, mc = sum(r[2] for r in a) / len(a), sum(r[2] for r in c) / len(c)
            out[mode][p] = {"pick": summary([r[2] for r in a]), "pick_stress": summary([r[2] for r in s]), "control": summary([r[2] for r in c]),
                            "diff_pct": round((ma - mc) * 100, 4), **boot(a, c),
                            "risk": risk(nav_period(cap, cal, cos, COST, mode, lo, hi)),
                            "risk_stress": risk(nav_period(cap, cal, cos, STRESS, mode, lo, hi))}
        out[mode]["trades"] = [[b, s_, round(x * 100, 6)] for b, s_, x in tp]
        out[mode]["navs_all"] = [[d, round(v, 12)] for d, v in run(cap, cal, cos, COST, mode, "pick")[1]]
    # 결손(판 날 · 들고 있는 날 시총 없음) 세기
    gaps = []
    last = max(i for i, d in enumerate(cal) if d in cap)
    for i, j, picks, _ in cos:
        end = j if j is not None else last
        for c in picks:
            for x in range(i + 1, end + 1):
                if cal[x] in cap and c not in cap[cal[x]]:
                    gaps.append([cal[i], c, cal[x]])
                    break
    out["pick_gaps"] = gaps
    # 판 날 거래량 0(정지 · 실제로는 못 팔았을 수 있음) 세기 — 판정에는 안 넣고 보고만
    out["pick_sell_halt"] = [[cal[i], c, cal[j]] for i, j, picks, _ in cos if j is not None for c in picks
                             if c in cap[cal[j]] and vol[cal[j]][c] == 0]
    out["picks"] = [[cal[i], cal[j] if j is not None else None, p] for i, j, p, _ in cos]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
