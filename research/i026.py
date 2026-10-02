"""I 31 ~ 33회차 — 새 생각 셋(할 일 줄이 비어 넣음).
I31 달력: 코스닥 연말 약세(개인 대주주 양도세 피하는 12월 매도) → 12월 N번째 ~ 끝에서 M번째 거래일 코스닥150 인버스(251340) / 1월 효과 → 1월 처음 K일 코스닥150(229200).
    해마다 따로 보이고(2016 ~ 2025), 창을 앞뒤로 밀어 고원 확인. 견줌: 같은 창의 코스피 인버스(114800).
I32 코스닥 과열 인버스(I22) 나오는 법 바꾸기: 고정 익절 1.5 대신 '코스닥150 종가 < 5일선이면 다음 날 판 · 손절 −2 · 20일' 등.
I33 옵션 만기 주(매달 둘째 목요일이 든 주): 월요일 종가 → 목요일 종가 인버스 · 지수(114800 · 069500) 해마다 + 몫."""
import sys
from datetime import date

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D, n = I.DAYS, len(I.DAYS)
P = {c: I.px(c) for c in ("251340", "229200", "114800", "069500")}


def hold(code, a, b):
    p = P[code]
    return p[b] / p[a] - 1 if not (np.isnan(p[a]) or np.isnan(p[b])) else np.nan


print("== I 31회차: 코스닥 연말 약세 · 1월 효과 ==", flush=True)
years = range(2016, 2026)
dec = {y: [i for i, d in enumerate(D) if d.startswith(f"{y}12")] for y in years}
jan = {y: [i for i, d in enumerate(D) if d.startswith(f"{y + 1}01")] for y in years}
for start in (0, 5, 10, 14):                  # 12월 몇 번째 거래일 종가에 삼(0 = 11월 마지막 날 종가)
    for end_back in (1, 2, 3):                 # 12월 끝에서 몇 번째 거래일 종가에 팖
        for code in ("251340", "114800"):
            rs = []
            for y in years:
                idx = dec[y]
                if len(idx) < 15:
                    continue
                a = idx[0] - 1 if start == 0 else idx[start - 1]
                b = idx[-end_back]
                r = hold(code, a, b)
                if np.isfinite(r):
                    rs.append(r - 0.002)
            if rs:
                rs = np.array(rs)
                print(f"  12월 {start}번째 → 끝에서 {end_back}번째 · {code}: {len(rs)}해 평균 {rs.mean()*100:+.2f}% · + 인 해 {np.mean(rs > 0)*100:.0f}% · 가장 나쁜 {rs.min()*100:+.1f}%", flush=True)
for k in (3, 5, 10, 20):
    rs = []
    for y in years:
        idx = jan[y]
        if len(idx) < k or not dec[y]:
            continue
        r = hold("229200", dec[y][-1], idx[k - 1])
        if np.isfinite(r):
            rs.append(r - 0.002)
    rs = np.array(rs)
    print(f"  1월 처음 {k}일 코스닥150: {len(rs)}해 평균 {rs.mean()*100:+.2f}% · + 인 해 {np.mean(rs > 0)*100:.0f}% · 가장 나쁜 {rs.min()*100:+.1f}%", flush=True)
yr = []
for y in years:
    idx = dec[y]
    if len(idx) >= 15:
        yr.append(f"{y} {hold('251340', idx[0] - 1, idx[-2]) * 100:+.1f}")
print("  해마다(12월 처음 → 끝에서 2번째 · 코스닥 인버스): " + " · ".join(yr), flush=True)

print("\n== I 32회차: 코스닥 과열 인버스 나오는 법 ==", flush=True)
q = P["229200"]
q10 = np.nan_to_num(I.ret(q, 10), nan=0) >= 0.10
m5 = I.ma(np.nan_to_num(q, nan=0), 5)
under5 = np.nan_to_num(q < m5, nan=0) > 0
over5 = np.nan_to_num(q > m5, nan=0) > 0
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
for tag, kw in (("익절 1.5 · 손절 1.5 · 10일(I22)", dict(stop=-0.015, take=0.015, maxd=10)),
                ("코스닥 < 5일선이면 · 손절 2 · 20일", dict(stop=-0.02, take=0.5, maxd=20, exit_sig=None)),
                ("코스닥 > 5일선(다시 오르면) 나옴 · 손절 2 · 20일", dict(stop=-0.02, take=0.5, maxd=20, exit_sig=over5)),
                ("익절 3 · 손절 1.5 · 코스닥 > 5일선이면 나옴", dict(stop=-0.015, take=0.03, maxd=20, exit_sig=over5)),
                ("익절 5 · 손절 2 · 20일", dict(stop=-0.02, take=0.05, maxd=20))):
    if "< 5일선이면" in tag:
        # 오르는 쪽(인버스 이익)에서 코스닥이 5일선 아래로 꺾이면 이익 챙김 → 인버스 기준 '익절 신호'
        kw["exit_sig"] = under5
    tr, d = I.sim(q10, "251340", **kw)
    print(I.line(tag, tr, d, PER)[0], flush=True)

print("\n== I 33회차: 옵션 만기 주(둘째 목요일) 월 → 목 ==", flush=True)
dd = [date(int(x[:4]), int(x[4:6]), int(x[6:])) for x in D]
for code in ("114800", "069500"):
    rs, yrs = [], {}
    for i, x in enumerate(dd):
        if x.weekday() == 3 and 8 <= x.day <= 14:          # 둘째 목요일
            mon = [j for j in range(max(0, i - 4), i) if dd[j].isocalendar()[:2] == x.isocalendar()[:2]]
            if not mon:
                continue
            a = mon[0] - 1                                    # 그 주 첫 거래일 앞 종가
            r = hold(code, a, i)
            if np.isfinite(r):
                rs.append(r - 0.002)
                yrs.setdefault(x.year, []).append(r)
    rs = np.array(rs)
    print(f"  {code}: {len(rs)}번 평균 {rs.mean()*100:+.2f}% · + 인 몫 {np.mean(rs > 0)*100:.0f}% · 해마다 합 + 인 해 {np.mean([sum(v) > 0 for v in yrs.values()])*100:.0f}%", flush=True)
print("끝", flush=True)
