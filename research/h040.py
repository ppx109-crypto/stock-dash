"""1시간봉 40회차(탐색 줄) — 종목 넓히기(사용자 "안되면 종목도 더 늘려서") 중간 점검: 전 거래일 시총 100 · 150 · 200 · 300위 모음.
새 180종목 가운데 수급이 들어온 것만 살 수 있음(수급 없으면 가르침이 거짓 → 안 삼) — 다 들어오면 다시 돌림.
규칙: 지금 규칙 · 자리 바꾸기(7봉 · <4%). 점검: 순위 칸별 매매 손익(1~100 · 101~150 · 151~200 · 201~300) · 반기 · 회전."""
import sys, json
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
from pathlib import Path
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
have = {p.stem for p in Path("investor-data").glob("*.json")}
added = json.loads(Path("hourly-data/universe.json").read_text(encoding="utf-8"))["top300_added"]
rdays = sorted(ranks)
def rank_at(c, stamp):
    d = H.prev_day(rdays, stamp)
    return ranks.get(d, {}).get(c) if d else None
def bucket(r):
    return "모름" if r is None else "1~100" if r <= 100 else "101~150" if r <= 150 else "151~200" if r <= 200 else "201~300" if r <= 300 else "301~"
stale = lambda p: (p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
print("== 1시간봉 40회차 (종목 넓히기 중간 점검) ==", flush=True)
print(f"  모의 종목 {len(data)} · 새 180종목 가운데 수급 있음 {sum(1 for c in added if c in have)} · 모의에 든 새 종목 {sum(1 for c in added if c in data)}", flush=True)
for top in (100, 150, 200, 300):
    U = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=top)
    IN = {c: np.array([U.ok(c, t) for t in data[c]["t"]]) for c in data}
    for tag, st in (("지금 규칙", None), ("자리 바꾸기", stale)):
        res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st)
        print(f"  {f'{top}위 · {tag}':18s} " + H.line(res), flush=True)
        parts = []
        for s in ("앞", "뒤"):
            g = {}
            for t in res[s]["목록"]:
                g.setdefault(bucket(rank_at(t["code"], t["산 때"])), []).append(t)
            parts.append(f"{s} " + " · ".join(f"{k} {len(v)}건 {sum(x['손익'] * x['칸'] for x in v) / sum(x['칸'] for x in v):+.2f}%" for k, v in sorted(g.items())))
        print(f"      {' | '.join(parts)}", flush=True)
        print(f"      반기(씨앗 0): 앞 {res['앞']['반기']} · 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
