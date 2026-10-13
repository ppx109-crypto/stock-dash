"""진단 2 · 3(전체 자료 · 판정 밖):
② 시간대: 한 시간 덩어리마다 '앞 30분 방향 → 뒤 30분 같은 방향' 이어지는 정도(평균 · p)
③ 수급(장 끝난 뒤 자료 → 다음 거래일에만): 전날 코스피 외국인 순매수 · 프로그램 전체 순매수(앞 20일 대비 z)의 부호와
   그날 미니 선물 09:05 시가 → 15:30 종가 · 09:05 → 11:00 움직임의 관계."""
import sys, json
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K
rows = K._rows_before("20261013")
byd = defaultdict(dict)
for r in rows:
    byd[r[0]][r[1]] = r
days = sorted(byd)
print("② 시간대(앞 30분 움직임 부호 × 뒤 30분 움직임 · p · 앞 반 / 뒤 반)")
for h0 in range(545, 900, 30):
    xs = []
    for d in days:
        t = byd[d]
        if all(m in t for m in (h0, h0 + 29, h0 + 30, h0 + 59)):
            a = t[h0 + 29][5] - t[h0][2]; bb = t[h0 + 59][5] - t[h0 + 30][2]
            if a != 0:
                xs.append((d, np.sign(a) * bb))
    v = np.array([x[1] for x in xs]); f = np.array([x[0] < "20260601" for x in xs])
    print(f"  {h0 // 60:02d}:{h0 % 60:02d} 날 {len(v)} 평균 {v.mean():+.2f} · 앞 {v[f].mean():+.2f} · 뒤 {v[~f].mean():+.2f}")
inv = {r["date"]: r for r in json.load(open("investor_KSP.json"))["rows"]}
prg = {r["date"]: r for r in json.load(open("program_K.json"))["rows"]}
idates = sorted(inv)
print("③ 전날 수급 부호 → 그날 움직임(같은 방향이면 +) · 날 · 평균 p · 맞은 비율")
for key, src, col in (("외국인", inv, "외국인"), ("기관", inv, "기관"), ("개인", inv, "개인"), ("프로그램", prg, "전체순매수")):
    for horizon in ("close", "am"):
        xs = []
        for d in days:
            prev = [x for x in idates if x < d]
            if len(prev) < 21:
                continue
            p = prev[-1]; hist = [src[x][col] for x in prev[-21:-1] if x in src]
            if p not in src or len(hist) < 15:
                continue
            z = (src[p][col] - np.mean(hist)) / (np.std(hist) or 1)
            t = byd[d]
            if 549 not in t or 930 not in t or 660 not in t:
                continue
            mv = (t[930][5] if horizon == "close" else t[660][5]) - t[549][2]
            xs.append((d, np.sign(z) * mv, z))
        v = np.array([x[1] for x in xs]); f = np.array([x[0] < "20260601" for x in xs])
        print(f"  {key:4} {horizon:5} 날 {len(v)} 평균 {v.mean():+.2f} · 앞 {v[f].mean():+.2f} · 뒤 {v[~f].mean():+.2f} · 맞음 {(v > 0).mean():.2f}")
