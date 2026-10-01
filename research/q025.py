"""15분봉 24회차 — 최종 후보의 '신호 하나하나' 평가: 0회차 사는 신호(정배열 · 정오) 가운데 최종 후보 거르기에 막힌 것 vs 남은 것,
그리고 최종 후보의 신호(10:45 사기 포함) 전체. 혼자 산 것으로 보고 파는 규칙대로 · 비용 0.30%. 161종목."""
import sys
import statistics
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q019.py", encoding="utf-8").read().split('al_cache = ')[0])
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('part = os.environ')[0].split('exec(open(')[0])
exec("def entry3" + open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split("def entry3", 1)[1].split("part = os.environ")[0])


def side_of(t):
    return next((n for n, (lo, hi) in PER if lo <= t < hi), None)


def show(tag, L):
    if not L:
        print(f"    {tag}: 없음")
        return
    L = sorted(L)
    cut = L[:-1] if len(L) > 3 else L
    print(f"    {tag}: 평균 {sum(L) / len(L):+.2f}% · 가운데 {statistics.median(L):+.2f}% · 큰 1건 뺀 {sum(cut) / len(cut):+.2f}% · 이김 {sum(x > 0 for x in L) / len(L) * 100:.0f}% ({len(L)}건)")


FIN = entry3(al_mkt=-0.01)
rows = []
for c, b in data.items():
    old, new = entry()(c, b), FIN(c, b)
    for k in np.flatnonzero(old | new):
        s = side_of(b["t"][k])
        if s is None:
            continue
        r = solo(c, k)
        if r is not None:
            rows.append((s, r, bool(old[k]), bool(new[k])))
print(f"== 15분봉 24회차: 최종 후보 신호 하나하나 ({len(data)}종목) ==", flush=True)
for s in ("앞", "뒤"):
    R = [r for r in rows if r[0] == s]
    print(f"  {s}")
    show("0회차 신호 전체", [r[1] for r in R if r[2]])
    show("0회차 신호 중 최종 후보에서 막힘", [r[1] for r in R if r[2] and not r[3]])
    show("최종 후보 신호 전체", [r[1] for r in R if r[3]])
    show("최종 후보에서 새로 생긴 신호(정오 대신 10:45 등)", [r[1] for r in R if r[3] and not r[2]])
print("끝", flush=True)
