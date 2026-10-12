"""KMF-0010 준비 · 판정 밖 진단 4(2026-01 ~ 08 · 09-01부터 안 읽음).
KMF-0009 고른 칸(N30_z0.15_b0.25)을 두 부분으로 나눔: ① 횡보 부분만(범위 끝 되돌림 · 범위 밖 b×W 나가면 정리만 · 뒤집지 않음)
② 추세 부분만(되돌림 없이 범위 밖 b×W 돌파에 들고 장 끝까지). 달마다 합."""
import json, sys
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf9 as K9

def sig(b, cfg, part):
    n = len(b); want = [None] * n; i = 0
    while i < n:
        d = b[i][0]; j = i
        while j < n and b[j][0] == d:
            j += 1
        start = b[i][1] - (K9.TF - 1); hi = lo = None; pos, done = 0, False
        for k in range(i, j):
            m, h, l, c = b[k][1], b[k][3], b[k][4], b[k][5]
            if m < start + cfg["or"]:
                hi = h if hi is None else max(hi, h); lo = l if lo is None else min(lo, l); continue
            if hi is None or hi <= lo or done:
                continue
            w = hi - lo; mid = (hi + lo) / 2; ok = m <= K.ENTRY_TO
            up, dn = c > hi + cfg["b"] * w, c < lo - cfg["b"] * w
            if up or dn:
                if part == "trend" and ok:
                    want[k] = 1 if up else -1
                elif part == "fade" and pos != 0:
                    want[k] = 0
                pos, done = 0, True
                continue
            if part == "fade":
                if pos == 0 and ok:
                    if hi - cfg["z"] * w <= c <= hi: want[k], pos = -1, -1
                    elif lo <= c <= lo + cfg["z"] * w: want[k], pos = 1, 1
                elif pos != 0 and ((pos < 0 and c <= mid) or (pos > 0 and c >= mid)):
                    want[k], pos = 0, 0
        i = j
    return want

b = K9.prep(K._rows_before(K.TEST[0]))
cfg = next(c for c in K9.grid() if K9.name(c) == "N30_z0.15_b0.25")
out = {}
for part in ("fade", "trend"):
    days, trades = K.simulate(b, sig(b, cfg, part))
    mo = defaultdict(float)
    for d, v in days.items():
        mo[d[:6]] += v
    out[part] = {"months": {k: round(v, 2) for k, v in sorted(mo.items())}, "sum": round(sum(days.values()), 2), "trades": len(trades)}
print(json.dumps(out, ensure_ascii=False, indent=1))
