"""1시간봉 10회차(사용자 요청: 다트 · 한국투자증권 자료로 사는 조건) — 사는 순간에 붙이는 재료(모두 **전 거래일까지**, 공시는 접수 다음 날부터).
한국투자증권: 종목 프로그램 순매수 몫(20일) · 대차 잔고 변화(20일) · 매수 · 매도 체결 몫(20일) · 외국인 · 투신 · 연기금 · 사모 수급(5일)
DART: 희석(유상증자 · CB · BW · EB) 20일 · 자사주 20일 · 분기 실적 발표 뒤(5거래일 안)
각 재료를 '안 삼'(거르기)과 '4칸'(크게)으로 써 보고, 거르기는 막았을 매매의 손익을 함께 봄."""
import sys, json, os, bisect, collections
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

def cum(folder, cols):
    out = {}
    for c in data:
        p = f"{folder}/{c}.json"
        if not os.path.exists(p): continue
        rr = json.load(open(p))["rows"]
        days = [x["date"] for x in rr]
        acc = {k: np.r_[0.0, np.cumsum([(x.get(k) or 0.0) for x in rr])] for k in cols}
        out[c] = (days, acc, rr)
    return out
PG = cum("program-data", ("순매수대금",))
for c, (days, acc, rr) in PG.items():
    acc["대금"] = np.r_[0.0, np.cumsum([(x.get("거래량") or 0) * (x.get("종가") or 0) for x in rr])]
LN = cum("loan-data", ("잔고주수",))
SD = cum("side-data", ("매수체결량", "매도체결량"))

def day_of(b, k): return b["t"][k][:8]
def window(tab, c, day, n):
    g = tab.get(c)
    if not g: return None
    days, acc, rr = g
    j = bisect.bisect_left(days, day)        # 전 거래일까지(오늘 값 안 씀)
    if j - n < 0 or days[j - 1] < str(int(day[:4]) - 1) + day[4:]: return None
    return days, acc, rr, j
def prog20(c, b, k):
    w = window(PG, c, day_of(b, k), 20)
    if not w: return None
    _, acc, _, j = w
    v = acc["대금"][j] - acc["대금"][j - 20]
    return None if v <= 0 else (acc["순매수대금"][j] - acc["순매수대금"][j - 20]) / v * 100
def loan20(c, b, k):
    w = window(LN, c, day_of(b, k), 21)
    if not w: return None
    _, _, rr, j = w
    a, z = rr[j - 21].get("잔고주수") or 0, rr[j - 1].get("잔고주수") or 0
    return None if a <= 0 else (z / a - 1) * 100
def side20(c, b, k):
    w = window(SD, c, day_of(b, k), 20)
    if not w: return None
    _, acc, _, j = w
    bb = acc["매수체결량"][j] - acc["매수체결량"][j - 20]; ss = acc["매도체결량"][j] - acc["매도체결량"][j - 20]
    return None if bb + ss <= 0 else bb / (bb + ss) * 100
def ctx(c, b, k): return ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
def flow(c, b, k, col):
    x = ctx(c, b, k); return (x["수급5"].get(col) if x else None)
from datetime import date as _d
QD = {}
for c in data:
    p = f"quarter-data/{c}.json"
    if os.path.exists(p):
        rr = json.load(open(p)).get("rows") or {}
        QD[c] = sorted({str(v.get("접수번호", ""))[:8] for v in rr.values() if isinstance(v, dict) and v.get("접수번호")})
def earnings5(c, b, k):
    """분기 실적 공시 접수일이 신호 날보다 앞서고(다음 날부터 씀) 달력 7일 안."""
    ds = QD.get(c)
    if not ds: return False
    day = day_of(b, k); j = bisect.bisect_left(ds, day)
    if j == 0: return False
    a = ds[j - 1]
    return (_d(int(day[:4]), int(day[4:6]), int(day[6:])) - _d(int(a[:4]), int(a[4:6]), int(a[6:]))).days <= 7

TESTS = [
    ("프로그램 20일 몫 −2% 아래", lambda c, b, k: (lambda v: v is not None and v < -2)(prog20(c, b, k))),
    ("대차 20일 +20% 넘게 늘어남", lambda c, b, k: (lambda v: v is not None and v > 20)(loan20(c, b, k))),
    ("매수 체결 몫 20일 48% 아래", lambda c, b, k: (lambda v: v is not None and v < 48)(side20(c, b, k))),
    ("연기금 5일 순매도", lambda c, b, k: (lambda v: v is not None and v < 0)(flow(c, b, k, "연기금"))),
    ("사모 5일 순매도", lambda c, b, k: (lambda v: v is not None and v < 0)(flow(c, b, k, "사모"))),
    ("희석 공시 20일 안", lambda c, b, k: bool(ctx(c, b, k) and ctx(c, b, k)["희석20"])),
    ("분기 실적 발표 뒤 7일 안", earnings5),
]
BIG = [
    ("프로그램 20일 몫 +5% 넘음", lambda c, b, k: (lambda v: v is not None and v > 5)(prog20(c, b, k))),
    ("대차 20일 −15% 아래로 줄어듦", lambda c, b, k: (lambda v: v is not None and v < -15)(loan20(c, b, k))),
    ("자사주 공시 20일 안", lambda c, b, k: bool(ctx(c, b, k) and ctx(c, b, k)["자사주20"])),
    ("연기금 · 사모 5일 둘 다 순매수", lambda c, b, k: (flow(c, b, k, "연기금") or 0) > 0 and (flow(c, b, k, "사모") or 0) > 0),
]
E0 = e_align_or_noon
def filtered(bad):
    def e(c, b):
        m = E0(c, b).copy()
        for k in np.flatnonzero(m):
            if bad(c, b, k): m[k] = False
        return m
    return e

print(f"자료 있는 종목: 프로그램 {len(PG)} · 대차 {len(LN)} · 체결 {len(SD)} · 분기 실적 {len(QD)}", flush=True)
print("== 1시간봉 10회차 (다트 · 한국투자증권 재료로 사는 조건) ==", flush=True)
base = H.simulate(data, E0, exit_daily, size, rank=rank)
print(f"  {'기준':28s} " + H.line(base), flush=True)
for tag, bad in TESTS:
    res = H.simulate(data, filtered(bad), exit_daily, size, rank=rank)
    print(f"  {'안 삼: ' + tag:28s} " + H.line(res), flush=True)
    for side in ("앞", "뒤"):
        by = collections.defaultdict(lambda: [0, 0.0])
        for t in base[side]["목록"]:
            c = t["code"]; b = data[c]; k = b["t"].index(t["산 때"]) - 1
            if k >= 0 and bad(c, b, k):
                h = t["산 때"][:4] + ("상" if t["산 때"][4:6] <= "06" else "하")
                by[h][0] += 1; by[h][1] += t["손익"] * t["칸"] / 10
        print(f"      막았을 매매 {side}: {sum(v[0] for v in by.values())}건 · 계좌 몫 {sum(v[1] for v in by.values()):+.1f}% · "
              + ", ".join(f"{h} {v[0]}건 {v[1]:+.1f}" for h, v in sorted(by.items())), flush=True)
for tag, good in BIG:
    res = H.simulate(data, E0, exit_daily, lambda c, b, k, good=good: 4 if good(c, b, k) else size(c, b, k), rank=rank)
    print(f"  {'4칸: ' + tag:28s} " + H.line(res), flush=True)
print("끝", flush=True)
