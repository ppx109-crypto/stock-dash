"""1시간봉 다시 보기 2단계(docs/RL-1HY.md) — 1일봉(운영 규칙 · 조용함 문턱은 그때까지 자료로만 = DNA_past)도 같은 잣대로:
종목 풀(그날 시총 100위 안 후보)에서 종목 10%를 무작위로 빼고 N번 · lab.run 씨앗 0(i044와 같은 판) · 2023-01부터 굴림(앞 9달은 몸풀기).
D_N(기본 200) · D_DROP(0.1) → scratchpad d1luck.json(판마다 장부: 종목 · 산 날 · 판 날 · 손익 · 칸)."""
import json
import os
import random
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
os.chdir("/home/user/stock-dash")
os.environ.setdefault("I_VAR", "DNA_past")
os.environ["I_SX"] = ""
_src = open("/home/user/stock-dash/research/i044.py", encoding="utf-8").read()
exec(_src.split("# 미래 참조 자르기 · 더럽히기")[0])
N, DROP = int(os.environ.get("D_N", "200")), float(os.environ.get("D_DROP", "0.1"))
OUTL = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/d1luck.json"
SINCE = "20230101"
pool0 = [r for r in nrl.inside if r["date"] >= "20220601"]
codes = sorted({r["code"] for r in pool0})


def one(keep):
    ks = set(keep)
    g = lab.run([r for r in pool0 if r["code"] in ks], nrl.prices, HOLD, EXIT, rank=rule.order, slots=nrl.SLOTS, since=SINCE,
                apart=nrl.kin, realistic=True, cap=130, size=nrl.BASE_SIZE, detail=True)
    T = [(t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for t in (g or {}).get("매매목록", [])]
    T3 = [t for t in T if "20231001" <= t[1] < "20260901"]
    w = sorted((t[3] * t[4] / 10 for t in T3), reverse=True)
    return {"합": sum(w), "큰2뺌": sum(w[2:]), "매매": len(T3), "장부": T}


full = one(codes)
print(f"1일봉 온 풀({len(codes)}종목): 2023-10 ~ 2026-08 매매 {full['매매']} · 합 {full['합']:+.1f}%p · 큰 두 건 뺌 {full['큰2뺌']:+.1f}", flush=True)
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
print(f"1일봉 무작위 {N}판(2023-10 ~ 2026-08): 합 가운데 {np.median(a):+.1f} · 아래 10% {np.percentile(a, 10):+.1f} · 위 10% {np.percentile(a, 90):+.1f} | 큰 두 건 뺌 가운데 {np.median(b):+.1f} · 아래 10% {np.percentile(b, 10):+.1f}", flush=True)
