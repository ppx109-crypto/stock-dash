"""G12 — 정배열 매매 손절의 RNA(사용자 2026-10-02: 미니코스피 v11처럼 고정 대신 변동성 비례).
손절 % = k × 변동성(lab.rolling_std: 최근 20거래일 하루 등락의 표준편차 %) · [하한, 상한]으로 자름. 지금은 고정 10%
(정배열 후보 변동성 가운데 2.58% → k 4가 지금과 비슷). 1시간봉 · 15분봉은 산 날 '전' 거래일 값(그날 값은 장중이라 안 씀)."""
import bisect
import json

import lab

HOME = "/home/user/stock-dash"
_V = {}
VARIANTS = {"1": (("변동성 × 3(5 ~ 20%)", 3, 5, 20), ("변동성 × 4(5 ~ 20%)", 4, 5, 20)),
            "2": (("변동성 × 5(5 ~ 20%)", 5, 5, 20), ("변동성 × 4(7 ~ 14%)", 4, 7, 14))}


def vol_before(code, day):
    if code not in _V:
        try:
            rows = json.load(open(f"{HOME}/price-data/{code[:6]}.json", encoding="utf-8"))["closes"]
            _V[code] = ([str(d) for d, _ in rows], lab.rolling_std([float(c) for _, c in rows]))
        except (OSError, ValueError, KeyError):
            _V[code] = ([], [])
    days, v = _V[code]
    k = bisect.bisect_left(days, day) - 1
    return v[k] if 0 <= k < len(v) else None


def stop_pct(v, k, lo=5, hi=20, default=10.0):
    return default if not v else min(max(k * v, lo), hi)
