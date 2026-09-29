"""1시간봉 36회차(확인 줄) — 자리 바꾸기 후보를 씨앗 32개로(앞 반 씨앗 폭이 ±20이라 8 · 16개로는 가르기 어려움).
견줌 · 7봉 <3% · 7봉 <4% · 10봉 <4% · 무작위 가드(7봉 · 확률 0.3)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
def stale(n, x):
    return lambda p: (p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x
def rand_stale(n, prob):
    rng = np.random.default_rng(7); memo = {}
    def f(p):
        key = (p["code"], p["i"], p["now"])
        if key not in memo: memo[key] = rng.random() < prob
        return (p["now"] - p["i"] >= n) and memo[key]
    return f
print("== 1시간봉 36회차 (씨앗 32) ==", flush=True)
for tag, st in (("지금", None), ("7봉 · <3%", stale(7, 3)), ("7봉 · <4%", stale(7, 4)), ("10봉 · <4%", stale(10, 4)), ("무작위 7봉 · 0.3", rand_stale(7, 0.3))):
    res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st, seeds=32)
    print(f"  {tag:16s} " + H.line(res), flush=True)
print("끝", flush=True)
