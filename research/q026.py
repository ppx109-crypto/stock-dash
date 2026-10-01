"""15분봉 25회차 — 최종 후보의 이득이 여러 달에 고르게 퍼졌는지: 달마다 계좌 손익(씨앗 0 · 판 매매의 계좌 몫 합)을
0회차와 견줌. 한두 달에 몰렸으면 드문 행운으로 봄. 161종목."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('part = os.environ')[0])


def monthly(fn):
    sg = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    res = M.simulate(data, lambda c, b: sg[c], exit_rule, size, rank=rank_plus(tiers(sg)), stale_of=stale90, seeds=1)
    out = {}
    for s in ("앞", "뒤"):
        for t in res[s]["목록"]:
            m = t["판 때"].lstrip("끝")[:6]
            out[m] = out.get(m, 0) + t["손익"] * t["칸"] / 10
    return out


a, b = monthly(entry()), monthly(entry3(al_mkt=-0.01))
print("== 15분봉 25회차: 달마다 계좌 손익(%) — 0회차 / 최종 후보 / 차이 ==", flush=True)
better = 0
for m in sorted(set(a) | set(b)):
    x, y = a.get(m, 0), b.get(m, 0)
    better += y > x
    print(f"  {m}: {x:+6.1f} / {y:+6.1f} / {y - x:+6.1f}")
print(f"  최종 후보가 나은 달 {better} / {len(set(a) | set(b))}")
print("끝", flush=True)
