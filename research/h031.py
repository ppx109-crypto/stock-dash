"""1시간봉 31회차(확인 줄) — 29회차 '7봉 · +3% 못 간 매매는 새 신호에 비킴'이 고원인지(이웃 문턱) · 씨앗 16개로.
29회차: 앞 21.7 → 27.2(골 −15.7) · 뒤 107.97 → 97.53 · 회전 16.6 → 26~29배 · 보유 39 → 12~16봉. 14 · 21봉은 나빠짐.
문턱: 봉 N = 4 · 5 · 7 · 10 · 손익 X = +2 · +3 · +4 · +5%. 씨앗을 16개로 늘려 가운데 값 흔들림을 줄임."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
def stale(n, x):
    return lambda p: (p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x
print("== 1시간봉 31회차 (자리 바꾸기 문턱 고원 · 씨앗 16) ==", flush=True)
print(f"  {'지금':16s} " + H.line(H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, seeds=16)), flush=True)
for n in (4, 5, 7, 10):
    for x in (2, 3, 4, 5):
        res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=stale(n, x), seeds=16)
        print(f"  {f'{n}봉 · <{x}%':16s} " + H.line(res), flush=True)
print("끝", flush=True)
