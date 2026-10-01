"""15분봉 재료 — 15분봉 자체(시가 · 고가 · 저가 · 종가 · 거래량)에서만 만들 수 있는 장중 재료(docs/DATA-AUDIT-15M.md).

모든 값은 **그 봉이 닫힌 때까지** 알 수 있는 것만 씁니다(봉 k의 값은 봉 0 ~ k로만 셈).
- relvol: 그 봉 거래량 ÷ 지난 n거래일 같은 시각 칸 거래량 평균(오늘 빼고)
- gap: 오늘 첫 봉 시가 ÷ 전 거래일 마지막 봉 종가 − 1(오늘 내내 같은 값, 09:00 시가에 이미 앎)
- day_ret: 이 봉 종가 ÷ 오늘 첫 봉 시가 − 1
- vwap_dev: 이 봉 종가 ÷ 오늘 이 봉까지의 거래량 가중 평균값((고+저+종)/3) − 1
- market: 같은 시각 종목들의 '오늘 첫 시가 대비' 수익 평균(161종목으로 만든 장중 시장 흐름) — 시각 → 값
"""
import numpy as np


def _days(t):
    return [s[:8] for s in t]


def relvol(b, n=20):
    t, v = b["t"], np.asarray(b["v"], dtype=float)
    out = np.full(len(t), np.nan)
    hist = {}                       # 칸(HHMM) → 지난 날들의 거래량(오늘 것은 하루가 끝난 뒤 넣음)
    today, pending = None, []
    for k, s in enumerate(t):
        d, slot = s[:8], s[8:12]
        if d != today:
            for sl, vol in pending:
                hist.setdefault(sl, []).append(vol)
            today, pending = d, []
        past = hist.get(slot, [])[-n:]
        if len(past) >= max(5, n // 2):
            m = sum(past) / len(past)
            out[k] = v[k] / m if m > 0 else np.nan
        pending.append((slot, v[k]))
    return out


def gap(b):
    t, o, c = b["t"], np.asarray(b["o"], float), np.asarray(b["c"], float)
    out = np.full(len(t), np.nan)
    prev_close, today, g = None, None, np.nan
    for k, s in enumerate(t):
        if s[:8] != today:
            if today is not None:
                prev_close = c[k - 1]
            today = s[:8]
            g = o[k] / prev_close - 1 if prev_close else np.nan
        out[k] = g
    return out


def day_ret(b):
    t, o, c = b["t"], np.asarray(b["o"], float), np.asarray(b["c"], float)
    out = np.empty(len(t))
    today, first = None, None
    for k, s in enumerate(t):
        if s[:8] != today:
            today, first = s[:8], o[k]
        out[k] = c[k] / first - 1 if first else np.nan
    return out


def vwap_dev(b):
    t = b["t"]
    h, l, c, v = (np.asarray(b[x], float) for x in ("h", "l", "c", "v"))
    out = np.empty(len(t))
    today, pv, vv = None, 0.0, 0.0
    for k, s in enumerate(t):
        if s[:8] != today:
            today, pv, vv = s[:8], 0.0, 0.0
        pv += (h[k] + l[k] + c[k]) / 3 * v[k]
        vv += v[k]
        out[k] = c[k] / (pv / vv) - 1 if vv > 0 else np.nan
    return out


def market(data):
    """{시각: 같은 시각 종목들의 day_ret 평균}. 그 시각 봉이 있는 종목만 셈(그 시각에 이미 닫힌 봉)."""
    acc = {}
    for b in data.values():
        r = day_ret(b)
        for s, x in zip(b["t"], r):
            if np.isfinite(x):
                a = acc.setdefault(s, [0.0, 0])
                a[0] += x
                a[1] += 1
    return {s: a[0] / a[1] for s, a in acc.items() if a[1] >= 5}
