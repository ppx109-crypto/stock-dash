"""1시간봉 97회차 — 2025 ~ 2026 하락장에서 최고 규칙(90 · 94회차)이 하락을 피했나(사용자 2026-10-01 질문).

1) 코스피에서 7% 넘는 하락 구간(꼭대기 → 바닥)을 찾음
2) 하락 시작 전 시장 전체(코스피) 외국인 · 기관 순매수(한투 시장 투자자 자료)가 평소보다 팔았나
3) 같은 구간에 최고 규칙(씨앗 16)이 얼마나 들고 있었고(가동), 계좌가 얼마나 움직였고, 새로 몇 번 샀나
"""
import json
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h094.py", encoding="utf-8").read().split('print("== 1시간봉 94회차')[0])
RK = rk_of(tiers(20, 5, 3))

K = [r for r in json.load(open("market-data/index_KOSPI.json", encoding="utf-8"))["rows"] if r["date"] >= "20230901"]
KD = [r["date"] for r in K]
KC = {r["date"]: r["종가"] for r in K}
INV = {r["date"]: r for r in json.load(open("market-data/investor_KSP.json", encoding="utf-8"))["rows"]}
IDAYS = sorted(d for d in INV if d >= "20230901")

drops, peak, pk, cur = [], None, None, None
for d in KD:
    c = KC[d]
    if peak is None or c > peak:
        if cur and cur[2] <= -7:
            drops.append(cur)
        peak, pk, cur = c, d, None
    dd = (c / peak - 1) * 100
    if cur is None or dd < cur[2]:
        cur = (pk, d, round(dd, 1))
if cur and cur[2] <= -7:
    drops.append(cur)


def flow_sum(day, n, col, before=True):
    k = IDAYS.index(day) if day in IDAYS else None
    if k is None:
        return None
    lo, hi = (k - n, k) if before else (k, k + n)
    return sum((INV[d].get(col) or 0) for d in IDAYS[max(0, lo):hi])


typ = {col: np.median([flow_sum(d, 10, col) for d in IDAYS[20:] if flow_sum(d, 10, col) is not None]) for col in ("외국인", "기관")}
print("== 1시간봉 97회차: 하락장 피했나 ==", flush=True)
print(f"(시장 투자자 10일 합의 평소 가운데: 외국인 {typ['외국인']:,.0f} · 기관 {typ['기관']:,.0f} — 자료 단위 그대로)", flush=True)
for p, t, depth in drops:
    f10, i10 = flow_sum(p, 10, "외국인"), flow_sum(p, 10, "기관")
    f5, i5 = flow_sum(p, 5, "외국인"), flow_sum(p, 5, "기관")
    fd, idd = flow_sum(p, max(1, IDAYS.index(t) - IDAYS.index(p)) if t in IDAYS and p in IDAYS else 1, "외국인", False), \
        flow_sum(p, max(1, IDAYS.index(t) - IDAYS.index(p)) if t in IDAYS and p in IDAYS else 1, "기관", False)
    print(f"  하락 {p} → {t} 코스피 {depth}% · 꼭대기 전 5일 외국인 {f5:,.0f} · 기관 {i5:,.0f} / 10일 외국인 {f10:,.0f} · 기관 {i10:,.0f}"
          f" · 하락 동안 외국인 {fd:,.0f} · 기관 {idd:,.0f}", flush=True)

runs = {}
for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
    runs[s] = [H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, RK, H.COST, None, None, stale90) for seed in range(16)]


def window(r, p, t):
    cv = r["곡선"]
    days = sorted(cv)
    a = max((d for d in days if d <= p), default=None)
    b = max((d for d in days if d <= t), default=None)
    if not a or not b:
        return None
    acct = (cv[b] / cv[a] - 1) * 100
    seg = [cv[d] for d in days if a <= d <= b]
    dd = (min(seg) / cv[a] - 1) * 100
    span = [d for d in days if a <= d <= b]
    held = []
    for d in span:
        held.append(sum(x["칸"] for x in r["목록"] if x["산 때"][:8] <= d < x["판 때"].replace("끝", "")[:8]) / 10 * 100)
    pre = [d for d in days if d < a][-10:]
    held_pre = np.mean([sum(x["칸"] for x in r["목록"] if x["산 때"][:8] <= d < x["판 때"].replace("끝", "")[:8]) / 10 * 100 for d in pre]) if pre else None
    buys = len({(x["code"], x["산 때"]) for x in r["목록"] if a <= x["산 때"][:8] <= b})
    return acct, dd, float(np.mean(held)), held_pre, buys


print("\n  최고 규칙(씨앗 16 가운데): 하락 구간 계좌 움직임 · 그 사이 가장 깊은 곳 · 평균 가동 · 꼭대기 전 10일 가동 · 새로 산 수", flush=True)
for p, t, depth in drops:
    side = "앞" if p < H.LATE[0] else "뒤"
    got = [window(r, p, t) for r in runs[side] if r]
    got = [g for g in got if g]
    if not got:
        print(f"  {p} → {t}: 시험 기간 밖", flush=True)
        continue
    m = lambda i: round(float(np.median([g[i] for g in got if g[i] is not None])), 1)
    print(f"  {p} → {t} (코스피 {depth}%): 계좌 {m(0):+}% · 가장 깊은 곳 {m(1):+}% · 가동 {m(2)}% (꼭대기 전 10일 {m(3)}%) · 새로 산 {m(4)}번", flush=True)
print("끝", flush=True)
