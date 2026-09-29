"""1시간봉 34회차(확인 줄) — 자리 바꾸기 후보(7봉 · +4% 못 간 매매를 새 신호에 비킴) 점검.
① 비용 민감도(회전이 2배라 비용이 더 아픔): 0.30 · 0.40 · 0.50% ② 반기(씨앗 0) ③ 비킨 매매(안 비켰으면 어땠나) vs 그 자리에 새로 산 매매
④ 무작위 가드: 비킬 매매를 '묵음'이 아니라 무작위로 고르면(같은 수준으로 자리 비우기) — 이득이 '묵은 것을 고른 데서' 오는지
⑤ 이웃 한 칸(7봉 · +3/+5 · 10봉 · +4) 비용 0.40%에서도 버티나."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
def stale(n, x):
    return lambda p: (p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x
def rand_stale(n, prob, seed=0):
    rng = np.random.default_rng(seed); memo = {}
    def f(p):
        key = (p["code"], p["i"], p["now"])
        if key not in memo: memo[key] = rng.random() < prob
        return (p["now"] - p["i"] >= n) and memo[key]
    return f
print("== 1시간봉 34회차 (자리 바꾸기 7봉 · +4% 점검) ==", flush=True)
for cost in (0.30, 0.40, 0.50):
    b = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, cost=cost)
    r = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, cost=cost, stale_of=stale(7, 4))
    print(f"  비용 {cost:.2f}% 지금          " + H.line(b), flush=True)
    print(f"  비용 {cost:.2f}% 7봉 · <4%     " + H.line(r), flush=True)
    if cost == 0.30:
        base, res = b, r
for s in ("앞", "뒤"):
    print(f"  {s} 반기(씨앗 0): 지금 {base[s]['반기']} → 바꾸기 {res[s]['반기']}", flush=True)
    kb = {(t["code"], t["산 때"]): t for t in base[s]["목록"] if not t["나눠"]}
    kr = {(t["code"], t["산 때"]) for t in res[s]["목록"]}
    moved = [t for t in res[s]["목록"] if t["비킴"]]
    was = [kb[(t["code"], t["산 때"])]["손익"] for t in moved if (t["code"], t["산 때"]) in kb]
    newt = [t for t in res[s]["목록"] if (t["code"], t["산 때"]) not in kb and not t["나눠"]]
    print(f"  {s} 비킨 {len(moved)}건 평균 {np.mean([t['손익'] for t in moved]):+.2f}% (안 비켰으면 {np.mean(was):+.2f}% · {len(was)}건 대조)"
          f" · 지금엔 없던 새 매매 {len(newt)}건 평균 {np.mean([t['손익'] for t in newt]):+.2f}% · 보유 {np.median([t['봉'] for t in newt]):.0f}봉", flush=True)
for prob in (0.3, 0.5):
    r = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=rand_stale(7, prob))
    print(f"  무작위 가드 7봉 · 확률 {prob}  " + H.line(r), flush=True)
for n, x in ((7, 3), (7, 5), (10, 4)):
    r = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, cost=0.40, stale_of=stale(n, x))
    print(f"  비용 0.40% {n}봉 · <{x}%     " + H.line(r), flush=True)
print("끝", flush=True)
