"""15분봉 12회차 — 새 후보(10:45 봉 뒤 사기 + 오늘 +2% 위면 안 삼 · 161종목)에서 파는 때 · 자리 바꾸기 · 골 줄이기를 다시 봄.
Q_PART=1: 추세 문 숫자(손절 · 익절 · 보유 봉) · 정배열 손절 · 이익 지키기.
Q_PART=2: 자리 바꾸기 · 계좌 브레이크(계좌가 꼭대기에서 x% 넘게 빠져 있으면 새 매수를 반으로 · 멈춤 — 지난 날 끝 값만 씀).
씨앗 16 · 두 반 · 비용 0.30%.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])
exec("def make_exit" + open("/home/user/stock-dash/research/q003.py", encoding="utf-8").read().split("def make_exit", 1)[1].split("def run(tag")[0])

BEST = cut_at("1045", lambda c, k: nan0(DR[c])[k] > 0.02)
SG = {c: np.asarray(BEST(c, b), bool) for c, b in data.items()}
RKB = rank_plus(tiers(SG))


def go(tag, ex=None, st=None, brake=None, cost=H.COST):
    res = M.simulate(data, lambda c, b: SG[c], ex or make_exit(), size, rank=RKB, stale_of=st or make_stale(),
                     seeds=16, cost=cost, brake=brake)
    print(f"  {tag:34s} " + H.line(res), flush=True)


def dd_brake(limit, cut):
    def f(eq):
        if not eq:
            return None
        peak = max(eq)
        return (cut if cut else True) if (eq[-1] / peak - 1) * 100 <= -limit else None
    return f


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 12회차({part}): 새 후보의 파는 때 · 골 줄이기 ({len(data)}종목) ==", flush=True)
go("새 후보 그대로")
if part == "1":
    for s in (4, 7):
        go(f"추세 손절 −{s}%", make_exit(stop=s))
    for t in (10, 16):
        go(f"추세 익절 +{t}%", make_exit(take=t))
    go("추세 보유 120봉", make_exit(hold=30))
    for a in (7, 13):
        go(f"정배열 손절 −{a}%", make_exit(astop=a))
    for kp in ((6, 1), (10, 2)):
        go(f"이익 지키기 {kp}", make_exit(keep=kp))
else:
    for bars in (4, 14):
        go(f"자리 바꾸기 {bars * 4}봉", st=make_stale(bars=bars))
    for g in (2, 6):
        go(f"자리 바꾸기 +{g}% 못 감", st=make_stale(gain=g))
    for lim in (8, 12):
        go(f"계좌 −{lim}% 빠지면 새 매수 반", brake=dd_brake(lim, 0.5))
        go(f"계좌 −{lim}% 빠지면 새 매수 멈춤", brake=dd_brake(lim, None))
print("끝", flush=True)
