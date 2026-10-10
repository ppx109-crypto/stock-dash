"""TOM-0028(NEW-BOT-0027 C2) — 월말 · 월초: 달력의 그 달 마지막 거래일 종가에 KODEX 200(069500)을 사서 다음 달 셋째 거래일 종가에 팖.
사전등록: research-exchange/claude-to-gpt/TOM-0028/PREREG.md(round 3 · GPT #160 6091400672 · 6091438066 반영).
- 달력은 research/t001_cal.py가 가격 파일 없이 규칙(공휴일 패키지 0.57 · 근로자의 날 · 연말 마지막 평일 · 공지 휴장)으로 만든 파일.
- 자료 · 달력은 저장소 상대 경로 · 전체 sha256이 다르면 멈춤. 신호는 달력 파일만 봄(가격 줄로 월말을 정하지 않음).
- 비용: 왕복 C를 편도 c = 1 − √(1 − C)로 나눠 산 날 · 판 날에 각각 뺌(거래 수익 · NAV · 스트레스 같은 규칙).
- 기간(A · B · C)마다 산 날 · 판 날이 모두 그 안인 매매만 쓰고, NAV도 그 매매로 현금 1에서 새로 셈. 대조도 같은 경계.
- 신뢰구간: 달력 달 블록 부트스트랩(블록 6달 · 10,000번 · 씨앗 20261010) — 같은 달 블록에서 TOM과 대조를 함께 다시 뽑음.
- 가격 수익만(분배금 미포함 · 근거 미확인) · 과거 휴장 목록이 시점별 공지가 아님 → 판정 이름은 탐색적 가격 패턴 후보(EXPLORATORY_CANDIDATE).
python3 research/t001.py            (T_TO=YYYYMMDD면 그날까지 가격만 읽음 — 자르기 시험 · 달력은 그대로)"""
import hashlib
import json
import math
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "etf-data" / "069500.json"
CAL = ROOT / "research-exchange" / "claude-to-gpt" / "TOM-0028" / "calendar.json"
SHA = {SRC: "362d358c8cc53145c6d73539a9639eb6891420247144ae54e33097ba72119db6",
       CAL: "533806486ea09430e12fc0a67549d8f5a54b20be014b24457ec675a3e9cd7939"}
TO = os.getenv("T_TO", "")
COST, STRESS = 0.0010, 0.0030
PERIODS = {"A": ("20021014", "20121231"), "B": ("20130101", "20191231"), "C": ("20200101", "20260930"), "ALL": ("20021014", "20260930")}
HOLD = 3
BLOCK, REPS, SEED = 6, 10000, 20261010


def side(c):
    return 1 - math.sqrt(1 - c)


def check():
    for p, h in SHA.items():
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != h:
            sys.exit(f"자료 해시가 다름: {p.name} {got}")


def load():
    px = {str(d): float(c) for d, c in json.loads(SRC.read_text())["closes"] if c}
    if TO:
        px = {d: c for d, c in px.items() if d <= TO}
    cal = json.loads(CAL.read_text())["days"]
    return px, cal


def plan(cal):
    """달력만으로 (산 날, 판 날): 산 날 = 그 달 마지막 거래일, 판 날 = 그 뒤 3번째 거래일(다음 달 셋째 거래일이어야 함)."""
    out = []
    for i, d in enumerate(cal):
        if i + 1 < len(cal) and cal[i + 1][:6] != d[:6] and i + HOLD < len(cal):
            assert cal[i + HOLD][:6] == cal[i + 1][:6], ("셋째 거래일이 다음 달이 아님", d)
            out.append((d, cal[i + HOLD]))
    return out


def trade_ret(px, b, s, c):
    k = side(c)
    return px[s] / px[b] * (1 - k) * (1 - k) - 1


def tom(px, cal, c):
    return [(b, s, trade_ret(px, b, s, c)) for b, s in plan(cal) if b in px and s in px]


def control(px, cal, c, skip):
    """같은 보유 길이 대조: 달 마지막 거래일이 아닌 모든 거래일 종가에 사서 3거래일 뒤 종가에 판 순수익(산 날 · 판 날 함께)."""
    out = []
    for i in range(len(cal) - HOLD):
        b, s = cal[i], cal[i + HOLD]
        if b not in skip and b in px and s in px:
            out.append((b, s, trade_ret(px, b, s, c)))
    return out


def within(rows, lo, hi):
    return [r for r in rows if lo <= r[0] and r[1] <= hi]


def nav(px, cal, ts, lo, hi, c):
    """기간 안 매매만으로 현금 1에서 시작 · 들고 있는 날 100% · 산 날 · 판 날에 편도 비용 · 날마다 종가 평가(자르기 끝의 열린 자리도 그날 종가로)."""
    k = side(c)
    buy = {b: s for b, s, _ in ts}
    days = [d for d in cal if lo <= d <= hi and d in px]
    v, out, sell, prev = 1.0, [], None, None
    for d in days:
        if sell is not None:
            v *= px[d] / prev
            if d == sell:
                v *= 1 - k
                sell = None
        if sell is None and d in buy:
            v *= 1 - k
            sell = buy[d]
        out.append((d, v))
        prev = px[d]
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
    """달력 달 블록 부트스트랩: 달(산 날의 YYYYMM)을 6달 묶음으로 이어 뽑아, 그 달들에 산 TOM · 대조를 함께 모아 평균 · 차이를 셈."""
    months = sorted({r[0][:6] for r in t} | {r[0][:6] for r in ctl})
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
    return {"tom_mean_ci95_pct": [round(q(mt, .025) * 100, 4), round(q(mt, .975) * 100, 4)],
            "diff_ci95_pct": [round(q(df, .025) * 100, 4), round(q(df, .975) * 100, 4)]}


def main():
    check()
    px, cal = load()
    out = {"task": "TOM-0028", "round": 2, "price_first": min(px), "price_last": max(px), "T_TO": TO or None,
           "sha256": {p.name: h for p, h in SHA.items()}}
    t_all, ts_all = tom(px, cal, COST), tom(px, cal, STRESS)
    c_all = control(px, cal, COST, {b for b, _ in plan(cal)})
    for p, (lo, hi) in PERIODS.items():
        t, ts, c = within(t_all, lo, hi), within(ts_all, lo, hi), within(c_all, lo, hi)
        if not t:
            continue
        mt, mc = sum(r[2] for r in t) / len(t), sum(r[2] for r in c) / len(c)
        out[p] = {"tom": summary([r[2] for r in t]), "tom_stress": summary([r[2] for r in ts]), "control": summary([r[2] for r in c]),
                  "diff_pct": round((mt - mc) * 100, 4), **boot(t, c),
                  "risk": risk(nav(px, cal, t, lo, hi, COST)), "risk_stress": risk(nav(px, cal, ts, lo, hi, STRESS))}
    out["trades"] = [[b, s, round(x * 100, 6)] for b, s, x in t_all]
    last = max(px)
    out["plan_without_price"] = [[b, s] for b, s in plan(cal) if s <= last and (b not in px or s not in px)]
    out["calendar_days_without_price"] = sorted(d for d in cal if d <= last and d not in px)
    lo, hi = PERIODS["ALL"]
    # 자르기 비교용 전체 NAV: 달력 계획 가운데 산 날 값이 있는 것 모두(판 날 값이 아직 없으면 열린 자리로 그날 종가 평가)
    out["navs_all"] = [[d, round(v, 12)] for d, v in nav(px, cal, [(b, s, None) for b, s in plan(cal) if b in px], lo, max(px), COST)]
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
