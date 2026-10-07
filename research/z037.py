"""B12 — 봇 강화(docs/RL-BOTS.md · 사용자 2026-10-07 "보조지표나 기관 · 투신 · 외국인 · 개인 매매법 조합 없어? EMA RNA 다 써본 거 맞아?"):
지금까지 한 번도 안 잰 고전 보조지표를 1일봉 엔진(새 82) 거르기로. 문턱은 **교과서 값으로 미리 정함**(숫자 고르기 없음).
값: RSI14 · MACD(12 · 26 · 9)는 신호 날 종가까지(1일봉은 그 종가에 삼 · 다른 재료와 같음).
    스토캐스틱 %K14 · ADX14 · MFI14 · OBV 20일 기울기는 고가 · 저가 · 거래량이 마감 뒤 확정이라 **전날까지**.
판: RSI > 80 거름 · RSI < 50 거름 · MACD < 시그널 거름 · %K > 90 거름 · ADX < 20 거름 · MFI > 80 거름 · OBV 20일 내림 거름.
엔진 잣대(씨앗 8 · 앞 2017 ~ 20 / 뒤 2021 ~ · 행운뺌) — 두 반 모두 같거나 나을 때만 후보.
python research/z037.py
"""
import bisect
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402

HLV = {}


def hlv(code):
    if code not in HLV:
        b = T._load(f"volume-data/{code}.json") or {}
        names = b.get("칸") or []
        rows = []
        if {"거래량", "고가", "저가"} <= set(names):
            iv, ih, il = names.index("거래량"), names.index("고가"), names.index("저가")
            rows = sorted((str(x[0]), x[ih], x[il], x[iv]) for x in (b.get("날") or []) if x[ih] and x[il] and x[iv] is not None)
        HLV[code] = ([r[0] for r in rows], rows)
    return HLV[code]


def closes(r, n):
    c = nrl.lanes[r["code"]]["closes"]
    i = r["i"]
    return np.asarray(c[max(0, i - n + 1):i + 1], float)


def rsi(r, n=14):
    c = closes(r, 200)
    if len(c) < n + 20:
        return None
    d = np.diff(c)
    up, dn = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    au, ad = up[:n].mean(), dn[:n].mean()
    for k in range(n, len(d)):                   # 와일더 평활
        au, ad = (au * (n - 1) + up[k]) / n, (ad * (n - 1) + dn[k]) / n
    return 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)


def ema(x, n):
    a, out = 2 / (n + 1), [x[0]]
    for v in x[1:]:
        out.append(out[-1] + a * (v - out[-1]))
    return np.asarray(out)


def macd_below(r):
    c = closes(r, 300)
    if len(c) < 80:
        return None
    m = ema(c, 12) - ema(c, 26)
    return bool(m[-1] < ema(m, 9)[-1])


def past(r, n):
    """전날까지 n일 (고가, 저가, 종가, 거래량) — 종가는 lanes(같은 날짜)."""
    days, rows = hlv(r["code"])
    k = bisect.bisect_left(days, r["date"])          # 신호 날 앞까지
    if k < n + 1:
        return None
    seg = rows[k - n - 1:k]
    lane = nrl.lanes[r["code"]]
    pos = {d: j for j, d in enumerate(lane["날"])} if "_pos" not in lane else lane["_pos"]
    lane["_pos"] = pos
    cl = [lane["closes"][pos[d]] if d in pos else None for d, *_ in seg]
    if any(x is None for x in cl):
        return None
    return np.array([s[1] for s in seg], float), np.array([s[2] for s in seg], float), np.array(cl, float), np.array([s[3] for s in seg], float)


def stoch(r, n=14):
    got = past(r, n)
    if got is None:
        return None
    h, l, c, _ = got
    hh, ll = h[-n:].max(), l[-n:].min()
    return None if hh == ll else (c[-1] - ll) / (hh - ll) * 100


def adx(r, n=14):
    got = past(r, 3 * n)
    if got is None:
        return None
    h, l, c, _ = got
    up, dn = h[1:] - h[:-1], l[:-1] - l[1:]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.maximum.reduce([h[1:] - l[1:], abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])])
    def w(x):
        s = [x[:n].sum()]
        for v in x[n:]:
            s.append(s[-1] - s[-1] / n + v)
        return np.asarray(s)
    atr, p, m = w(tr), w(pdm), w(mdm)
    pdi, mdi = 100 * p / np.where(atr == 0, np.nan, atr), 100 * m / np.where(atr == 0, np.nan, atr)
    dx = 100 * abs(pdi - mdi) / np.where((pdi + mdi) == 0, np.nan, pdi + mdi)
    dx = dx[~np.isnan(dx)]
    if len(dx) < n:
        return None
    a = dx[:n].mean()
    for v in dx[n:]:
        a = (a * (n - 1) + v) / n
    return a


def mfi(r, n=14):
    got = past(r, n + 1)
    if got is None:
        return None
    h, l, c, v = got
    tp = (h + l + c) / 3
    flow = tp * v
    pos = flow[1:][tp[1:] > tp[:-1]].sum()
    neg = flow[1:][tp[1:] < tp[:-1]].sum()
    return 100.0 if neg == 0 else 100 - 100 / (1 + pos / neg)


def obv_down(r, n=20):
    got = past(r, n + 1)
    if got is None:
        return None
    _, _, c, v = got
    obv = np.cumsum(np.sign(np.diff(c)) * v[1:])
    return bool(obv[-1] < obv[0])


def main():
    print("== B12: 고전 보조지표 거르기(1일봉 엔진 · 교과서 문턱) ==", flush=True)
    rows = [r for r in nrl.inside if nrl.BASE_HOLD(r)]
    tests = [("RSI14 > 80 거름", lambda r: (rsi(r) or 0) > 80), ("RSI14 < 50 거름", lambda r: (rsi(r) or 100) < 50),
             ("MACD < 시그널 거름", lambda r: macd_below(r) is True), ("스토캐스틱 %K > 90 거름(전날까지)", lambda r: (stoch(r) or 0) > 90),
             ("ADX14 < 20 거름(전날까지)", lambda r: (adx(r) or 99) < 20), ("MFI14 > 80 거름(전날까지)", lambda r: (mfi(r) or 0) > 80),
             ("OBV 20일 내림 거름(전날까지)", lambda r: obv_down(r) is True)]
    for tag, bad in tests:
        n = sum(1 for r in rows if bad(r))
        print(f"  {tag}: 후보 줄 {len(rows)} 가운데 걸림 {n}({n / len(rows):.0%})", flush=True)
    base = T.once("지금(새 82)", holds=nrl.BASE_HOLD)
    for tag, bad in tests:
        got = T.once(tag, holds=lambda r, bad=bad: nrl.BASE_HOLD(r) and not bad(r))
        T.diff_check(base, got)


if __name__ == "__main__":
    main()
