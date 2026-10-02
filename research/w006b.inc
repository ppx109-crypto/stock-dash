# Q_PART=2: D의 숫자 고원 + '1일봉 계좌는 그대로 · 빈 현금 일부로 인버스'(얹기) 판.
def Dsig(a, b, n, k):
    return (M[a] < M[b]) & ~np.isnan(M[b]) & (cl < M[n]) & (br < k)


for a, b, n, k in ((20, 60, 20, 40), (20, 60, 20, 35), (20, 60, 20, 45), (10, 60, 20, 40), (20, 120, 20, 40), (20, 60, 10, 40), (20, 60, 60, 40)):
    sig = Dsig(a, b, n, k)
    for cost in (0.1, 0.5):
        mine, flips = sim(sig, cost)
        out = [f"  D 고원 {a}<{b} · 지수<{n} · 폭<{k} 비용 {cost}"]
        for side, lo, hi in (("앞", "20170101", MID), ("뒤", MID, "20991231")):
            t = stats(mine, lo, hi)
            out.append(f"| {side} 합 {t[0]:+5.1f} 연 {t[1]:+4.1f} 골 {t[2]:5.1f}")
        print(" ".join(out) + f" | 갈아탐 {flips}", flush=True)
sig = Dsig(20, 60, 20, 40)
for cost in (0.1, 0.5):
    mine, _ = sim(sig, cost)
    for wgt in (0.0, 0.2, 0.3, 0.5):
        both = {x: base.get(x, 0) + wgt * mine.get(x, 0) for x in set(base) | set(mine)}
        out = [f"  얹기 1일봉 + 인버스 {int(wgt * 100)}% 비용 {cost}"]
        for side, lo, hi in (("앞", "20170101", MID), ("뒤", MID, "20991231")):
            t = stats(both, lo, hi)
            out.append(f"| {side} 합 {t[0]:+6.1f} 연 {t[1]:+5.1f} 골 {t[2]:5.1f} 나쁜 주 {t[3]:5.1f}")
        print(" ".join(out), flush=True)
print("끝", flush=True)
