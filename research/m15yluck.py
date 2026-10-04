"""최종 판단(docs/RL-1HY.md 17회차~) — 15분봇 규칙을 1시간봉으로 옮긴 판(research/m15y.py)도 종목 풀 10%를 무작위로 빼고 N번(기본 200 · 씨앗 1).
M15Y_SRC=yahoo(2023-10 ~ 2026-08). → scratchpad m15yluck_{SRC}.json(판마다 합 · 큰2뺌 · 매매 · 장부)."""
import json
import os
import random
src = open("/home/user/stock-dash/research/m15y.py", encoding="utf-8").read()
exec(src.split("res16 = M.simulate(")[0])
N, DROP = int(os.environ.get("M_N", "200")), float(os.environ.get("M_DROP", "0.1"))
OUTL = f"/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/m15yluck_{SRC}.json"
codes = sorted(data)


def one(keep):
    d = {c: data[c] for c in keep}
    res = M.simulate(d, lambda c, b: SGF[c], exit_rule, size, rank=RKF, stale_of=stale90, seeds=1, cost=H.COST)
    T = [(t["code"], t["산 때"][:8], t["판 때"].lstrip("끝")[:8], t["손익"], t["칸"]) for s in res if res[s] for t in res[s]["목록"]]
    w = sorted((t[3] * t[4] / 10 for t in T), reverse=True)
    return {"합": sum(w), "큰2뺌": sum(w[2:]), "매매": len(T), "장부": T}


full = one(codes)
print(f"15분봇→1시간봉 {SRC} 온 풀: 매매 {full['매매']} · 합 {full['합']:+.1f}%p", flush=True)
rng = random.Random(11)
out = []
for i in range(N):
    out.append(one([c for c in codes if rng.random() >= DROP]))
    if (i + 1) % 20 == 0:
        json.dump({"온 풀": full, "판": out}, open(OUTL, "w"))
        print(f"  {i + 1}판", flush=True)
json.dump({"온 풀": full, "판": out}, open(OUTL, "w"))
import numpy as np
a = np.array([r["합"] for r in out])
print(f"무작위 {N}판: 합 가운데 {np.median(a):+.1f} · 아래 10% {np.percentile(a, 10):+.1f}", flush=True)
