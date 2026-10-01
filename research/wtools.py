"""W(약세 · 옆걸음장) 갈래 도우미 — 1일봉 엔진(ntools.once)으로 돌리고, 1일봉 규칙(새 82)과의 주 손익 상관 · 반반 계좌를 함께 찍음.
1일봉 규칙 매매 목록은 research/x008.py Q_PART=d1이 만든 scratchpad/x008_d1.json(없으면 만들어 씀)."""
import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
D1 = Path(SP + "x008_d1.json")
weak = lambda r: nrl.BR.get(r["date"], 100) < 50


def base_ledger():
    if not D1.exists():
        got = T.once("1일봉 새 82(견줄 몫)")
        json.dump([(t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for s in ("앞", "뒤") if got.get(s)
                   for t in got[s]["매매목록"]], open(D1, "w"))
    return json.load(open(D1))


def _wk(s):
    return date(int(s[:4]), int(s[4:6]), int(s[6:8])).isocalendar()[:2]


def mix(base, mine, lo, hi):
    """주 확정 손익(계좌 몫 %) 상관 · 1일봉만 / W만 / 반반의 합 · 골 · 가장 나쁜 주."""
    def daily(rows, w):
        out = {}
        for code, b, s, g, k in rows:
            if lo <= b < hi:
                out[s] = out.get(s, 0) + w * k / 10 * g
        return out

    def stats(d):
        eq, peak, dip, wk = 1.0, 1.0, 0.0, {}
        for x in sorted(d):
            eq *= 1 + d[x] / 100
            peak = max(peak, eq)
            dip = min(dip, eq / peak - 1)
            wk[_wk(x)] = wk.get(_wk(x), 0) + d[x]
        return round(sum(d.values()), 1), round(dip * 100, 1), round(min(wk.values()) if wk else 0, 1), wk

    a, b = daily(base, 1), daily(mine, 1)
    half = {}
    for x, v in list(a.items()) + list(b.items()):
        half[x] = half.get(x, 0) + v / 2
    sa, sb, sh = stats(a), stats(b), stats(half)
    weeks = sorted(set(sa[3]) | set(sb[3]))
    va = np.array([sa[3].get(w, 0) for w in weeks]); vb = np.array([sb[3].get(w, 0) for w in weeks])
    corr = float(np.corrcoef(va, vb)[0, 1]) if len(weeks) > 3 and va.std() and vb.std() else float("nan")
    return corr, sa[:3], sb[:3], sh[:3]


def run(tag, holds, **kw):
    """W 규칙 하나 → ntools.once 줄 + 두 반 각각 상관 · 계좌 견줌 줄."""
    got = T.once(tag, holds=holds, **kw)
    base = base_ledger()
    for side, lo, hi in (("앞", "20170101", nrl.rule.MID), ("뒤", nrl.rule.MID, "20991231")):
        g = got.get(side)
        if not g:
            print(f"    {side}: 매매가 너무 적어 셈 못 함", flush=True)
            continue
        mine = [(t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for t in g["매매목록"]]
        corr, a, b, h = mix(base, mine, lo, hi)
        print(f"    {side}: 주 손익 상관 {corr:+.2f} | 1일봉만 합 {a[0]:+.1f} 골 {a[1]} 나쁜 주 {a[2]} | W만 합 {b[0]:+.1f} 골 {b[1]} 나쁜 주 {b[2]} | "
              f"반반 합 {h[0]:+.1f} 골 {h[1]} 나쁜 주 {h[2]}", flush=True)
    return got
