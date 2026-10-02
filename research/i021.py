"""I 23회차 — 인버스 더 찾기(I22 코스닥 과열 인버스에서 이어서).
판(그날 종가 판단 → 그날 종가에 인버스 · 손절 뒤 쉬기 0 · 10):
  Q1 코스닥 10일 +10% 또는 5일 +6.5%(두 신호 합침) → 251340
  Q2 코스닥 10일 +10% · 시장 폭 ≥ 50(1일봉이 들어가 있는 과열) → 251340  / Q3 같은데 시장 폭 < 50
  Q4 코스닥 10일 +10% → 코스피 인버스 114800(코스닥 과열이 코스피도 끌어내리나)
  Q5 코스닥이 코스피보다 10일 +6% 넘게 앞섬(코스닥만 과열) → 251340
  Q6 코스닥 10일 +10% 그리고 오늘 코스닥 −(첫 꺾임 날) → 251340
  Q7 코스닥 20일 +15% · 20일선보다 +10% 위 → 251340
나오는 법: 익절 1.5 · 2 · 3 × 손절 1.5 · 2 · 3 × 5 · 10 · 20일 × 쉬기 0 · 10. 기간 B · C1 · C2(2026) 모두 + · 골 −15 안."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

q, k = I.px("229200"), I.K200
I.px("251340")
rq = {n: np.nan_to_num(I.ret(q, n), nan=0) for n in (1, 5, 10, 20)}
rk10 = np.nan_to_num(I.ret(k, 10), nan=0)
mq20 = I.ma(np.nan_to_num(q, nan=0), 20)
br = np.nan_to_num(I.breadth(), nan=-1)
base = rq[10] >= 0.10
SIG = {
    "Q1 10일 +10% 또는 5일 +6.5%": (base | (rq[5] >= 0.065), "251340"),
    "Q2 10일 +10% · 시장 폭 ≥ 50": (base & (br >= 50), "251340"),
    "Q3 10일 +10% · 시장 폭 < 50": (base & (br >= 0) & (br < 50), "251340"),
    "Q4 코스닥 10일 +10% → 코스피 인버스": (base, "114800"),
    "Q5 코스닥이 코스피보다 10일 +6% 앞섬": (rq[10] - rk10 >= 0.06, "251340"),
    "Q6 10일 +10% · 오늘 코스닥 −": (np.concatenate([[False], base[:-1]]) & (rq[1] < 0), "251340"),
    "Q7 20일 +15% · 20일선 +10% 위": ((rq[20] >= 0.15) & (np.nan_to_num(q / mq20 - 1, nan=0) >= 0.10), "251340"),
}
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
print("== I 23회차: 인버스 더 찾기 ==", flush=True)
for name, (sig, code) in SIG.items():
    rows = []
    for take in (0.015, 0.02, 0.03):
        for stop in (-0.015, -0.02, -0.03):
            for maxd in (5, 10, 20):
                for cool in (0, 10):
                    tr, d = I.sim(sig, code, stop, take, maxd, cool=cool)
                    js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER]
                    ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                    rows.append((ok, min(j["cagr"] for j in js), f"익절 {take*100:.1f} 손절 {stop*100:.1f} {maxd}일 쉬기 {cool}",
                                 " | ".join(f"{nm} {j['n']}건 이김 {j['win']:.0f} 연 {j['cagr']:+.1f} 골 {j['dd']:.1f}" for (nm, _, _), j in zip(PER, js))))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    print(f"[{name}] 신호 날 {int(sig.sum())} · 합격 {sum(x[0] for x in rows)}/{len(rows)} · 맨 위 {rows[0][2]} (가장 나쁜 {rows[0][1]:+.1f}) {rows[0][3]}", flush=True)
print("끝", flush=True)
