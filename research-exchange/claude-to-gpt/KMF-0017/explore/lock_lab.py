"""2차: 이익 잠금 촘촘히(L 30 ~ 60 · G 10 ~ 30) × 쉬는 동안 시간대 봇(KMF-0015) 끼우기 켬/끔 · 하루 멈춤 −25 그대로."""
import sys, json, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import guard_lab as G
import kmf15 as M15
W = G.M16.intent(G.b, M15.signals(G.b, M15.grid()[0]))
R0 = list(G.R)
res = {}
for use_w in (0, 1):
    G.R = [r if r else (W[i] if use_w else 0) for i, r in enumerate(R0)]
    for L, Gv in itertools.product((30, 40, 50, 60), (10, 15, 20, 25, 30)):
        if Gv >= L:
            continue
        r = G.score(*G.run(-25.0, 0, (L, Gv), 0))
        res[f"W{use_w}_L{L}-{Gv}"] = r
    r = G.score(*G.run(-25.0, 0, (0, 0), 0)); res[f"W{use_w}_none"] = r
G.R = R0
json.dump(res, open(Path(__file__).parent / "lock_lab.json", "w"), ensure_ascii=False)
print("칸: 합 / 177일 / 자기 위10 뺀 합 / +달 / 가장 나쁜 달")
for w in (0, 1):
    print(f"시간대 봇 {'끼움' if w else '안 끼움'}  없음:", {k: res[f'W{w}_none'][k] for k in ('total', 'rest177', 'ex10')})
    for L in (30, 40, 50, 60):
        print(f"  L{L}", "  ".join(f"G{g}:{res[f'W{w}_L{L}-{g}']['total']:+.0f}/{res[f'W{w}_L{L}-{g}']['rest177']:+.0f}/{res[f'W{w}_L{L}-{g}']['ex10']:+.0f}/{res[f'W{w}_L{L}-{g}']['pos_m']}/{res[f'W{w}_L{L}-{g}']['worst_m']:+.0f}" for g in (10, 15, 20, 25, 30) if f'W{w}_L{L}-{g}' in res))
