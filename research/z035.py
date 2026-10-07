"""B11b — '실제 계좌(날마다 평가)로 한 달 −15% 안' 판 찾기(사용자 2026-10-07 "머리는 판 날 기준인데 심리적으로는 −15% 넘으면 힘들 것 같아").
도구: research/m_eval.py(1일봉 장부 · 날마다 평가 · 실제 비용 · 덧씌우기 판단은 그날 종가까지 · 실행은 다음 거래일 종가).
판(미리 정함 · 숫자 고르기 안 함): 바탕 · SZ80 · SZ70 · SZ60(크기 × 0.8 · 0.7 · 0.6) · MS10 · MS12(그달 −10 · −12%면 다 팔고 그달 쉼) · WC30 · WC25(한 종목 몫 덮개) · 둘씩.
기간: 고르기 17 ~ 22 · 시험 23 ~ 25 · 2026(1 ~ 10월). 칸: 연 · 골(날마다) · 가장 나쁜 하루 · 가장 나쁜 달 · −15% 넘은 달 수.
M_SHOW_TEST=1 M_OPEN2026=1 python research/z035.py
"""
import os
import sys

os.environ.setdefault("M_SHOW_TEST", "1")
os.environ.setdefault("M_OPEN2026", "1")
sys.path.insert(0, "/home/user/stock-dash/research")
import numpy as np  # noqa: E402
import m_eval as M  # noqa: E402

DESIGNS = ["", "SZ80", "SZ70", "SZ60", "MS10", "MS12", "WC30", "WC25", "MS12+WC30", "SZ80+MS12", "SZ80+WC30"]


def row(E, lo, hi):
    D = M.D
    ii = np.flatnonzero(np.array([lo <= d < hi for d in D]))
    a, b = max(ii[0], 1), ii[-1]
    r = E[a:b + 1] / E[a - 1:b] - 1
    months = {}
    for i in range(a, b + 1):
        months.setdefault(D[i][:6], []).append(i)
    mr = np.array([E[v[-1]] / E[v[0] - 1] - 1 for v in months.values()]) * 100
    ann = ((E[b] / E[a - 1]) ** (250 / (b - a + 1)) - 1) * 100
    q = E[a - 1:b + 1] / E[a - 1]
    dd = (q / np.maximum.accumulate(q) - 1).min() * 100
    return f"연 {ann:+6.1f} · 골 {dd:6.1f} · 하루 {r.min() * 100:5.1f} · 달 {mr.min():6.1f} · −15%↓ {int((mr < -15).sum())}달"


if __name__ == "__main__":
    print("판 | " + " | ".join(n for n, *_ in M.PERIODS), flush=True)
    for design in DESIGNS:
        E, C = M.sim(design)
        print(f"{design or '바탕':12s} | " + " | ".join(row(E, lo, hi) for _, lo, hi in M.PERIODS), flush=True)
