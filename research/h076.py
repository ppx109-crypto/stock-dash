"""1시간봉 76회차 — 사용자 질문 "1시간봉 진입 vs 일봉 진입, 어느 쪽이 연수익이 높나": 같은 기간 · 같은 종목 · 같은 파는 법(일봉 규칙) · 씨앗 16으로 나란히.
일봉 진입 = 일봉 신호가 켜진 날 다음 날 09시 시가에 삼(일봉 종가 매수와 가장 가까운 것) · 1시간봉 진입 = 1시간봉 A 정배열 된 봉 다음, 없으면 12시."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
def e_dil(c, b):
    m = np.asarray(e_align_or_noon(c, b), bool).copy(); n = len(b["t"])
    for k in np.flatnonzero(m):
        x = ATT[c][k + 1] if k + 1 < n else ATT[c][k]
        if x and x["희석20"]: m[k] = False
    return m
EX = make_exit()
print("== 1시간봉 76회차 (1시간봉 진입 vs 일봉 진입) ==", flush=True)
for tag, e, st in (("일봉 진입(다음 날 09시 시가)", e_morning, None), ("일봉 진입 + 자리 바꾸기", e_morning, stale90),
                   ("1시간봉 진입", e_align_or_noon, None), ("1시간봉 진입 + 자리 바꾸기(최고)", e_align_or_noon, stale90),
                   ("1시간봉 최고 + 희석 공시 거르기", e_dil, stale90)):
    res = H.simulate(data, e, EX, size, rank=rank, stale_of=st, seeds=16)
    print(f"  {tag:28s} " + H.line(res), flush=True)
print("끝", flush=True)
