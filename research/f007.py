"""F 7회차(첫 판) — 2006 ~ 2016(2008 금융위기 · 2011 포함)에도 수급 조건이 통했나. investor-full 받아진 종목만.
대상: 그날까지 20일 평균 거래대금 상위 100(받아진 종목 안 · 미래 참조 없음 · 주식수 자료가 2016부터라 시총 대신).
추세(간단 흉내): 종가 > 60일선 · 20일선 > 60일선. 수급은 전날까지 5일. 앞으로 20일 시장 넘는 수익(그날 대상 평균 대비).
기간: 2006 ~ 2010 · 2011 ~ 2016 · 2017 ~ 2020 · 2021 ~(견줌)."""
import glob
import json
from pathlib import Path

import numpy as np

COLS = None
data = {}
for p in sorted(glob.glob("investor-full/*.json")):
    body = json.loads(Path(p).read_text(encoding="utf-8"))
    code = body["code"]
    COLS = body["cols"]
    try:
        pr = json.loads(Path(f"price-data/{code}.json").read_text(encoding="utf-8"))["closes"]
        vo = json.loads(Path(f"volume-data/{code}.json").read_text(encoding="utf-8"))["날"]
    except (OSError, ValueError, KeyError):
        continue
    data[code] = (body["rows"], dict(pr), {r[0]: r[2] for r in vo if len(r) > 2})
days = sorted({d for rows, cl, tv in data.values() for d in cl if d >= "20060101"})
di = {d: i for i, d in enumerate(days)}
T, N = len(days), len(data)
codes = sorted(data)
C = np.full((N, T), np.nan); V = np.full((N, T), np.nan)
F = {c: np.full((N, T), np.nan) for c in COLS if c not in ("date", "종가")}
for j, code in enumerate(codes):
    rows, cl, tv = data[code]
    for d, c in cl.items():
        if d in di:
            C[j, di[d]] = c
    for d, v in tv.items():
        if d in di:
            V[j, di[d]] = v
    for r in rows:
        if r[0] in di:
            for k, col in enumerate(COLS):
                if col in F and r[k] is not None:
                    F[col][j, di[r[0]]] = r[k]


def roll(a, n):
    out = np.full_like(a, np.nan)
    cs = np.nancumsum(np.nan_to_num(a), axis=1)
    out[:, n:] = (cs[:, n:] - cs[:, :-n]) / n
    return out


ma20, ma60, tv20 = roll(C, 20), roll(C, 60), roll(V, 20)
fl5 = {c: roll(F[c], 5) * 5 for c in ("외국인", "투신", "개인", "금융투자", "보험", "기관", "연기금")}
lag = lambda a: np.concatenate([np.full((N, 1), np.nan), a[:, :-1]], axis=1)   # 전날까지
fl5 = {c: lag(v) for c, v in fl5.items()}
fwd = np.full((N, T), np.nan)
fwd[:, 1:T - 21] = C[:, 22:] / C[:, 1:T - 21] - 1        # t+1 종가에 사서 20일
uni = np.zeros((N, T), bool)
tvl = lag(tv20)
for t in range(T):
    v = tvl[:, t]
    ok = ~np.isnan(v) & ~np.isnan(C[:, t])
    if ok.sum() < 30:
        continue
    k = np.argsort(-np.where(ok, v, -1))[:min(100, ok.sum())]
    uni[k, t] = True
mean = np.array([np.nanmean(fwd[uni[:, t], t]) if uni[:, t].any() else np.nan for t in range(T)])
ex = fwd - mean[None, :]
trend = (C > ma60) & (ma20 > ma60)
pos = lambda c: fl5[c] > 0
negv = lambda c: fl5[c] < 0
teacher = pos("외국인") & pos("투신") & negv("개인")
reverse = negv("외국인") & pos("개인")
D = np.array(days)
SPANS = (("2006 ~ 2010", "20060101", "20110101"), ("2011 ~ 2016", "20110101", "20170101"),
         ("2017 ~ 2020", "20170101", "20210101"), ("2021 ~", "20210101", "20991231"))
print(f"== F 7회차(첫 판): 받아진 {N}종목 · {days[0]} ~ {days[-1]} ==", flush=True)


def show(name, m):
    out = [f"  {name:30s}"]
    for nm, lo, hi in SPANS:
        sel = m & uni & ((D >= lo) & (D < hi))[None, :] & ~np.isnan(ex)
        v = ex[sel]
        out.append(f"| {nm} {v.size:6d}건 {np.mean(v) * 100:+5.2f} 가운데 {np.median(v) * 100:+5.2f} 이김 {np.mean(v > 0) * 100:4.1f}" if v.size else f"| {nm} 없음")
    print(" ".join(out), flush=True)


ALL = np.ones((N, T), bool)
show("모두", ALL)
show("추세(흉내)", trend)
show("가르침(외+ 투+ 개−)", teacher)
show("추세 + 가르침", trend & teacher)
show("추세 + 가르침 아님", trend & ~teacher)
show("추세 + 반대(외− 개+)", trend & reverse)
show("추세 + 가르침 + 금융투자+", trend & teacher & pos("금융투자"))
show("추세 + 가르침 + 보험+", trend & teacher & pos("보험"))
show("추세 + 가르침 + 연기금+", trend & teacher & pos("연기금"))
show("추세 + 외+ 기관+", trend & pos("외국인") & pos("기관"))
print("끝", flush=True)
