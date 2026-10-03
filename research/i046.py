"""RNA 1라운드 고원 확인 — i045의 엔진 RNA 후보(급락 자기 기록 백분위 · 코스닥 RNA 익절손절) · 빈칸 엔진 · 코스닥 인버스(사용자 2026-10-03).
DNA: 급락 = 코스피200 5일 ≤ −5% · 코스닥 과열 = 코스닥150 10일 ≥ +10%.
RNA: 그 지수의 앞 60일 하루 흔들림(표준편차 · 그날까지만)으로 나눔 → 급락 = 5일 ≤ −k × σ × √5 · 과열 = 10일 ≥ +k × σ × √10.
k는 DNA와 신호 날 수가 비슷해지는 값 근처를 흔듦. 사고팔기(익절 · 손절 · 기간 · 쉼)는 그대로. 계좌 전부 · A 2012 ~ 2016 · B · C."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

PER = (("A", "20120101", "20170101"), ("B", "20170101", "20210101"), ("C", "20210101", "20991231"))


def sigma(p, n=60):
    r = np.concatenate([[np.nan], p[1:] / p[:-1] - 1])
    out = np.full(len(p), np.nan)
    for i in range(n, len(p)):
        w = r[i - n + 1:i + 1]
        out[i] = np.nanstd(w)
    return out


def show(tag, sig, code, st, tk, days, cool=0):
    tr, dd = I.sim(sig, code, st, tk, days, cool=cool)
    cells = []
    for p, lo, hi in PER:
        s = I.stats(dd, lo, hi)
        n = sum(1 for a, b, _ in tr if lo <= I.DAYS[a] < hi)
        cells.append(f"{p} {s[0]:+5.1f} · {s[1]:6.1f} ({n}건)" if s else f"{p} -")
    print(f"  {tag:26s} 신호 날 {int(np.nansum(sig))} | " + " | ".join(cells), flush=True)



# (사용자 "한 번에 실패라 하지 말고 DNA만큼 연구") — 고르기는 B(2017 ~ 2020), 시험은 A(안 본 앞) · C(뒤)
def pct_hist(x, q, start=250):
    """그날까지의 지난 값(자기 기록)에서 아래 q 자리(미래 참조 없음)."""
    out = np.full(len(x), np.nan)
    srt = []
    import bisect
    for i in range(len(x)):
        if i >= start and srt:
            out[i] = srt[min(len(srt) - 1, int(len(srt) * q))]
        if np.isfinite(x[i]):
            bisect.insort(srt, x[i])
    return out


def sim_rna(sig, code, p, sg, c_tk, c_st, days, cool=0):
    """익절 · 손절도 RNA: 산 날의 σ × √days × c (그날까지 값)."""
    px = I.px(code)
    daily = np.zeros(len(I.DAYS))
    trades, i, n = [], 0, len(I.DAYS)
    while i < n - 1:
        if not sig[i] or np.isnan(px[i]) or not np.isfinite(sg[i]):
            i += 1
            continue
        tk, st = c_tk * sg[i] * np.sqrt(days), -c_st * sg[i] * np.sqrt(days)
        p0 = px[i]
        daily[i] -= 0.001
        j = i + 1
        while j < n:
            if np.isnan(px[j]):
                j += 1
                continue
            daily[j] += px[j] / px[j - 1] - 1 if not np.isnan(px[j - 1]) else 0
            r = px[j] / p0 - 1
            if r <= st or r >= tk or j - i >= days:
                break
            j += 1
        j = min(j, n - 1)
        daily[j] -= 0.001
        trades.append((i, j, px[j] / p0 - 1))
        i = j + 1 + (cool if px[j] / p0 - 1 <= st else 0)
    return trades, daily


def show2(tag, tr, dd):
    cells = []
    for p_, lo, hi in PER:
        s = I.stats(dd, lo, hi)
        nn = sum(1 for a, b, _ in tr if lo <= I.DAYS[a] < hi)
        cells.append(f"{p_} {s[0]:+5.1f} · {s[1]:6.1f} ({nn}건)" if s else f"{p_} -")
    print(f"  {tag:30s} | " + " | ".join(cells), flush=True)



k = I.K200
r5 = np.nan_to_num(I.ret(k, 5), nan=0)
r5raw = I.ret(k, 5)
print("== 고원 · 급락 되돌림 자기 기록 아래 q ==")
show("DNA 5일 ≤ −5%", r5 <= -0.05, "069500", -0.03, 0.03, 20, 20)
for qq in (0.025, 0.03, 0.035, 0.04):
    c = pct_hist(r5raw, qq)
    show(f"자기 기록 아래 {qq * 100:.1f}%", np.nan_to_num(r5raw <= c, nan=0).astype(bool), "069500", -0.03, 0.03, 20, 20)
q = I.px("229200")
sq = sigma(q)
r10 = np.nan_to_num(I.ret(q, 10), nan=0)
print("== 고원 · 코스닥 인버스 RNA 익절손절 c ==")
show("DNA ±1.5%", r10 >= 0.10, "251340", -0.015, 0.015, 10)
for c in (0.2, 0.25, 0.3, 0.35):
    tr, dd = sim_rna(r10 >= 0.10, "251340", q, np.nan_to_num(sq, nan=np.nan), c, c, 10)
    show2(f"RNA 익절손절 {c}σ√10", tr, dd)
