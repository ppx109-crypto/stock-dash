"""1시간봉 15회차(탐색 줄) — '막 힘이 붙는 봉'에서 사기(사용자 목표 ① 오르기 직전에 산다 · 짧은 판의 기대 이익 키우기).
무엇을 = A그룹 꼴 + 가르침(전 거래일). 사는 때 = 그 재료가 켜진 날, 1시간봉이
- 돌파: 종가가 지난 N봉(7 = 하루 · 35 = 닷새) 가장 높은 고가를 넘음
- 거래량: 그 봉 거래량이 지난 20봉 평균의 X배(1.5 · 2 · 3) 넘음
둘을 함께 만족한 봉 다음 봉 시가(종목마다 하루 한 번). 먼저 사건 연구(7 · 14 · 35봉 앞날, 두 반)로 힘을 보고,
짧은 판(+5% · −5% · 21봉, 2칸)과 긴 판(일봉 규칙 파는 법)으로 계좌를 굴림. 미래 엿보기 · 무작위와도 견줌."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

def rolling_max_prev(a, n):
    out = np.full(len(a), np.nan)
    for k in range(n, len(a)):
        out[k] = a[k - n:k].max()
    return out
_RM = {}
def breakout(c, b, n):
    key = (c, n)
    if key not in _RM: _RM[key] = rolling_max_prev(b["h"], n)
    return b["c"] > _RM[key]
_RV = {}
def vol_mult(c, b):
    if c not in _RV:
        v = b["v"]; avg = np.full(len(v), np.nan)
        cs = np.r_[0.0, np.cumsum(v)]
        for k in range(20, len(v)):
            avg[k] = (cs[k] - cs[k - 20]) / 20
        _RV[c] = np.where(avg > 0, v / avg, np.nan)
    return _RV[c]
def once_a_day(b, m):
    days = [t[:8] for t in b["t"]]; seen = set(); out = np.zeros(len(m), bool)
    for k in np.flatnonzero(m):
        if days[k] not in seen:
            out[k] = True; seen.add(days[k])
    return out
def burst(n, x):
    def e(c, b):
        return once_a_day(b, ctx_now(c, b) & breakout(c, b, n) & (np.nan_to_num(vol_mult(c, b)) >= x))
    return e

K = (7, 14, 35)
print("== 1시간봉 15회차 (막 힘이 붙는 봉: 돌파 + 거래량) ==", flush=True)
print("-- 사건 연구(비용 뺀 k봉 앞날 %, 이긴 몫)", flush=True)
H.show("재료 날 아무 봉", H.study(data, lambda c, b: ctx_now(c, b), uni, K, edge=False), K)
H.show("재료 날 후보(정배열 · 12시)", H.study(data, e_align_or_noon, uni, K, edge=False), K)
for n in (7, 35):
    for x in (1.5, 2, 3):
        H.show(f"돌파 {n}봉 + 거래량 {x}배", H.study(data, burst(n, x), uni, K, edge=False), K)
print("-- 계좌(짧은 판 +5% · −5% · 21봉 · 2칸 / 긴 판)", flush=True)
short = lambda c, b, p, k: "all" if k - p["i"] >= 21 else 0
tp = lambda p: (p["price"] * 1.05, "all")
sl = lambda p: p["price"] * 0.95
for n, x in ((7, 2), (35, 2), (7, 3)):
    E = burst(n, x)
    res = H.simulate(data, E, short, lambda c, b, k: 2, rank=rank, take_of=tp, stop_of=sl)
    print(f"  {f'짧은 판 · 돌파 {n}봉 + 거래량 {x}배':30s} " + H.line(res), flush=True)
    res = H.simulate(data, E, exit_daily, size, rank=rank)
    print(f"  {f'긴 판 · 돌파 {n}봉 + 거래량 {x}배':30s} " + H.line(res), flush=True)
print("끝", flush=True)
