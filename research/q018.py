"""15분봉 17회차 — 16회차: 장중 시장 문턱 −0.75% → −1%에서 앞 반이 91 → 142로 뜀. 바뀐 매매를 직접 봄(씨앗 0),
그리고 새 후보(기준) → −1% 쉼에서 막힌 매매 · 새로 담긴 매매의 계좌 몫 손익(두 반). 161종목."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])


def sim(fn):
    sg = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    return M.simulate(data, lambda c, b: sg[c], exit_rule, size, rank=rank_plus(tiers(sg)), stale_of=stale90, seeds=1)


mk = lambda x: cut_at("1045", lambda c, k: nan0(DR[c])[k] > 0.02 or (x is not None and nan0(MKT[c])[k] < x))
base, m075, m1 = sim(mk(None)), sim(mk(-0.0075)), sim(mk(-0.01))
key = lambda t: (t["code"], t["산 때"])
acc = lambda L: sum(t["손익"] * t["칸"] / 10 for t in L)
for side in ("앞", "뒤"):
    for name, a_run, b_run in (("기준 → −1%", base, m1), ("−0.75% → −1%", m075, m1)):
        a = {key(t): t for t in a_run[side]["목록"]}
        b = {key(t): t for t in b_run[side]["목록"]}
        gone = [a[k] for k in a if k not in b or a[k]["판 때"] != b[k]["판 때"]]
        came = [b[k] for k in b if k not in a or a[k]["판 때"] != b[k]["판 때"]]
        big = sorted(came, key=lambda t: -abs(t["손익"] * t["칸"]))[:3]
        print(f"{side} {name}: 빠진 {len(gone)}건 {acc(gone):+.1f}% → 담긴 {len(came)}건 {acc(came):+.1f}% · 담긴 것 중 큰 것 "
              + ", ".join(f"{t['code']} {t['산 때'][:8]} {t['손익']:+.1f}%×{t['칸']}" for t in big))
