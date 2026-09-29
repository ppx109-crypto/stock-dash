"""1시간봉 33회차(탐색 줄) — 어떤 종목이 '빨리' 버나: 시총 순위 · 시장(코스피/코스닥)별 매매 속도.
사용자 목표(빠른 회전 + 수익)를 위해, 지금 규칙 매매를 전 거래일 시총 순위(1~30 · 31~60 · 61~100 · 101~150)와 시장으로 나눠
건수 · 평균 손익 · 보유 봉 가운데 값 · 봉당 손익(= 속도)을 봄. 종목 모음 150위로 한 판도 같이(순위 101~150 매매를 보려고).
종목을 더 넓히면(300위) 빨리 버는 종목이 늘어날지 가늠하는 예비 조사."""
import sys, json, bisect
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
from pathlib import Path
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
SUF = json.loads(Path("hourly-data/suffix.json").read_text(encoding="utf-8"))
rdays = sorted(ranks)
def rank_at(c, stamp):
    d = H.prev_day(rdays, stamp)
    return ranks.get(d, {}).get(c) if d else None
def bucket(r):
    if r is None: return "모름"
    return "1~30" if r <= 30 else "31~60" if r <= 60 else "61~100" if r <= 100 else "101~150" if r <= 150 else "151~"
def report(tag, res):
    print(f"  {tag}: " + H.line(res), flush=True)
    for s in ("앞", "뒤"):
        L = [t for t in res[s]["목록"]]
        for key, fn in (("순위", lambda t: bucket(rank_at(t["code"], t["산 때"]))), ("시장", lambda t: "코스닥" if SUF.get(t["code"]) == "KQ" else "코스피")):
            g = {}
            for t in L: g.setdefault(fn(t), []).append(t)
            parts = []
            for k in sorted(g):
                T = g[k]; w = sum(t["칸"] for t in T)
                pnl = sum(t["손익"] * t["칸"] for t in T) / w
                bars = np.median([t["봉"] for t in T])
                speed = sum(t["손익"] * t["칸"] for t in T) / max(sum(max(t["봉"], 1) * t["칸"] for t in T), 1)
                parts.append(f"{k} {len(T)}건 {pnl:+.2f}% {bars:.0f}봉 봉당 {speed:+.3f}")
            print(f"      {s} {key}: " + " · ".join(parts), flush=True)
print("== 1시간봉 33회차 (어떤 종목이 빨리 버나) ==", flush=True)
report("지금(100위)", H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank))
U150 = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=150)
IN = {c: np.array([U150.ok(c, t) for t in data[c]["t"]]) for c in data}
report("150위", H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank))
print("끝", flush=True)
