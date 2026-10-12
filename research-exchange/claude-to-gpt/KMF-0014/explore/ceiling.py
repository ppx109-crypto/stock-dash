"""하늘 끝(미래를 안다는 가정 · 판정 밖): KMF-0013 위 10일을 뺀 177일에서
 ① 그날 방향을 미리 알고 09:05 시가 → 장 끝 한 번 들기 ② 한 시간 덩어리마다 방향을 알고 들기(6번) · 비용 포함."""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import short_lab as S
sys.path.insert(0, str(S.ROOT / "research"))
import kmf13 as M13
rows, b, B = S.load()
d13, _ = S.K.simulate(b, M13.signals(b, M13.grid()[0]))
top = set(sorted(d13, key=lambda d: -d13[d])[:10])
byd = defaultdict(list)
for r in b:
    byd[r[0]].append(r)
one = hour = 0.0; n = 0
for d, v in byd.items():
    if d in top:
        continue
    n += 1
    o = next(r[2] for r in v if r[1] >= 549); cl = v[-1][5]
    one += abs(cl - o) - 0.08
    for h0 in range(545, 930, 60):
        seg = [r for r in v if h0 <= r[1] < h0 + 60]
        if len(seg) >= 2:
            hour += abs(seg[-1][5] - seg[0][2]) - 0.08
print(f"날 {n} · ① 하루 한 번 방향 앎 {one:+.0f}p(하루 {one/n:+.1f}) · ② 한 시간마다 방향 앎 {hour:+.0f}p(하루 {hour/n:+.1f})")
print(f"KMF-0013 위 10일 합 {sum(d13[d] for d in top):+.1f} · 나머지 {sum(v for d,v in d13.items() if d not in top):+.1f}")
