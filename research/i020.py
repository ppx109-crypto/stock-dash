"""I 22회차 — 코스닥 과열 뒤 코스닥150 인버스(251340) 다듬기(I20에서 처음 합격한 인버스).
신호: 코스닥150(229200) 10일 수익 ≥ X(8 ~ 13%) 또는 5일 ≥ Y(5 ~ 7%) · 그날 종가에 251340.
나오는 법: 익절 1.5 · 2 · 3 × 손절 1.5 · 2 · 3 × 5 · 10 · 20일 × 손절 뒤 쉬기 0 · 10 · 20. 비용 0.2 · 0.4%.
기간: B(2017 ~ 2020) · C1(2021 ~ 2025) · C2(2026) — 셋 모두 연 + · 골 −15 안이면 합격. 고원: 이웃 판 합격 몫."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

q = I.px("229200")
I.px("251340")
r5, r10 = np.nan_to_num(I.ret(q, 5), nan=0), np.nan_to_num(I.ret(q, 10), nan=0)
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
SIG = {f"10일 +{x}%": r10 >= x / 100 for x in (8, 9, 10, 11, 12, 13)}
SIG.update({f"5일 +{y}%": r5 >= y / 100 for y in (5, 5.5, 6, 6.5, 7)})
print("== I 22회차: 코스닥 과열 뒤 코스닥150 인버스 다듬기 ==", flush=True)
for cost in (0.002, 0.004):
    print(f"\n######## 비용 {cost*100:.1f}% ########", flush=True)
    for name, sig in SIG.items():
        rows = []
        for take in (0.015, 0.02, 0.03):
            for stop in (-0.015, -0.02, -0.03):
                for maxd in (5, 10, 20):
                    for cool in (0, 10, 20):
                        tr, d = I.sim(sig, "251340", stop, take, maxd, cost=cost, cool=cool)
                        js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER]
                        ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                        rows.append((ok, min(j["cagr"] for j in js), f"익절 {take*100:.1f} 손절 {stop*100:.1f} {maxd}일 쉬기 {cool}",
                                     " | ".join(f"{nm} {j['n']}건 이김 {j['win']:.0f} 연 {j['cagr']:+.1f} 골 {j['dd']:.1f}" for (nm, _, _), j in zip(PER, js))))
        rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
        print(f"[{name}] 신호 날 {int(sig.sum())} · 합격 {sum(x[0] for x in rows)}/{len(rows)} · 맨 위 {rows[0][2]} (가장 나쁜 {rows[0][1]:+.1f}) {rows[0][3]}", flush=True)
print("끝", flush=True)
