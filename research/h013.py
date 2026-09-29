"""1시간봉 13회차 — 사용자 목표 전환(2026-09-30): '일봉보다 짧게 들고 자주 돌려 수익률을 올림'.
짧은 판: 무엇을 = A그룹 꼴 + 가르침(전 거래일) · 사는 때 = 1시간봉 A 정배열 된 봉 다음, 없으면 12시(종목마다 하루 한 번)
파는 법 = **장중 지정가 익절**(봉 고가가 닿으면 그 값, 시가가 이미 위면 시가) · **장중 손절**(봉 저가) · **시간 제한**(봉 종가 뒤 다음 봉 시가)
같은 봉에서 익절 · 손절 둘 다 닿으면 손절이 먼저. 칸은 모두 2칸(20%)으로 여러 종목을 빨리 돌림.
견줌: 지금 1시간봉 규칙(일봉 파는 법, 길게 듦). 회전 = 한 해 산 금액 ÷ 자금."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

E = e_align_or_noon
def short_exit(bars):
    def go(c, b, p, k):
        return "all" if k - p["i"] >= bars else 0
    return go
def take(pct):
    return lambda p: (p["price"] * (1 + pct / 100), "all")
def stop(pct):
    return lambda p: p["price"] * (1 - pct / 100)
two = lambda c, b, k: 2

print("== 1시간봉 13회차 (짧은 판: 지정가 익절 · 장중 손절 · 시간) ==", flush=True)
res = H.simulate(data, E, exit_daily, size, rank=rank)
print(f"  {'견줌: 지금 규칙(길게 듦)':30s} " + H.line(res), flush=True)
for bars in (7, 21):
    for tp in (3, 5, 8):
        for sl in (2, 3, 5):
            res = H.simulate(data, E, short_exit(bars), two, rank=rank, take_of=take(tp), stop_of=stop(sl))
            print(f"  {f'+{tp}% 익절 · −{sl}% 손절 · {bars}봉':30s} " + H.line(res), flush=True)
print("끝", flush=True)
