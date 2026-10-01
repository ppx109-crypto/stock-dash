"""15분봉 2회차 — 파는 때 · 자리 바꾸기(사는 때는 0회차 그대로). 1시간봉 숫자 × 4에서 시작해 15분봉에 맞는 숫자를 찾음.
추세 문: 손절 −5 · 익절 +13 · 절반 +5 · 240봉 / 정배열 문: −10 · 이익 지키기 +8 → +1 · 일봉 정배열 깨짐 / 자리 바꾸기: 28봉 · +4% 못 감.
씨앗 16 · 두 반 · 비용 0.30%.
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())


def make_exit(stop=5, take=13, half=5, hold=60, astop=10, keep=(8, 1)):
    def ex(c, b, p, k):
        now = (b["c"][k] / p["price"] - 1) * 100
        kind = door(ATT[c][p["i"]]) or "정배열"
        if kind == "추세":
            if now >= take or now <= -stop or k - p["i"] >= hold * SCALE:
                return "all"
            before = b["c"][p["i"]:k].max() if k > p["i"] else -1
            if half and now >= half and (before / p["price"] - 1) * 100 < half and p["칸"] == p["처음칸"]:
                return max(1, p["처음칸"] // 2)
            return 0
        if now <= -astop:
            return "all"
        if keep and (p["peak"] / p["price"] - 1) * 100 >= keep[0] and now <= keep[1]:
            return "all"
        if k + 1 < len(b["t"]):
            nx = ATT[c][k + 1]
            if nx is not None and not nx["정배열"]:
                return "all"
        return 0
    return ex


def make_stale(bars=7, gain=4):
    def st(p):
        if not ((p["now"] - p["i"] >= bars * SCALE) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < gain):
            return False
        x = ATT[p["code"]][p["now"]]
        return (x["시장폭"] if x and x["시장폭"] is not None else 100) < 90
    return st


def run(tag, ex=None, st=None):
    res = M.simulate(data, lambda c, b: SIGS[c], ex or make_exit(), size, rank=RANK, stale_of=st or make_stale(), seeds=16)
    print(f"  {tag:34s} " + H.line(res), flush=True)


print("== 15분봉 2회차: 파는 때 · 자리 바꾸기 ==", flush=True)
run("0회차 그대로")
for s in (3, 4, 7):
    run(f"추세 손절 −{s}%", make_exit(stop=s))
for t in (10, 16):
    run(f"추세 익절 +{t}%", make_exit(take=t))
for h in (30, 90):
    run(f"추세 보유 {h * 4}봉", make_exit(hold=h))
run("추세 절반 익절 없음", make_exit(half=0))
for a in (7, 13):
    run(f"정배열 손절 −{a}%", make_exit(astop=a))
for kp in ((6, 1), (10, 2), None):
    run(f"이익 지키기 {kp}", make_exit(keep=kp))
for bars in (4, 14):
    run(f"자리 바꾸기 {bars * 4}봉", st=make_stale(bars=bars))
for g in (2, 6):
    run(f"자리 바꾸기 +{g}% 못 감", st=make_stale(gain=g))
print("끝", flush=True)
