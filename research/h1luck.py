"""1시간봉 다시 보기 2단계(docs/RL-1HY.md) — 운을 걷어낸 실력: 종목 풀에서 10%를 무작위로 빼고 N번 돌려 성적 분포.
H1_SRC(research/h1src.py와 같음 · 기본 yahoo) · H1_ALL=1(한투 종목 모두) · H1_LO / H1_HI(YYYYMMDDHH) · H1_N(기본 200) · H1_DROP(기본 0.1).
같은 규칙(94회차 = 운영) · 같은 엔진 · 규칙 숫자는 안 바꿈. 자료 · 신호는 한 번만 만들고 풀만 바꿔 다시 굴림(신호는 그 종목 자료만 보므로 풀을 빼도 그대로).
출력: 판마다 칸 반영 합 · 큰 두 건 뺀 합 · 매매 수 · 장부(종목 · 산 날 · 판 날 · 손익 · 칸) → scratchpad h1luck_{이름}.json · 요약 한 줄."""
import json
import os
import random
import sys

os.environ.setdefault("H1_SRC", "yahoo")
LO, HI = os.environ.get("H1_LO", "2023100100"), os.environ.get("H1_HI", "2026090100")
N, DROP = int(os.environ.get("H1_N", "200")), float(os.environ.get("H1_DROP", "0.1"))
src = open("/home/user/stock-dash/research/h1src.py", encoding="utf-8").read()
exec(src.split("r = H._one_run(")[0])
LO, HI = os.environ.get("H1_LO", "2023100100"), os.environ.get("H1_HI", "2026090100")   # h1src가 덮어쓴 기간을 되돌림(2026-10-04 고침)
name = f"{os.environ['H1_SRC']}{'_all' if os.environ.get('H1_ALL') == '1' else ''}_{LO[:6]}_{HI[:6]}"
OUTL = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/h1luck_" + name + ".json"
codes = sorted(data)
rk = rk_of(tiers(20, 5, 3))
res = []


def one(keep):
    d = {c: data[c] for c in keep}
    s = {c: sigs[c] for c in keep}
    r = H._one_run(d, s, EX, size, LO, HI, 10, 0, None, rk, H.COST, None, None, stale90)
    T = [(t["code"], t["산 때"][:8], t["판 때"].lstrip("끝")[:8], t["손익"], t["칸"]) for t in r["목록"]]
    w = sorted((t[3] * t[4] / 10 for t in T), reverse=True)
    return {"합": sum(w), "큰2뺌": sum(w[2:]), "매매": len(T), "장부": T}       # 장부 = 3단계 조합(a_mtm 날마다 평가)에 씀


full = one(codes)
print(f"{name} 온 풀: 매매 {full['매매']} · 합 {full['합']:+.1f}%p · 큰 두 건 뺌 {full['큰2뺌']:+.1f}", flush=True)
rng = random.Random(11)
for i in range(N):
    keep = [c for c in codes if rng.random() >= DROP]
    res.append(one(keep))
    if (i + 1) % 20 == 0:
        json.dump({"온 풀": full, "판": res}, open(OUTL, "w"))
        print(f"  {i + 1}판", flush=True)
import numpy as np
a = np.array([r["합"] for r in res]); b = np.array([r["큰2뺌"] for r in res])
json.dump({"온 풀": full, "판": res}, open(OUTL, "w"))
print(f"{name} 무작위 {N}판: 합 가운데 {np.median(a):+.1f} · 아래 10% {np.percentile(a, 10):+.1f} · 위 10% {np.percentile(a, 90):+.1f} | 큰 두 건 뺌 가운데 {np.median(b):+.1f} · 아래 10% {np.percentile(b, 10):+.1f}", flush=True)
