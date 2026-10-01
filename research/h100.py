"""1시간봉 100회차 — 일봉 새 85회차와 짝(사용자 질문: ②정배열 매매에 기간 청산을 넣으면 나아지나).
최고 규칙(94회차)의 정배열 쪽에 기간 청산을 더함: N봉(60 · 120 · 180 · 240 = 약 10 · 20 · 30 · 40거래일)이 지나면 팖,
또는 N봉째 이익이 +3% 미만이면 팖. 씨앗 16 · 두 반.
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h094.py", encoding="utf-8").read().split('print("== 1시간봉 94회차')[0])
RK = rk_of(tiers(20, 5, 3))


def with_limit(bars, gain=None):
    def f(c, b, p, k):
        r = EX(c, b, p, k)
        if r:
            return r
        if (door(ATT[c][p["i"]]) or "정배열") == "정배열" and k - p["i"] >= bars:
            now = (b["c"][k] / p["price"] - 1) * 100
            if gain is None or now < gain:
                return "all"
        return 0
    return f


print("== 1시간봉 100회차: 정배열 매매에 기간 청산 더하기 (씨앗 16) ==", flush=True)
res = H.simulate(data, e_align_or_noon, EX, size, rank=RK, stale_of=stale90, seeds=16)
print(f"  {'기준(94회차, 기간 제한 없음)':28s} " + H.line(res), flush=True)
for n in (60, 120, 180, 240):
    res = H.simulate(data, e_align_or_noon, with_limit(n), size, rank=RK, stale_of=stale90, seeds=16)
    print(f"  {f'정배열 {n}봉(약 {n // 6}거래일) 청산':28s} " + H.line(res), flush=True)
for n in (60, 120, 180):
    res = H.simulate(data, e_align_or_noon, with_limit(n, 3), size, rank=RK, stale_of=stale90, seeds=16)
    print(f"  {f'정배열 {n}봉째 +3% 못 가면 청산':28s} " + H.line(res), flush=True)
print("끝", flush=True)
