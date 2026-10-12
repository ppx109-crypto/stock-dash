"""KMF-0010 결과 뒤 · 판정 밖 진단(01 ~ 08 · 09-01부터 안 읽음): '덫이 −12p 멈춤에 막혔다'는 해석을 날마다 확인(GPT #301).
trap 0 칸으로 돌려 돌파에 든 날마다: 덫 조건(범위 안으로 R × W 되돌림 종가)이 그날 처음 생긴 봉 vs 그날 −12p 멈춤이 난 분을 견줌.
  가: 덫 조건 전에 멈춤 · 나: 멈춤 없이 덫 조건 생김(덫 켜짐) · 다: 덫 조건 끝내 없음 · + 그날 범위 폭 W 평균."""
import json, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf10 as M
b = M.prep(K._rows_before(M.VAL[0]))
out = {}
for nb in ("N30_b0.25", "N30_b0.5", "N60_b0.25", "N60_b0.5"):
    cfg = next(c for c in M.grid() if c["tag"] == nb + "_t0")
    want = M.signals(b, cfg)
    days, trades = K.simulate(b, want)
    stop_min = {t[0]: t[1] for t in trades if days[t[0]] <= K.DAY_STOP + 1e-9}
    byd = defaultdict(list)
    for i, r in enumerate(b):
        byd[r[0]].append(i)
    cnt = defaultdict(lambda: defaultdict(int)); wsum = defaultdict(lambda: defaultdict(float))
    for d, idx in byd.items():
        st = b[idx[0]][1] - (M.TF - 1)
        rng = [i for i in idx if b[i][1] < st + cfg["or"]]
        k0 = next((i for i in idx if want[i] in (1, -1)), None)
        if k0 is None or not rng:
            continue
        hi = max(b[i][3] for i in rng); lo = min(b[i][4] for i in rng); w = hi - lo; pos = want[k0]
        k1 = next((i for i in idx if i > k0 and ((pos > 0 and b[i][5] <= hi - M.R * w) or (pos < 0 and b[i][5] >= lo + M.R * w))), None)
        blk = next(f"{a[4:6]}-{z[4:6]}" for a, z in M.BLOCKS if a <= d <= z)
        sm = stop_min.get(d)
        cat = "다" if k1 is None and sm is None else ("가" if sm is not None and (k1 is None or sm <= b[k1][1]) else "나")
        if k1 is None and sm is not None:
            cat = "가(조건 없음 · 멈춤)"
        cnt[blk][cat] += 1; wsum[blk][cat] += w
    out[nb] = {blk: {c: {"days": n, "avg_W": round(wsum[blk][c] / n, 1)} for c, n in sorted(v.items())} for blk, v in sorted(cnt.items())}
print(json.dumps(out, ensure_ascii=False, indent=1))
