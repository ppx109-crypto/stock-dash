"""B 갈래: 날 고르기 특징(앞 날 자료 · 그날 시가만). 미래 참조 없음."""
import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/hdd")
from base import K, R4, Z, DAYS, stat
import bisect
AD = K.DAYS  # 전체 날(준비 기간 포함)
# 일봉: 그날 시 · 고 · 저 · 종(09:00~15:34 1분봉 전체) — 그날 끝난 뒤에만 쓰고, 판단엔 '앞 날'까지만 씀
D = {d: (K.BY[d][min(K.BY[d])][2], max(r[3] for r in K.BY[d].values()), min(r[4] for r in K.BY[d].values()), K.last_close(d)) for d in AD}
E5, E20, ATR = {}, {}, {}
e5 = e20 = a = None; pc = None
for d in AD:
    o, h, l, c = D[d]; tr = max(h, pc) - min(l, pc) if pc is not None else h - l
    e5 = c if e5 is None else e5 + (c - e5) * 2 / 6; e20 = c if e20 is None else e20 + (c - e20) * 2 / 21
    a = tr if a is None else a + (tr - a) * 2 / 15; E5[d], E20[d], ATR[d] = e5, e20, a; pc = c
IDX = {d: i for i, d in enumerate(AD)}
def prev(d, k=1): i = IDX[d] - k; return AD[i] if i >= 0 else None
def feat(d):
    """판단 시각 = 그날 09:00 시가 직후(첫 신호 09:15 앞). 앞 날 일봉 끝 값 + 그날 시가만."""
    p = prev(d); p5 = prev(d, 6)
    c = D[p][3]; a = ATR[p]
    z = (c - E20[p]) / a                       # 앞 날 종가가 EMA20에서 몇 ATR
    sl = (E20[p] - E20[p5]) / a if p5 else 0.0  # EMA20 5일 기울기 / ATR
    rna = 1 if (E5[p] > E20[p] and sl > 0) else (-1 if (E5[p] < E20[p] and sl < 0) else 0)
    gap = (D[d][0] - c) / a                    # 오늘 시가 갭 / ATR
    # 60분 EMA 띠: 오늘 앞 마지막으로 끝난 60분봉(=앞 날 마지막 봉)의 |EMA10-EMA20|/ATR60
    B, E10, E20b, keys = R4.TF[60]; i = bisect.bisect_left(keys, (d, 0)) - 1
    band = abs(E10[i][0] - E20b[i][0]) / E10[i][1]
    return {"z": z, "sl": sl, "rna": rna, "gap": gap, "band": band}
F = {d: feat(d) for d in DAYS}
