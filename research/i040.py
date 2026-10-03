"""I 7라운드 ① — 빈칸 엔진 전체(급락 되돌림 → 하락 추세 달러 → 돌리기)를 안 본 기간 A(2012 ~ 2016)에서 다시.
1일봉 장부 없이 '계좌 전부가 비었다'고 보고 엔진만 돌림(A엔 시장 폭 · 1일봉 장부가 없어 시장 폭 거르기 없이).
달마다 코스피 국면(내림 −2% 아래 · 오름 +2% 위 · 그 밖 옆걸음)별 평균도 냄. 미래 참조: 신호는 그날 종가까지 · 돌리기는 주 끝에 고름 · 달러는 하루 밀어 씀."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import i011 as R
import itools as I

D, n = I.DAYS, len(I.DAYS)
k = I.K200
COST = 0.002
CANDS = ["133690", "138230", "132030", "148070"]
PER = (("A 2012~16", "20120101", "20170101"), ("B 2017~20", "20170101", "20210101"), ("C 2021~", "20210101", "20991231"))


def shift(a):
    return np.concatenate([[False], a[:-1]])


rot = R.run(R.G["언제나"], R.momentum(20, 2, CANDS), COST)
dip_sig = np.nan_to_num(I.ret(k, 5), nan=0) <= -0.05
tr, dd = I.sim(dip_sig, "069500", -0.03, 0.03, 20, cool=20, cost=COST)
dip_on = np.zeros(n, bool)
for a, b, _ in tr:
    dip_on[a + 1:b + 1] = True
dol = I.px("138230")
d20 = np.nan_to_num(dol / np.concatenate([np.full(20, np.nan), dol[:-20]]) - 1, nan=0)
cond = (d20 > 0.02) & (np.nan_to_num(k < I.ma(k, 20), nan=0) > 0)
dol_on = shift(cond) & ~dip_on
dret = np.concatenate([[0.0], dol[1:] / dol[:-1] - 1])
dret = np.nan_to_num(dret)
turn = np.abs(np.diff(np.concatenate([[0], dol_on.astype(float)])))
dol_d = np.where(dol_on, dret, 0.0) - turn * COST / 2
eng = np.where(dip_on, dd, np.where(dol_on, dol_d, rot))
for a, b, _ in tr:                    # 급락 되돌림 사는 날 비용
    eng[a] += dd[a]

parts = {"급락 되돌림만": dd, "하락 추세 달러만": dol_d, "돌리기만": rot, "엔진 전체": eng, "코스피200 들고 있기": np.nan_to_num(np.concatenate([[0.0], k[1:] / k[:-1] - 1]))}
print("== I 7라운드 ①: 빈칸 엔진을 안 본 기간까지(계좌 전부 · 연 · 골) ==")
for nm, x in parts.items():
    print(f"  {nm:16s} " + " | ".join(f"{p} {I.stats(x, lo, hi)[0]:+5.1f} · {I.stats(x, lo, hi)[1]:6.1f}" for p, lo, hi in PER))

print("\n== 달마다 코스피 국면별 엔진 평균(%) ==")
months = sorted(set(d[:6] for d in D if d >= "20120101"))
for p, lo, hi in PER:
    rows = {"내림": [], "옆걸음": [], "오름": []}
    for m in months:
        if not (lo[:6] <= m < hi[:6]):
            continue
        idx = np.array([d[:6] == m for d in D])
        km = np.prod(1 + parts["코스피200 들고 있기"][idx]) - 1
        em = np.prod(1 + eng[idx]) - 1
        rows["내림" if km < -0.02 else "오름" if km > 0.02 else "옆걸음"].append(em * 100)
    print(f"  {p}: " + " · ".join(f"{g} {np.mean(v):+.2f}({len(v)}달 · 이긴 달 {np.mean(np.array(v) > 0) * 100:.0f}%)" for g, v in rows.items() if v))

print("\n== 하락 추세 달러 단계를 빼면(급락 → 돌리기만) · 달러 문턱 이웃 ==")
nodol = np.where(dip_on, dd, rot)
for a, b, _ in tr:
    nodol[a] += dd[a]
print(f"  {'달러 빼기':16s} " + " | ".join(f"{p} {I.stats(nodol, lo, hi)[0]:+5.1f} · {I.stats(nodol, lo, hi)[1]:6.1f}" for p, lo, hi in PER))
for th in (0.01, 0.03):
    c2 = (d20 > th) & (np.nan_to_num(k < I.ma(k, 20), nan=0) > 0)
    on2 = shift(c2) & ~dip_on
    t2 = np.abs(np.diff(np.concatenate([[0], on2.astype(float)])))
    e2 = np.where(dip_on, dd, np.where(on2, np.where(on2, dret, 0.0) - t2 * COST / 2, rot))
    for a, b, _ in tr:
        e2[a] += dd[a]
    print(f"  {'달러 문턱 %+.0f%%' % (th * 100):16s} " + " | ".join(f"{p} {I.stats(e2, lo, hi)[0]:+5.1f} · {I.stats(e2, lo, hi)[1]:6.1f}" for p, lo, hi in PER))
