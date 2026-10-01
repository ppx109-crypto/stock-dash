"""1시간봉 110회차(T2 · C5 잣대) — 94회차 숫자 고원(같은 시각 순서: 무리 3 · 수익 20일 · 수급 5일 / 자리 바꾸기: 7봉 · +4% 못 감)을
**한투 자료**(15분봉을 1시간으로 묶음 · 2025-09 ~ 2026-08)로 다시 봄. 야후 자료의 94회차 고원과 같은 쪽이 나으면 '두 자료 모두'.
Q_PART=1: 순서 숫자 · Q_PART=2: 자리 바꾸기 숫자. 씨앗 16."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
os.environ["Q_BARS"] = "1h"
exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())


def go(tag, rank=None, st=stale90):
    res = M.simulate(data, lambda c, b: SIGS[c], exit_rule, size, rank=rank or RANK, stale_of=st, seeds=16)
    print(f"  {tag:36s} " + H.line(res), flush=True)


def stale_x(bars=7, gain=4, br=90):
    def st(p):
        if not ((p["now"] - p["i"] >= bars) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < gain):
            return False
        x = ATT[p["code"]][p["now"]]
        return (x["시장폭"] if x and x["시장폭"] is not None else 100) < br
    return st


part = os.environ.get("Q_PART", "1")
print(f"== 1시간봉 110회차({part}): 94회차 숫자를 한투 자료로 ({len(data)}종목) ==", flush=True)
go("기준(94회차 숫자)")
if part == "1":
    for n in (2, 5):
        go(f"순서 무리 {n}", rank=rank_of(tiers(SIGS, 20, 5, n)))
    for rn in (10, 40):
        go(f"순서 수익 {rn}일", rank=rank_of(tiers(SIGS, rn, 5, 3)))
    go("순서 수급 10일", rank=rank_of(tiers(SIGS, 20, 10, 3)))
    go("순서 없음(추세 · 3일 연속만)", rank=rank_of({}))
else:
    for bars, gain in ((5, 4), (10, 4), (7, 2), (7, 6)):
        go(f"자리 바꾸기 {bars}봉 · +{gain}%", st=stale_x(bars, gain))
    go("자리 바꾸기 없음", st=None)
print("끝", flush=True)
