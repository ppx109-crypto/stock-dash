"""I 5라운드 준비 — 새 공시 종류(대량보유 · 임원소유 · 주식소각 · 잠정실적 · 조회공시 · 시설투자 · 기업설명회 · 최대주주지분변동)를
두 가지로 훑기(2026-10-03 · 토요일 전체 수집으로 2015 ~ 기록이 채워진 뒤).
 A 시장 물결: 종류마다 하루 공시 수 → 하루 밀기(장 끝 뒤 공시는 다음 거래일부터) → 20일 합 → 앞 250일과만 견준 순위.
   순위 위 20% − 아래 20%일 때 코스피200 · 코스닥150 앞 5 · 20일 수익 차이(B 2017 ~ 2020 · C 2021 ~).
 B 종목 사건: 공시 다음 거래일 종가에 사서 5 · 20거래일 뒤 종가까지, 같은 기간 코스피200(069500)을 뺀 초과 수익.
   같은 종목 · 같은 종류는 20거래일 안 겹치면 첫 건만. 비용 0.3%(왕복) 뺌.
미래 참조: 공시 날 종가가 아니라 '다음 거래일 종가'에 삼 · 순위는 앞 날들과만 견줌.
I_KINDS=쉼표로 종류 지정(기본: 위 새 종류 + 견줌용 자사주취득 · 공급계약)."""
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

ROOT = Path("/home/user/stock-dash")
D, n = I.DAYS, len(I.DAYS)
IX = {d: i for i, d in enumerate(D)}
NEW = ["대량보유", "임원소유", "주식소각", "잠정실적", "조회공시", "시설투자", "기업설명회", "최대주주지분변동"]
KINDS = [k for k in os.environ.get("I_KINDS", ",".join(NEW + ["자사주취득", "공급계약"])).split(",") if k]
PER = (("B", "20170101", "20210101"), ("C", "20210101", "20991231"))
COST = 0.003

ev = {k: [] for k in KINDS}
for f in sorted(glob.glob(str(ROOT / "event-data/*.json"))):
    code = Path(f).stem
    for r in json.load(open(f)).get("rows", []):
        if r.get("kind") in ev and (not I.CUT or r["date"] <= I.CUT):
            ev[r["kind"]].append((r["date"], code))


def roll_sum(a, w):
    c = np.cumsum(np.insert(a, 0, 0))
    out = np.full(n, np.nan)
    out[w - 1:] = c[w:] - c[:-w]
    return out


def rank250(a):
    out = np.full(n, np.nan)
    for i in range(250, n):
        h = a[i - 250:i]
        h = h[np.isfinite(h)]
        if len(h) > 150 and np.isfinite(a[i]):
            out[i] = (h < a[i]).mean() * 100
    return out


fwd = {}
for code in ("069500", "229200"):
    p = I.px(code)
    for h in (5, 20):
        f = np.full(n, np.nan)
        f[:-h] = p[h:] / p[:-h] - 1
        fwd[(code, h)] = f

print("== A 시장 물결: 순위 위20% − 아래20% 앞 수익 차이(%) · B / C ==", flush=True)
print("   칸: 코스피200 5일 · 20일 | 코스닥150 5일 · 20일", flush=True)
for k in KINDS:
    cnt = np.zeros(n)
    for d, _ in ev[k]:
        i = np.searchsorted(D, d)
        if i < n:
            cnt[i] += 1
    a = np.concatenate([[np.nan], roll_sum(cnt, 20)[:-1]])          # 하루 밀기
    first = min((d for d, _ in ev[k]), default="-")
    rk = rank250(a)
    parts, same = [], 0
    for code in ("069500", "229200"):
        for h in (5, 20):
            cell = []
            for _, lo, hi in PER:
                idx = np.array([lo <= d < hi for d in D])
                f = fwd[(code, h)]
                lo_s, hi_s = idx & (rk <= 20) & np.isfinite(f), idx & (rk >= 80) & np.isfinite(f)
                cell.append((f[hi_s].mean() - f[lo_s].mean()) * 100 if lo_s.sum() > 30 and hi_s.sum() > 30 else np.nan)
            same += np.isfinite(cell).all() and np.sign(cell[0]) == np.sign(cell[1])
            parts.append(f"{cell[0]:+5.1f}/{cell[1]:+5.1f}")
    print(f"  {k:10s} {len(ev[k]):6d}건 첫 {first} | " + " | ".join(parts) + ("  ★ 같은 방향 %d/4" % same if same >= 3 else ""), flush=True)

print("\n== B 종목 사건: 다음 거래일 종가 사기 → 코스피200 뺀 초과 수익(비용 0.3% 뺌) ==", flush=True)
k200 = dict(zip(D, I.px("069500")))
cache = {}


def closes(code):
    if code not in cache:
        try:
            body = json.load(open(ROOT / f"price-data/{code}.json"))
            rows = [(str(d), float(c)) for d, c in body["closes"] if c and (not I.CUT or str(d) <= I.CUT)]
        except (OSError, ValueError, KeyError):
            rows = []
        cache[code] = ([d for d, _ in rows], np.array([c for _, c in rows]))
    return cache[code]


for k in KINDS:
    res = {(nm, h): [] for nm, _, _ in PER for h in (5, 20)}
    last = {}
    for d, code in sorted(ev[k]):
        ds, cs = closes(code)
        if len(ds) < 30:
            continue
        j = int(np.searchsorted(ds, d, side="right"))               # 공시 날 다음 거래일
        if j >= len(ds) or (code in last and j - last[code] < 20):
            continue
        last[code] = j
        nm = next((p for p, lo, hi in PER if lo <= ds[j] < hi), None)
        if nm is None:
            continue
        for h in (5, 20):
            if j + h < len(ds) and ds[j] in k200 and ds[j + h] in k200:
                r = cs[j + h] / cs[j] - 1 - (k200[ds[j + h]] / k200[ds[j]] - 1) - COST
                if abs(r) < 1.5:
                    res[(nm, h)].append(r)
    cells = []
    for nm, _, _ in PER:
        for h in (5, 20):
            x = np.array(res[(nm, h)])
            cells.append(f"{nm}{h}일 {len(x):4d}건 {x.mean()*100:+5.2f}% 이김{(x > 0).mean()*100:3.0f}%" if len(x) >= 20 else f"{nm}{h}일 {len(x):4d}건  -")
    print(f"  {k:10s} | " + " | ".join(cells), flush=True)
print("끝", flush=True)
