"""15분봉 46회차 — 41회차 후보(1시간봉 규칙 손절 · 익절을 15분봉 종가마다 봄)의 버팀: 달마다 계좌 몫 · 손절선 −4.5 / −5.5% (추세) · −9 / −11% (정배열)."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
os.environ["Q_BARS"] = "1h"
exec(open("/home/user/stock-dash/research/q042.py", encoding="utf-8").read().split('part = os.environ')[0])

res = M.simulate(data, lambda c, b: SIGS[c], exit_rule, size, rank=RANK, stale_of=stale90, seeds=1)


def replay(ts, ta, side):
    by = {}
    for t in res[side]["목록"]:
        c = t["code"]
        if str(t["판 때"]).startswith("끝") or c not in IDX:
            continue
        b15, i0, i1 = M15[c], IDX[c].get(t["산 때"]), IDX[c].get(t["판 때"])
        if i0 is None or i1 is None:
            continue
        price = b15["o"][i0]
        kind = door(ATT[c][data[c]["t"].index(t["산 때"])]) or "정배열"
        base = (b15["o"][i1] / price - 1) * 100
        new = base
        for j in range(i0, i1 - 1):
            g = (b15["c"][j] / price - 1) * 100
            if (kind == "추세" and g <= -ts) or (kind != "추세" and g <= -ta):
                new = (b15["o"][j + 1] / price - 1) * 100
                break
        m = t["판 때"][:6]
        by[m] = by.get(m, 0) + (new - base) * t["칸"] / 10
    return by


print("== 15분봉 46회차: 1시간봉 손절을 15분봉 종가로 · 버팀 ==", flush=True)
for ts, ta in ((5, 10), (4.5, 9), (5.5, 11)):
    for side in ("앞", "뒤"):
        by = replay(ts, ta, side)
        good = sum(v > 0 for v in by.values())
        bad = sum(v < 0 for v in by.values())
        print(f"  추세 −{ts:g} · 정배열 −{ta:g}% {side}: 합 {sum(by.values()):+.1f}%p · 나은 달 {good} · 나쁜 달 {bad} · 달마다 " + " ".join(f"{m[2:]}:{v:+.1f}" for m, v in sorted(by.items()) if v), flush=True)
print("끝", flush=True)
