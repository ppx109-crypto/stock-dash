"""15분봉 29회차 — 1시간봉 · 일봉 연구 옮기기 ④.
Q_PART=1: 자리 바꾸기에서 비킬 차례(1시간봉 48 · 50회차): 최근에 산 묵음부터 · 오래 든 것부터 (지금 = 손익 나쁜 것부터)
Q_PART=2: 장세에 따라 파는 법(1시간봉 59회차): 전날 시장 폭 50% 아래면 추세 익절 +8% · 손절 −4% / 시장 폭 80% 위면 추세 익절 +18%
최종 후보(22회차) 위 · 161종목 · 씨앗 16.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
exec("def make_exit" + open("/home/user/stock-dash/research/q003.py", encoding="utf-8").read().split("def make_exit", 1)[1].split("def run(tag")[0])


def go2(tag, ex=None, key=None):
    res = M.simulate(data, lambda c, b: SGF[c], ex or exit_rule, size, rank=RKF, stale_of=stale90, stale_key=key, seeds=16)
    print(f"  {tag:36s} " + H.line(res), flush=True)


WEAK, STRONG = make_exit(take=8, stop=4), make_exit(take=18)


def by_regime(c, b, p, k):
    x = ATT[c][k]
    br = (x["시장폭"] if x and x["시장폭"] is not None else 70)
    if br < 50:
        return WEAK(c, b, p, k)
    if br > 80:
        return STRONG(c, b, p, k)
    return exit_rule(c, b, p, k)


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 29회차({part}): 1시간봉 · 일봉 연구 옮기기 ④ ({len(data)}종목) ==", flush=True)
if part == "1":
    go2("최종 후보 그대로")
    go2("비킬 차례: 최근에 산 것부터", key=lambda q: -q["i"])
    go2("비킬 차례: 오래 든 것부터", key=lambda q: q["i"])
else:
    go2("장세별 추세 익절 · 손절", ex=by_regime)
print("끝", flush=True)
