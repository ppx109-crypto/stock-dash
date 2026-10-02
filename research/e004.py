"""E 4회차(E9) — 현금흐름 · 이익의 질(사용자 "잠정실적 · 현금흐름 두 개로 분석하고 진행해줘", 2026-10-02).
자료: cash-data/{code}.json(collect_dart_extra cashflow · 전체 재무제표 · 접수번호 앞 8자리 = 접수일). 신호 날 **앞** 접수만.
보는 것(가장 최근 보고서 기준, 누적 = 그해 1분기부터 그 분기까지):
  발생액 비율 = (순이익 누적 − 영업현금 누적) ÷ 자산        — 높을수록 '이익은 났는데 현금이 안 들어옴'
  현금 전환   = 영업현금 누적 ÷ 영업이익 누적
  영업현금 증가 = 영업현금 누적 vs 작년 같은 누적
  재고 − 매출 = 재고 증가율(작년 같은 보고서 대비) − 매출 누적 증가율
  매출채권 − 매출 = 매출채권 증가율 − 매출 누적 증가율
  설비투자 비율 = 설비투자 누적 ÷ 자산
[1] 그날 시총 100위 전체 · [2] 1일봉 사는 조건 안 — 앞으로 20 · 60일 수익(그날 100위 평균 대비, 두 반)
[3] 두 반 모두 같은 쪽으로 나온 것만 엔진(새 82 · 씨앗 8)에 거르기로."""
import bisect
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl

ROOT = Path("/home/user/stock-dash")
KIND = {"1분기": 1, "반기": 2, "3분기": 3, "사업": 4}
MID = nrl.rule.MID


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def series(code):
    try:
        body = json.loads((ROOT / "cash-data" / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    out = []
    for key, v in (body.get("rows") or {}).items():
        if not v or "-" not in key or not str(v.get("접수번호", ""))[:8].isdigit():
            continue
        y, k = key.split("-", 1)
        if k in KIND:
            out.append((str(v["접수번호"])[:8], (int(y), KIND[k]), v))
    out.sort()
    return ([d for d, _, _ in out], out) if out else None


CACHE = {}


def feats(code, day):
    if code not in CACHE:
        CACHE[code] = series(code)
    got = CACHE[code]
    if not got:
        return None
    days, rows = got
    n = bisect.bisect_left(days, day)
    if not n:
        return None
    seen = {q: v for _, q, v in rows[:n]}
    last = max(seen)
    v = seen[last]
    prev = seen.get((last[0] - 1, last[1]))
    g = lambda a, b: (a - b) / abs(b) * 100 if a is not None and b not in (None, 0) else None
    ni, cfo, op = num(v.get("순이익_누적")), num(v.get("영업현금")), num(v.get("영업이익_누적"))
    assets = num(v.get("자산"))
    f = {"분기": last}
    f["발생액"] = (ni - cfo) / assets * 100 if None not in (ni, cfo) and assets else None
    f["현금전환"] = cfo / op if cfo is not None and op and op > 0 else None
    f["영업현금증가"] = g(cfo, num(v.get("영업현금_작년")))
    f["영업현금적자"] = cfo is not None and cfo < 0
    sales_g = g(num(v.get("매출_누적")), num(v.get("매출_작년누적")))
    if prev:
        inv_g = g(num(v.get("재고")), num(prev.get("재고")))
        ar_g = g(num(v.get("매출채권")), num(prev.get("매출채권")))
        f["재고-매출"] = inv_g - sales_g if None not in (inv_g, sales_g) else None
        f["채권-매출"] = ar_g - sales_g if None not in (ar_g, sales_g) else None
    capex = num(v.get("설비투자"))
    f["설비투자"] = abs(capex) / assets * 100 if capex is not None and assets else None
    return f


rows = list(nrl.inside)
F = {(r["code"], r["date"]): feats(r["code"], r["date"]) for r in rows}
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


def show(name, picked):
    out = [f"  {name:24s}"]
    for side, test in (("앞", lambda d: d < MID), ("뒤", lambda d: d >= MID)):
        sel = [r for r in picked if test(r["date"])]
        a = [ex(r, 20) for r in sel if ex(r, 20) is not None]
        b = [ex(r, 60) for r in sel if ex(r, 60) is not None]
        out.append(f"| {side} {len(a)}건(적음)" if len(a) < 20 else
                   f"| {side} {len(a):6d}건 20일 {np.mean(a) * 100:+5.2f} 60일 {np.mean(b) * 100:+5.2f} 이김 {np.mean(np.array(a) > 0) * 100:4.1f}")
    print(" ".join(out), flush=True)


def fifths(pool, key):
    vals = [(F[(r["code"], r["date"])] or {}).get(key) for r in pool]
    vals = [v for v in vals if v is not None]
    if len(vals) < 100:
        print(f"  {key}: 값 {len(vals)}개(적음)", flush=True)
        return
    qs = np.quantile(vals, [0.2, 0.4, 0.6, 0.8])
    print(f" -- {key} 다섯 무리(경계 {', '.join(f'{q:.1f}' for q in qs)})", flush=True)
    for j in range(5):
        lo = -np.inf if j == 0 else qs[j - 1]
        hi = np.inf if j == 4 else qs[j]
        show(f"무리 {j + 1}", [r for r in pool if (F[(r["code"], r["date"])] or {}).get(key) is not None
                               and lo <= F[(r["code"], r["date"])][key] < hi])


have = [r for r in rows if F[(r["code"], r["date"])]]
print(f"== E 4회차(E9 현금흐름): 100위 줄 {len(rows)} 중 현금흐름 붙은 {len(have)} ==", flush=True)
if len(have) < 1000:
    print("현금흐름 자료가 아직 적습니다(cash-data 수집 중). 끝.", flush=True)
    sys.exit(0)
KEYS = ("발생액", "현금전환", "영업현금증가", "재고-매출", "채권-매출", "설비투자")
for label, pool in (("[1] 100위 전체", have), ("[2] 1일봉 사는 조건 안", [r for r in have if nrl.BASE_HOLD(r)])):
    print(f"\n{label}", flush=True)
    show("현금흐름 붙은 것 전체", pool)
    show("영업현금 적자", [r for r in pool if F[(r["code"], r["date"])].get("영업현금적자")])
    show("이익 흑자 · 영업현금 적자", [r for r in pool if F[(r["code"], r["date"])].get("영업현금적자")
                                and (F[(r["code"], r["date"])].get("발생액") or 0) > 0])
    for k in KEYS:
        fifths(pool, k)
print("끝", flush=True)
