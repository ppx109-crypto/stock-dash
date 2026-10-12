"""KMF-0014 탐색(사용자 2026-10-13: "위 10일을 제외하고 작거나 짧은 추세에도 작동할 추세봇 · +800p가 되게" · "횡보장봇도 RNA로").
전체 자료 01-02 ~ 10-12(시험 2 자료 안 읽음) · 5분봉 · −25p · 1계약 · 편도 0.04p · 판단 = 봉 종가 · 체결 = 다음 봉 시가.
잣대: ex10 = 그 봇 자신의 가장 좋은 10일을 뺀 합(큰 날에 기대지 않는지) · 같이: 합 · +달 · 가장 나쁜 달 · 이웃 평평함.
짧은 추세 봇(RNA): 선 a < b < c(EMA · 짧게) 정배열 + c선 기울기 → 들기 · 정리 = 종가가 정리선 반대 · 트레일 k×ATR · 목표 g×ATR(0 = 없음) · 최대 H봉 들기(0 = 장 끝)
 · 아침 관망(watch) 켬/끔 · 하루 들기 n번."""
import sys, json, itertools
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf4 as K4
K.DAY_STOP = -25.0
END = "20261013"


def ema(a, s):
    out = np.empty(len(a)); k = 2 / (s + 1); out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = out[i - 1] + k * (a[i] - out[i - 1])
    out[:s] = np.nan
    return out


def base(b):
    c = np.array([r[5] for r in b]); h = np.array([r[3] for r in b]); l = np.array([r[4] for r in b])
    pc = np.r_[c[0], c[:-1]]
    trr = np.maximum(np.maximum(h - l, np.abs(h - pc)), np.abs(l - pc))
    atr = np.full(len(c), np.nan)
    cs = np.r_[0, np.cumsum(trr)]
    for i in range(20, len(c)):
        atr[i] = (cs[i] - cs[i - 20]) / 20               # 앞 20봉(그 봉 제외)
    return c, h, l, atr


_E = {}


def E(c, s):
    if s not in _E:
        _E[s] = ema(c, s)
    return _E[s]


def signals(b, cfg, B):
    c, h, l, atr = B
    a, m_, z = cfg["sp"]
    ea, eb, ec, ex = E(c, a), E(c, m_), E(c, z), E(c, cfg["xs"])
    n = len(b); want = [None] * n
    pos = 0; peak = ent = None; cnt = 0; day = None; watch = False; held = 0; ea0 = None
    sk = cfg.get("sk", 3)
    for i in range(n):
        d, m = b[i][0], b[i][1]
        if d != day:
            day, pos, cnt, peak, watch = d, 0, 0, None, False
        if i < sk + 1 or np.isnan(ec[i - sk]) or np.isnan(atr[i]):
            continue
        slope = ec[i] - ec[i - sk]
        up = ea[i] > eb[i] > ec[i] and slope > 0
        dn = ea[i] < eb[i] < ec[i] and slope < 0
        if pos:
            held += 1
            peak = max(peak, c[i]) if pos > 0 else min(peak, c[i])
            out = (pos > 0 and c[i] < ex[i]) or (pos < 0 and c[i] > ex[i])
            if cfg["tr"]:
                out |= (pos > 0 and c[i] < peak - cfg["tr"] * atr[i]) or (pos < 0 and c[i] > peak + cfg["tr"] * atr[i])
            if cfg["tg"] and not watch:
                out |= pos * (c[i] - ent) >= cfg["tg"] * atr[i]
            if cfg["H"] and held >= cfg["H"]:
                out = True
            if out:
                if not watch:
                    want[i] = 0
                pos, watch = 0, False
            continue
        if m > K.ENTRY_TO or cnt >= cfg["n"]:
            continue
        if up or dn:
            side = 1 if up else -1
            if m < K.ENTRY_FROM:
                if cfg["watch"]:
                    pos, peak, ent, cnt, watch, held = side, c[i], c[i], cnt + 1, True, 0
                continue
            want[i], pos, peak, ent, cnt, held = side, side, c[i], c[i], cnt + 1, 0
    return want


def report(days, trades):
    vals = days; mo = defaultdict(float)
    for d, v in vals.items():
        mo[d[:6]] += v
    vs = sorted(vals.values(), reverse=True)
    eq = pk = mdd = 0.0
    for d in sorted(vals):
        eq += vals[d]; pk = max(pk, eq); mdd = min(mdd, eq - pk)
    return {"total": round(sum(vs), 1), "ex10": round(sum(vs[10:]), 1), "trades": len(trades), "pos_m": sum(1 for v in mo.values() if v > 0),
            "worst_m": round(min(mo.values()), 1), "mdd": round(mdd, 1), "months": {k: round(v, 1) for k, v in sorted(mo.items())}}


def load():
    rows = K._rows_before(END)
    b = K4.day_start_aligned(rows, 5)
    return rows, b, base(b)
