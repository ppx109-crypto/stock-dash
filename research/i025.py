"""I 29 · 30회차.
I29: 코스닥150 10일 +10% 급등(I22) + 원화 강세(KOSEF 미국달러선물 138230 20일 −1 · −2%) / 원화 약세일 때 코스닥150 인버스 — 54판.
I30: 코스닥 급등 날 인버스 사는 시각(etf-m15 229200 · 약 1년). 판단 시각 T(11:00 · 13:00 · 14:00 · 15:15) 값 / 10거래일 앞 종가 − 1 ≥ 10%이면 그 시각에 삼.
  251340 장중 값이 없어 '그날 인버스 값 = 어제 인버스 종가 × (1 − (T 값 / 어제 코스닥150 종가 − 1))'로 어림(하루 안 −1배). 그 뒤는 종가로 익절 1.5 · 손절 1.5 · 10일."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D, n = I.DAYS, len(I.DAYS)
q, inv = I.px("229200"), I.px("251340")
q10 = np.nan_to_num(I.ret(q, 10), nan=0) >= 0.10
dol = I.px("138230")
d20 = np.nan_to_num(dol / np.concatenate([np.full(20, np.nan), dol[:-20]]) - 1, nan=0)
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
print("== I 29회차: 코스닥 급등 + 원화 강세 · 약세 ==", flush=True)
for name, sig in (("I22 단독", q10), ("I22 · 달러 20일 −1%(원화 강세)", q10 & (d20 <= -0.01)), ("I22 · 달러 20일 −2%", q10 & (d20 <= -0.02)),
                  ("I22 · 달러 20일 +(원화 약세)", q10 & (d20 > 0)), ("I22 · 달러 20일 +1%", q10 & (d20 >= 0.01))):
    rows = []
    for take in (0.015, 0.02, 0.03):
        for stop in (-0.015, -0.02, -0.03):
            for maxd in (5, 10, 20):
                for cool in (0, 10):
                    tr, d = I.sim(sig, "251340", stop, take, maxd, cool=cool)
                    js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER]
                    ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                    rows.append((ok, min(j["cagr"] for j in js), f"익절 {take*100:.1f} 손절 {stop*100:.1f} {maxd}일 쉬기 {cool}",
                                 " | ".join(f"{nm} {j['n']}건 연 {j['cagr']:+.1f} 골 {j['dd']:.1f}" for (nm, _, _), j in zip(PER, js))))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    print(f"[{name}] 신호 날 {int(sig.sum())} · 합격 {sum(x[0] for x in rows)}/54 · 맨 위 {rows[0][2]} (가장 나쁜 {rows[0][1]:+.1f}) {rows[0][3]}", flush=True)

print("\n== I 30회차: 코스닥 급등 날 인버스 사는 시각(15분봉 1년) ==", flush=True)
bars = {}
for f in sorted(Path("/home/user/stock-dash/etf-m15/229200").glob("*.csv")):
    for line in f.read_text().splitlines():
        t, o, h, l, c, v = line.split(",")[:6]
        bars.setdefault(t[:8], {})[t[8:]] = float(c)
have = np.array([d in bars for d in D])
lo = D[int(np.argmax(have))]
back10 = np.concatenate([np.full(10, np.nan), q[:-10]])
qy, iy = np.concatenate([[np.nan], q[:-1]]), np.concatenate([[np.nan], inv[:-1]])


def sim_at(entry, buy_px, stop=-0.015, take=0.015, maxd=10, cost=0.002):
    daily, trades, i = np.zeros(n), [], 0
    while i < n - 1:
        if not entry[i] or np.isnan(buy_px[i]):
            i += 1
            continue
        p0 = buy_px[i]
        daily[i] += inv[i] / p0 - 1 - cost / 2
        j = i + 1
        while j < n:
            daily[j] += inv[j] / inv[j - 1] - 1
            r = inv[j] / p0 - 1
            if r <= stop or r >= take or j - i >= maxd:
                break
            j += 1
        j = min(j, n - 1)
        daily[j] -= cost / 2
        trades.append((i, j, inv[j] / p0 - 1 - cost))
        i = j + 1
    return trades, daily


print(f"  기간 {lo} ~ ({int(have.sum())}일)", flush=True)
for slot in ("1045", "1245", "1345", "1500"):        # 그 칸 종가 = 11:00 · 13:00 · 14:00 · 15:15에 아는 값
    qt = np.array([bars.get(d, {}).get(slot, np.nan) for d in D])
    sig = np.nan_to_num(qt / back10 - 1, nan=0) >= 0.10
    buy = iy * (1 - (qt / qy - 1))
    tr, d = sim_at(sig & have, buy)
    print(I.line(f"{int(slot[:2]) + (1 if slot[2:] == '45' else 0)}:{'00' if slot[2:] == '45' else '15'} 판단 → 그 시각에 삼(신호 {int((sig & have).sum())}날)", tr, d, (("1년", lo, "20991231"),))[0], flush=True)
tr, d = I.sim(q10 & have, "251340", -0.015, 0.015, 10)
print(I.line(f"종가 판단 → 종가(신호 {int((q10 & have).sum())}날)", tr, d, (("1년", lo, "20991231"),))[0], flush=True)
print("끝", flush=True)
