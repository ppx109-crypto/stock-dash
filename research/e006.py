"""E 6회차 — 이익과 주가를 함께 봄(가치 · 괴리). 사용자 2026-10-02 "DART 정보를 더 잘 활용할 방법".
그날 알려진(접수일이 그날 앞) 최근 네 분기 영업이익 합(TTM)으로:
  이익 수익률 = TTM 영업이익 ÷ 그날 시가총액(%)                       — 이익에 비해 싼가
  이익 수익률 변화 = 지금 − 1년 전(같은 방식, %p)                       — 이익이 주가보다 빨리 늘었나
  괴리 = TTM 영업이익 증가율(앞 네 분기 대비, %) − 주가 1년 수익률(%)     — '이익은 늘었는데 주가는 덜 오름'이 크면 +
[1] 100위 전체 · [2] 1일봉 사는 조건 안 — 다섯 무리별 앞으로 20 · 60일(그날 100위 평균 대비) · 두 반
Q_PART=2: 두 반 모두 한쪽으로 나온 것을 엔진(새 82 · 씨앗 8)에 — 거르기 · 같은 날 후보 순서."""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import etools as E
import nrl

MID = nrl.rule.MID
book = E.Book()


def ttm(seen, last):
    y, k = last
    qs = [(y if j <= k else y - 1, j) for j in range(1, 5)]
    now = [seen.get(q, {}).get("o") for q in qs]
    old = [seen.get(q, {}).get("o0") for q in qs]
    return (None if None in now else sum(now)), (None if None in old else sum(old))


def feats(r):
    seen, last = book.known(r["code"], r["date"])
    if not seen:
        return None
    now, old = ttm(seen, last)
    cap = r.get("시가총액")
    if now is None or not cap:
        return None
    c = nrl.lanes[r["code"]]["closes"]
    i = r["i"]
    ret1y = c[i] / c[i - 250] - 1 if i >= 250 and c[i - 250] else None
    f = {"수익률": now / cap * 100}
    if old is not None and ret1y is not None:
        cap_then = cap / (1 + ret1y)
        f["수익률변화"] = now / cap * 100 - old / cap_then * 100
        g = E.growth(now, old)
        f["괴리"] = g - ret1y * 100 if g is not None else None
    return f


rows = list(nrl.inside)
F = {(r["code"], r["date"]): feats(r) for r in rows}
fw, mean = {}, {}
for r in rows:
    c = nrl.lanes[r["code"]]["closes"]
    i = r["i"]
    for h in (20, 60):
        v = c[i + 1 + h] / c[i + 1] - 1 if i + 1 + h < len(c) and c[i + 1] else None
        fw[(r["code"], r["date"], h)] = v
        if v is not None:
            mean.setdefault((r["date"], h), []).append(v)
mean = {k: float(np.mean(v)) for k, v in mean.items()}
ex = lambda r, h: None if fw[(r["code"], r["date"], h)] is None else fw[(r["code"], r["date"], h)] - mean[(r["date"], h)]
val = lambda r, k: (F[(r["code"], r["date"])] or {}).get(k)


def show(name, picked):
    out = [f"  {name:22s}"]
    for side, test in (("앞", lambda d: d < MID), ("뒤", lambda d: d >= MID)):
        sel = [r for r in picked if test(r["date"])]
        a = [ex(r, 20) for r in sel if ex(r, 20) is not None]
        b = [ex(r, 60) for r in sel if ex(r, 60) is not None]
        out.append(f"| {side} {len(a)}건(적음)" if len(a) < 20 else
                   f"| {side} {len(a):6d}건 20일 {np.mean(a) * 100:+5.2f} 60일 {np.mean(b) * 100:+5.2f} 이김 {np.mean(np.array(a) > 0) * 100:4.1f}")
    print(" ".join(out), flush=True)


def fifths(pool, key):
    vals = [val(r, key) for r in pool if val(r, key) is not None]
    if len(vals) < 100:
        print(f"  {key}: 값 {len(vals)}(적음)", flush=True)
        return None
    qs = np.quantile(vals, [0.2, 0.4, 0.6, 0.8])
    print(f" -- {key} 다섯 무리(경계 {', '.join(f'{q:.1f}' for q in qs)})", flush=True)
    for j in range(5):
        lo = -np.inf if j == 0 else qs[j - 1]
        hi = np.inf if j == 4 else qs[j]
        show(f"무리 {j + 1}", [r for r in pool if val(r, key) is not None and lo <= val(r, key) < hi])
    return qs


part = os.environ.get("Q_PART", "1")
if part == "1":
    have = [r for r in rows if F[(r["code"], r["date"])]]
    print(f"== E 6회차: 100위 줄 {len(rows)} 중 이익 · 시총 붙은 {len(have)} ==", flush=True)
    for label, pool in (("[1] 100위 전체", have), ("[2] 1일봉 사는 조건 안", [r for r in have if nrl.BASE_HOLD(r)])):
        print(f"\n{label}", flush=True)
        show("전체", pool)
        for k in ("수익률", "수익률변화", "괴리"):
            fifths(pool, k)
else:
    import ntools as T
    base = nrl.BASE_HOLD
    b = T.once("지금(새 82)", holds=base)
    door = [r for r in rows if base(r)]
    for key in ("수익률", "수익률변화", "괴리"):
        vals = [val(r, key) for r in door if val(r, key) is not None]
        if len(vals) < 100:
            continue
        lo20, hi80 = np.quantile(vals, [0.2, 0.8])
        g = T.once(f"− {key} 아래 20%", holds=lambda r, key=key, lo=lo20: base(r) and not (val(r, key) is not None and val(r, key) < lo))
        T.diff_check(b, g, "거른")
        g = T.once(f"− {key} 위 20%", holds=lambda r, key=key, hi=hi80: base(r) and not (val(r, key) is not None and val(r, key) >= hi))
        T.diff_check(b, g, "거른")
        g = T.once(f"같은 날 {key} 큰 것 먼저", rank=lambda r, key=key: (-(val(r, key) if val(r, key) is not None else -1e9), nrl.rule.order(r)))
print("끝", flush=True)
