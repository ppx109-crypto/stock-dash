"""15분봉 14회차 — 13회차 확인: 추세 손절을 −5 → −4% · −4.5%로 바꿀 때 바뀐 매매를 직접 봄(씨앗 0 목록),
그리고 새 후보 뒤 반의 가장 깊은 하락(골)이 언제 · 어떤 매매로 생겼는지. 161종목."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q013.py", encoding="utf-8").read().split('part = os.environ')[0])


def sim(ex):
    return M.simulate(data, lambda c, b: SG[c], ex, size, rank=RKB, stale_of=make_stale(), seeds=1)


base, s4, s45 = sim(make_exit()), sim(make_exit(stop=4)), sim(make_exit(stop=4.5))
key = lambda t: (t["code"], t["산 때"])
for name, other in (("−4%", s4), ("−4.5%", s45)):
    a = {key(t): t for t in base["앞"]["목록"]}
    b = {key(t): t for t in other["앞"]["목록"]}
    gone = [a[k] for k in a if k not in b or a[k]["판 때"] != b[k]["판 때"]]
    came = [b[k] for k in b if k not in a or a[k]["판 때"] != b[k]["판 때"]]
    acc = lambda L: sum(t["손익"] * t["칸"] / 10 for t in L)
    print(f"앞 반 추세 손절 −5 → {name}: 바뀐 매매 기준 {len(gone)}건 {acc(gone):+.1f}%(계좌 몫) → 새 {len(came)}건 {acc(came):+.1f}%")
    for t in sorted(came, key=lambda t: t["산 때"])[:12]:
        print(f"    {t['code']} {t['산 때']} → {t['판 때']} {t['손익']:+.1f}% {t['칸']}칸")
cv = base["뒤"]["곡선"]
days = sorted(cv)
peak, worst, at = 0, 0, None
for d in days:
    peak = max(peak, cv[d])
    dd = cv[d] / peak - 1
    if dd < worst:
        worst, at = dd, d
top = max((d for d in days if d <= at), key=lambda d: cv[d])
print(f"뒤 반 가장 깊은 하락: {top} → {at} {worst * 100:.1f}%")
inside = [t for t in base["뒤"]["목록"] if top <= t["판 때"][:8] <= at or top <= t["산 때"][:8] <= at]
for t in sorted(inside, key=lambda t: t["손익"] * t["칸"])[:10]:
    print(f"    {t['code']} {t['산 때']} → {t['판 때']} {t['손익']:+.1f}% {t['칸']}칸")
