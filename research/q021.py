"""15분봉 20회차 — 정배열 신호(15분봉 EMA가 정배열이 된 봉)도 '신호 하나하나'로 봄: 시각대별 · 장중 시장 흐름별 · 오늘 수익별 평균.
18회차와 같은 혼자 사기 셈(다음 봉 시가 · 파는 규칙대로 · 비용 0.30%). 161종목."""
import sys
import statistics
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q019.py", encoding="utf-8").read().split('al_cache = ')[0])

rows = []
for c, b in data.items():
    base = entry(noon="1045")(c, b)
    al = e_align(c, b)
    for k in np.flatnonzero(base & al):
        t = b["t"][k]
        side = next((n for n, (lo, hi) in PER if lo <= t < hi), None)
        if side is None:
            continue
        r = solo(c, k)
        if r is not None:
            rows.append((side, r, HH[c][k], nan0(DR[c])[k], nan0(MKT[c])[k]))


def show(tag, L):
    if not L:
        print(f"    {tag}: 없음")
        return
    L = sorted(L)
    cut = L[:-1] if len(L) > 3 else L
    print(f"    {tag}: 평균 {sum(L) / len(L):+.2f}% · 가운데 {statistics.median(L):+.2f}% · 큰 1건 뺀 {sum(cut) / len(cut):+.2f}% · 이김 {sum(x > 0 for x in L) / len(L) * 100:.0f}% ({len(L)}건)")


print(f"== 15분봉 20회차: 정배열 신호 하나하나 ({len(data)}종목 · {len(rows)}건) ==", flush=True)
for side in ("앞", "뒤"):
    R = [r for r in rows if r[0] == side]
    print(f"  {side}")
    show("모두", [r[1] for r in R])
    for lo, hi, name in (("0900", "0930", "09:00 ~ 09:15 봉"), ("0930", "1045", "09:30 ~ 10:30 봉"), ("1045", "1600", "10:45 봉 뒤")):
        show(name, [r[1] for r in R if lo <= r[2] < hi])
    show("시장 −1% 아래", [r[1] for r in R if r[4] < -0.01])
    show("시장 −1% 이상", [r[1] for r in R if r[4] >= -0.01])
    show("오늘 +2% 위", [r[1] for r in R if r[3] > 0.02])
    show("오늘 +2% 이하", [r[1] for r in R if r[3] <= 0.02])
print("끝", flush=True)
