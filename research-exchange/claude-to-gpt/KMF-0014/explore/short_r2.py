"""2차: 들어가는 법을 바꿈 — 흐름(c선 기울기 · 정배열) 안에서
 pull: 값이 b선까지 눌렸다(앞 봉 종가 ≤ b선) 다시 a선 위로 마감하면 듦
 brk : 지난 N봉 고가(팔기는 저가)를 뚫는 종가에 듦
 나가기: 목표 g×ATR · 멈춤 s×ATR(들 때 값 기준 · 종가로) · 최대 H봉 · 흐름 풀리면(c선 반대) 정리.
 잣대 ex10(자기 위 10일 뺀 합) · ex10k13(KMF-0013 위 10일 날짜를 뺀 합)."""
import sys, json, itertools
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import short_lab as S
sys.path.insert(0, str(S.ROOT / "research"))
import kmf13 as M13
rows, b, B = S.load()
c, h, l, atr = B
d13, _ = S.K.simulate(b, M13.signals(b, M13.grid()[0]))
TOP13 = set(sorted(d13, key=lambda d: -d13[d])[:10])


def sig2(cfg):
    a, m_, z = cfg["sp"]
    ea, eb, ec = S.E(c, a), S.E(c, m_), S.E(c, z)
    n = len(b); want = [None] * n; pos = 0; ent = None; cnt = 0; day = None; held = 0
    for i in range(n):
        d, m = b[i][0], b[i][1]
        if d != day:
            day, pos, cnt = d, 0, 0
        if i < 30 or np.isnan(ec[i - 3]) or np.isnan(atr[i]):
            continue
        slope = ec[i] - ec[i - 3]
        upt = eb[i] > ec[i] and slope > 0
        dnt = eb[i] < ec[i] and slope < 0
        if pos:
            held += 1
            g = pos * (c[i] - ent)
            out = g >= cfg["g"] * atr[i] or g <= -cfg["s"] * atr[i] or (cfg["H"] and held >= cfg["H"]) or (pos > 0 and c[i] < ec[i]) or (pos < 0 and c[i] > ec[i])
            if out:
                want[i], pos = 0, 0
            continue
        if m < S.K.ENTRY_FROM or m > S.K.ENTRY_TO or cnt >= cfg["n"]:
            continue
        for side, ok in ((1, upt), (-1, dnt)):
            if not ok:
                continue
            if cfg["mode"] == "pull":
                trig = side * (c[i - 1] - eb[i - 1]) <= 0 and side * (c[i] - ea[i]) > 0
            else:
                w = h[i - cfg["N"]:i].max() if side > 0 else l[i - cfg["N"]:i].min()
                trig = side * (c[i] - w) > 0
            if trig:
                want[i], pos, ent, cnt, held = side, side, c[i], cnt + 1, 0
                break
    return want


res = {}
for sp, mode, N, g, s, H, n in itertools.product([(3, 10, 30), (4, 15, 45), (5, 20, 60), (8, 30, 90)], ("pull", "brk"), (6, 12), (1, 2, 3), (1, 2), (6, 0), (6, 12)):
    if mode == "pull" and N == 12:
        continue
    cfg = {"sp": sp, "mode": mode, "N": N, "g": g, "s": s, "H": H, "n": n}
    days, tr = S.K.simulate(b, sig2(cfg))
    r = S.report(days, tr); r["ex10k13"] = round(sum(v for d, v in days.items() if d not in TOP13), 1)
    res[json.dumps(cfg)] = r
json.dump(res, open(Path(__file__).parent / "short_r2.json", "w"), ensure_ascii=False)
for k, v in sorted(res.items(), key=lambda kv: -kv[1]["ex10"])[:20]:
    print(k, {x: v[x] for x in ("total", "ex10", "ex10k13", "trades", "pos_m", "worst_m", "mdd")})
print("조합", len(res), "· ex10 > 0인 조합", sum(1 for v in res.values() if v["ex10"] > 0))
