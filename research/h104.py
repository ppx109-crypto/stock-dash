"""1시간봉 104회차 — 15분봉 후보의 다른 축 '정오(12:00) 대신 11:00에 사기'를 1시간봉 긴 자료에서 신호 하나하나로:
정오 사기 신호(11시 봉 뒤 · 그날 정배열 신호 없음)마다 같은 날 10시 봉 뒤(11:00 시가)에 샀을 때와 11시 봉 뒤(12:00 시가)에 샀을 때 손익을 견줌. 해마다."""
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("research/h103.py", encoding="utf-8").read().split('rows = []')[0])

rows = []
for c, b in data.items():
    if c.startswith("K"):
        continue
    m = entry_f()(c, b)
    al = e_align(c, b)
    hrs = [t[8:10] for t in b["t"]]
    for k in np.flatnonzero(m):
        t = b["t"][k]
        if al[k] or hrs[k] != "11" or not ("2023100100" <= t < "2026093000"):
            continue
        j = k - 1
        if j < 0 or b["t"][j][:8] != t[:8] or hrs[j] != "10":
            continue
        a, z = solo(c, j), solo(c, k)
        if a is not None and z is not None:
            rows.append((t[:4], a, z, t < "2025040100"))
print(f"== 1시간봉 104회차: 정오 사기를 11:00로 당기면 (같은 신호 {len(rows)}건) ==", flush=True)
for name, sel in (("앞", lambda r: r[3]), ("뒤", lambda r: not r[3]), ("2024", lambda r: r[0] == "2024"), ("2025", lambda r: r[0] == "2025"), ("2026", lambda r: r[0] == "2026")):
    R = [r for r in rows if sel(r)]
    if not R:
        continue
    d = [r[1] - r[2] for r in R]
    print(f"  {name}: 11:00 평균 {statistics.mean(r[1] for r in R):+.2f} · 12:00 평균 {statistics.mean(r[2] for r in R):+.2f} · 차이 가운데 {statistics.median(d):+.2f} · 11:00이 나은 몫 {sum(x > 0 for x in d) / len(d) * 100:.0f}% ({len(R)}건)")
print("끝", flush=True)
