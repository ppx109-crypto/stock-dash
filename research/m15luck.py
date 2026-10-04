"""1시간봉 다시 보기 2단계(docs/RL-1HY.md) — 15분봉 22회차(운영 규칙)도 같은 잣대로: 종목 풀 10%를 무작위로 빼고 N번.
자료 · 신호는 q027(22회차 후보 · 시장 흐름은 그 봉 100위 안 종목만)에서 한 번 만들고 풀만 바꿈 · 씨앗 1 · 두 반(앞 · 뒤) 매매를 이어 붙임.
M_N(기본 200) · M_DROP(0.1) → scratchpad m15luck.json(판마다 합 · 큰2뺌 · 매매 · 장부)."""
import json
import os
import random
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
os.chdir("/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
N, DROP = int(os.environ.get("M_N", "200")), float(os.environ.get("M_DROP", "0.1"))
OUTL = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/m15luck.json"
codes = sorted(data)


def one(keep):
    d = {c: data[c] for c in keep}
    res = M.simulate(d, lambda c, b: SGF[c], exit_rule, size, rank=RKF, stale_of=stale90, seeds=1, cost=H.COST)
    T = [(t["code"], t["산 때"][:8], t["판 때"].lstrip("끝")[:8], t["손익"], t["칸"]) for s in ("앞", "뒤") if res.get(s) for t in res[s]["목록"]]
    w = sorted((t[3] * t[4] / 10 for t in T), reverse=True)
    return {"합": sum(w), "큰2뺌": sum(w[2:]), "매매": len(T), "장부": T}


full = one(codes)
print(f"15분봉 온 풀({len(codes)}종목): 매매 {full['매매']} · 합 {full['합']:+.1f}%p · 큰 두 건 뺌 {full['큰2뺌']:+.1f}", flush=True)
rng = random.Random(11)
res = []
for i in range(N):
    res.append(one([c for c in codes if rng.random() >= DROP]))
    if (i + 1) % 20 == 0:
        json.dump({"온 풀": full, "판": res}, open(OUTL, "w"))
        print(f"  {i + 1}판", flush=True)
import numpy as np
a = np.array([r["합"] for r in res]); b = np.array([r["큰2뺌"] for r in res])
json.dump({"온 풀": full, "판": res}, open(OUTL, "w"))
print(f"15분봉 무작위 {N}판: 합 가운데 {np.median(a):+.1f} · 아래 10% {np.percentile(a, 10):+.1f} · 위 10% {np.percentile(a, 90):+.1f} | 큰 두 건 뺌 가운데 {np.median(b):+.1f} · 아래 10% {np.percentile(b, 10):+.1f}", flush=True)
