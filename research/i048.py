"""RNA 7라운드 — D3 60일 조건을 15:15 값으로 판단해도 같은 결정인지(한투 15분봉 m15-kis · 2025 ~).
1일봉 장부(DNA · VX)의 산 날마다: 60일 전 대비(종가) → 15:15 값(15:00 칸 종가)으로 바꿔 다시 잼.
DNA: 60일 전 대비 ≥ 20% · VX 1.09: 60일 전 대비 ≥ 1.09 × 변동성 × √60. 바뀌는(조건이 깨지는) 매매 수를 셈.
(변동성은 그날 종가 대신 15:15 값이어도 거의 같아 그대로 둠 · 후보 ② 매매는 60일 조건과 무관해 둘 다 같이 셈)"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash")
import nrl

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
ROW = {(r["code"], r["date"]): r for r in nrl.inside}
M15 = Path("/home/user/stock-dash/m15-kis")
_cache = {}


def at(code, day):
    if code not in _cache:
        p, c = {}, {}
        for f in sorted((M15 / code).glob("20*.csv")) if (M15 / code).exists() else []:
            for t, o, h, lo, cl, v in csv.reader(open(f)):
                if t[8:] == "1500":
                    p[t[:8]] = float(cl)
                c[t[:8]] = float(cl)          # 그날 마지막 칸 = 종가 근사
        _cache[code] = (p, c)
    p, c = _cache[code]
    return p.get(day), c.get(day)


for name, led, test in (("DNA", "r2_dna.json", lambda s, v: s >= 20.0),
                        ("VX 1.09", "r2_vx.json", lambda s, v: s >= 1.09 * v * np.sqrt(60))):
    seen = flip = 0
    gaps, margins = [], []
    for code, buy, sell, pnl, slots in json.load(open(SP + led)):
        if buy < "20250101":
            continue
        r = ROW.get((code, buy))
        p, c = at(code, buy)
        if r is None or p is None or not c or r.get("60일 전 대비") is None or r.get("변동성") is None:
            continue
        s, v = r["60일 전 대비"], r["변동성"]
        if not test(s, v):           # 60일 조건 없이 들어온 매매(후보 ②)
            continue
        s15 = ((1 + s / 100) * p / c - 1) * 100
        seen += 1
        gaps.append((p / c - 1) * 100)
        flip += not test(s15, v)
        margins.append(s - (20.0 if name == "DNA" else 1.09 * v * np.sqrt(60)))
    m = np.array(margins)
    print(f"  {name:8s} 60일 조건으로 산 매매 {seen} · 15:15 값이면 조건 깨짐 {flip}({flip / max(seen, 1) * 100:.1f}%) · "
          f"여유 중앙 {np.median(m):.1f}%p · 여유 2%p 안 {np.mean(m < 2) * 100:.0f}% · 15:15 − 종가 절대 평균 {np.mean(np.abs(gaps)):.2f}%")
