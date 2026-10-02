"""I 4회차(I3) — 급락 되돌림에 '진짜 하락 vs 흔들림' 거르기를 붙임(2017 ~ 자료 · B · C 기간만).
바탕: KODEX 200 5일 급락(I_TH, 기본 −5%) → 익절 · 손절 · 20일(I_TAKE · I_STOP · 기본 4 · −4).
거르기(그날까지 알려진 것만):
  시장 폭(시총 100위 안 50 > 200일선 몫): 30 넘음 · 20 넘음 / 아래
  시장 외국인 5일 순매수(코스피 · 금액): + / −  · 기관 5일: + / −  · 개인 5일: + / −
  프로그램 비차익 5일: + / −
  신용융자잔고 20일 변화: 늘어남(빚 쌓임 → 더 빠질 수 있음) / 줄어듦(빚 정리됨 → 바닥 가까움)
  고객예탁금 20일 변화: 늘어남 / 줄어듦
잣대: B · C 모두 연 + · 골 −15% 안, 거르기 전보다 골이 얕아지고 연 수익이 크게 줄지 않아야."""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

TH = float(os.environ.get("I_TH", "-0.05"))
TAKE = float(os.environ.get("I_TAKE", "0.04"))
STOP = float(os.environ.get("I_STOP", "-0.04"))
k = I.K200
base = np.nan_to_num(I.ret(k, 5), nan=0) <= TH
br = I.breadth()


def roll_sum(a, n):
    """그날 포함 n거래일 합(빈 날이 하루 넘게 있으면 nan)."""
    out = np.full(len(a), np.nan)
    for i in range(n - 1, len(a)):
        w = a[i - n + 1:i + 1]
        out[i] = np.nansum(w) if np.isfinite(w).sum() >= n - 1 else np.nan
    return out


def change(a, n):
    out = np.full(len(a), np.nan)
    out[n:] = a[n:] / a[:-n] - 1
    return out


fr = I.series("market-data/investor_KSP.json", "외국인")
inst = I.series("market-data/investor_KSP.json", "기관")
indiv = I.series("market-data/investor_KSP.json", "개인")
prog = I.series("market-data/program_K.json", "비차익순매수")
credit = I.series("market-data/funds.json", "신용융자잔고")
deposit = I.series("market-data/funds.json", "고객예탁금")
F5, I5, P5, G5 = (roll_sum(x, 5) for x in (fr, inst, indiv, prog))
C20, D20 = change(credit, 20), change(deposit, 20)
pos = lambda a: np.nan_to_num(a, nan=0) > 0
neg = lambda a: np.nan_to_num(a, nan=0) < 0
FILTERS = {
    "거르기 없음": np.ones(len(k), bool),
    "시장 폭 > 30": np.nan_to_num(br, nan=0) > 30,
    "시장 폭 > 20": np.nan_to_num(br, nan=0) > 20,
    "시장 폭 ≤ 30": (np.nan_to_num(br, nan=99) <= 30),
    "외국인 5일 +": pos(F5), "외국인 5일 −": neg(F5),
    "기관 5일 +": pos(I5), "기관 5일 −": neg(I5),
    "개인 5일 +": pos(P5), "개인 5일 −": neg(P5),
    "프로그램 비차익 5일 +": pos(G5), "프로그램 비차익 5일 −": neg(G5),
    "신용융자 20일 줄어듦": neg(C20), "신용융자 20일 늘어남": pos(C20),
    "고객예탁금 20일 늘어남": pos(D20), "고객예탁금 20일 줄어듦": neg(D20),
}
PER = I.PERIODS[1:]
print(f"== I 4회차(I3): 급락 되돌림 + 거르기 · 5일 {TH*100:.0f}% · 익절 {TAKE*100:.0f} · 손절 {STOP*100:.0f} · 20일 (B · C) ==", flush=True)
for name, f in FILTERS.items():
    for cool in (0, 20):
        tr, d = I.sim(base & f, "069500", STOP, TAKE, 20, cool=cool)
        text, worst = I.line(f"{name} · 쉬기 {cool}", tr, d, PER)
        print(text, flush=True)
print("끝", flush=True)
