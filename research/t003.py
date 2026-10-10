"""STR-0030(NEW-BOT-0027 C1) round 2 — 종목 단기 반전: 5거래일마다, 전날 시총 100위(상장폐지 포함 · public-daily-v2) 가운데
전날까지 5거래일 수정 수익이 가장 나쁜 10종목을 그날 종가에 똑같이 사서 다음 바꿔 담는 날(5거래일 뒤) 종가에 팖.
round 2(GPT #164 6091687311 고칠 것 4개 반영):
- 수익 · NAV는 시총 비율이 아니라 거래소 기준가로 맞춘 날마다 수익 g = 종가 ÷ (종가 − 대비)를 이은 값(분할 · 무상증자 · 권리락 맞춤 · 배당 빠짐).
  시총은 Universe 순위에만 씀. 신호 r5도 같은 g를 5일 이은 값.
- 고른 10종목은 전날 p까지 자료로만 고정(대체 없음). 산 날 t에 줄이 없거나 거래량 0이면 '못 삼': lo = 그 몫 0원 · hi = 그 몫 현금.
- NAV는 모든 유효 거래일 종가 뒤 값을 적고, 바꿔 담는 날에는 판 비용 · 새로 산 비용을 그날 NAV에 모두 넣음.
- 달력: TOM-0028 규칙 달력에서 공식 휴장 20260717을 뺀 유효 거래일 달력(STR-0030/calendar.json · sha256 고정)에서 5칸 간격.
  유효 거래일인데 자료가 통째로 없으면 NEEDS_DATA로 멈춤.
- 들고 있는 날 · 판 날 줄이 없으면(상장폐지 · 흡수합병 · 위 400 밖 · 대비 빈칸 · 정지 뒤 기준가를 새로 정한 거래재개 날) lo = 그 뒤 0원 · hi = 그 앞 값에서 멈춤.
  판 날 거래량 0(정지)이면 lo = 0원 · hi = 그날 종가 값(판 비용은 냄).
사전등록: research-exchange/claude-to-gpt/STR-0030/PREREG.md
python3 research/t003.py            (T_TO=YYYYMMDD면 public-daily-v2를 그날까지만 읽음 — 자르기 시험)"""
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
BOX = ROOT / "research-exchange/claude-to-gpt/STR-0030"
CAL = BOX / "calendar.json"
PD = ROOT / "public-daily-v2"
SHA_CAL = "e3b5599b9db536623a5578488415e18855118c009645001487e90020e4185227"
SHA_PD = json.loads((BOX / "public_daily_v2_sha256.json").read_text())
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
    if got != SHA_CAL:
        sys.exit(f"달력 해시 다름 {got}")
    for name, h in SHA_PD.items():
        g = hashlib.sha256((PD / name).read_bytes()).hexdigest()
        if g != h:
            sys.exit(f"public-daily-v2 해시 다름 {name} {g}")


def load():
    """cap[d][c] 시총 · vol[d][c] 거래량 · g[d][c] 그날 수정 수익 · top[d] 그날 순위 100.
    g 없음(= 그날 줄 없음과 같게 셈): 대비 빈칸 · 기준가(종가 − 대비) ≤ 0 · **앞날 거래량 0(정지)이고 오늘 기준가 ≠ 앞날 종가**
    (감자 · 재상장 뒤 거래재개는 기준가를 시초가로 새로 정해 대비가 그 틈을 못 담음 — 예: 020560 20210115)."""
    cap, vol, g, rank_rows, raw = defaultdict(dict), defaultdict(dict), defaultdict(dict), defaultdict(list), defaultdict(dict)
    for name in sorted(SHA_PD):
        with (PD / name).open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                d = r["날"]
                if TO and d > TO:
                    continue
                c, v, px = r["코드"], float(r["시가총액(억)"]), float(r["종가"])
                if v <= 0 or px <= 0:
                    continue
                cap[d][c] = v
                vol[d][c] = float(r["거래량"])
                raw[d][c] = (px, float(r["대비"]) if r["대비"] != "" else None)
                if pop(c):
                    rank_rows[d].append((v, c))
    top = {d: [c for _, c in sorted(xs, key=lambda x: (-x[0], x[1]))[:TOP]] for d, xs in rank_rows.items()}
    last = max(cap)
    cal = [d for d in json.loads(CAL.read_text())["days"] if START <= d <= last]
    hole = [d for d in cal if d not in cap]
    if hole:
        sys.exit(f"NEEDS_DATA: 유효 거래일인데 자료가 통째로 없음 {hole}")
    extra = sorted(d for d in set(cap) - set(cal) if d >= START)
    if extra:
        sys.exit(f"NEEDS_DATA: 달력에 없는 날 자료 {extra}")
    no_vs, resume = 0, []
    for x, d in enumerate(cal):
        prev = cal[x - 1] if x else None
        for c, (px, vs) in raw[d].items():
            if vs is None or px - vs <= 0:
                no_vs += 1
                continue
            base = px - vs
            if prev and c in raw[prev] and vol[prev][c] == 0 and abs(base / raw[prev][c][0] - 1) > 1e-9:
                resume.append([d, c])
                continue
            g[d][c] = px / base
    return cap, vol, g, top, cal, no_vs, resume


def r5(g, cal, p, c):
    """p 앞 5거래일(p−4 ~ p) 수정 수익을 이은 값 − 1. 하루라도 없으면 None."""
    x = 1.0
    for k in range(p - LOOK + 1, p + 1):
        if c not in g[cal[k]]:
            return None
        x *= g[cal[k]][c]
    return x - 1


def cohorts(g, top, cal):
    """[(산 날 칸 i, 판 날 칸 j 또는 None, 고른 10종목, 대조 종목)]. 고르기는 p = i − 1까지 자료만 씀(t 자료로 바꾸지 않음)."""
    idx = list(range(LOOK + 1, len(cal), STEP))
    out = []
    for k, i in enumerate(idx):
        p = i - 1
        uni = top[cal[p]]
        sig = [(s, c) for c in uni if (s := r5(g, cal, p, c)) is not None]
        picks = [c for _, c in sorted(sig)][:PICK]
        j = idx[k + 1] if k + 1 < len(idx) else None
        out.append((i, j, picks, list(uni)))
    return out


def slots(cap, vol, g, cal, i, j, names, mode, c, last):
    """칸 i ~ end 날마다 각 몫의 값(산 날 몫 1 → 산 비용 뒤). 반환: (날 칸 목록, 몫마다 값 목록, 기록)."""
    k = side(c)
    end = j if j is not None else last
    t = cal[i]
    rows, info = [], {"unfilled": [], "gap": [], "sell_halt": []}
    for nm in names:
        if not (nm in cap[t] and vol[t][nm] > 0):
            info["unfilled"].append(nm)
            rows.append([0.0 if mode == "lo" else 1.0] * (end - i + 1))
            continue
        v, seq, dead = 1 - k, [1 - k], False
        for x in range(i + 1, end + 1):
            d = cal[x]
            if not dead and nm in g[d]:
                v *= g[d][nm]
            elif not dead:
                dead = True
                info["gap"].append([t, nm, d])
                if mode == "lo":
                    v = 0.0
            if x == j:
                if not dead and vol[d].get(nm, 0) == 0:
                    info["sell_halt"].append([t, nm, d])
                    if mode == "lo":
                        v = 0.0
                v *= 1 - k
            seq.append(v)
        rows.append(seq)
    return list(range(i, end + 1)), rows, info


def run(cap, vol, g, cal, cos, c, mode, which):
    """바구니를 이어서: 매매 [(산 날, 판 날, 순수익)] · NAV [(날, 값)](모든 유효 거래일 · 바꿔 담는 날 판 · 산 비용 그날 반영) · 기록."""
    last = len(cal) - 1
    trades, nav, V, logs = [], [], 1.0, []
    for i, j, picks, ctl in cos:
        names = picks if which == "pick" else ctl
        xs, rows, info = slots(cap, vol, g, cal, i, j, names, mode, c, last)
        n = len(rows)
        basket = [sum(r[s] for r in rows) / n for s in range(len(xs))] if n else [1.0] * len(xs)
        start = V
        if nav and nav[-1][0] == cal[i]:
            nav[-1] = (cal[i], start * basket[0])
        else:
            nav.append((cal[i], start * basket[0]))
        for s in range(1, len(xs)):
            nav.append((cal[xs[s]], start * basket[s]))
        V = start * basket[-1]
        if j is not None:
            trades.append((cal[i], cal[j], basket[-1] - 1))
        logs.append(info)
        if j is None:
            break
    return trades, nav, logs


def within(rows, lo, hi):
    return [r for r in rows if lo <= r[0] and r[1] <= hi]


def nav_period(cap, vol, g, cal, cos, c, mode, lo, hi):
    """그 기간 안에서 산 날 · 판 날이 모두 든 바구니만으로 현금 1에서 다시."""
    sub = [x for x in cos if x[1] is not None and lo <= cal[x[0]] and cal[x[1]] <= hi]
    return run(cap, vol, g, cal, sub, c, mode, "pick")[1]


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
    """달력 달 블록 부트스트랩(블록 3달): 같은 달 블록에서 고른 바구니 · 대조를 함께 다시 뽑음."""
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
    cap, vol, g, top, cal, no_vs, resume = load()
    cos = cohorts(g, top, cal)
    out = {"task": "STR-0030", "round": 2, "first": min(cap), "last": max(cap), "T_TO": TO or None, "cohorts": len(cos),
           "rows_without_vs": no_vs, "resume_adjusted": resume}
    for mode in ("lo", "hi"):
        tp, navp, logs = run(cap, vol, g, cal, cos, COST, mode, "pick")
        tps = run(cap, vol, g, cal, cos, STRESS, mode, "pick")[0]
        tc = run(cap, vol, g, cal, cos, COST, mode, "ctl")[0]
        out[mode] = {}
        for p, (lo, hi) in PERIODS.items():
            a, s, c = within(tp, lo, hi), within(tps, lo, hi), within(tc, lo, hi)
            if not a:
                continue
            ma, mc = sum(r[2] for r in a) / len(a), sum(r[2] for r in c) / len(c)
            out[mode][p] = {"pick": summary([r[2] for r in a]), "pick_stress": summary([r[2] for r in s]), "control": summary([r[2] for r in c]),
                            "diff_pct": round((ma - mc) * 100, 4), **boot(a, c),
                            "risk": risk(nav_period(cap, vol, g, cal, cos, COST, mode, lo, hi)),
                            "risk_stress": risk(nav_period(cap, vol, g, cal, cos, STRESS, mode, lo, hi))}
        out[mode]["trades"] = [[b, s_, round(x * 100, 6)] for b, s_, x in tp]
        out[mode]["navs_all"] = [[d, round(v, 12)] for d, v in navp]
        if mode == "lo":
            out["pick_unfilled"] = [[cal[i], nm] for (i, *_), lg in zip(cos, logs) for nm in lg["unfilled"]]
            out["pick_gaps"] = [x for lg in logs for x in lg["gap"]]
            out["pick_sell_halt"] = [x for lg in logs for x in lg["sell_halt"]]
    out["picks"] = [[cal[i], cal[j] if j is not None else None, p] for i, j, p, _ in cos]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
