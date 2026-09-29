"""1시간봉 12회차(확인 줄) — 11회차 후보 '시장 폭 70% 아래면 종목 모음을 150위까지' (사는 때 = 아침 09시 시가) 확인.
- 문턱 고원: 62 · 65 · 68 · 70 · 72 · 75 · 80
- 계좌 짜임: 자리 8 · 12
- 더해진 매매(넓혀서 새로 산 101~150위 매매)의 손익 · 반기별 · 큰 몇 건에 기대는지"""
import sys, collections
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
U150 = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=150)
IN100 = IN
IN150 = {c: np.array([U150.ok(c, t) for t in data[c]["t"]]) for c in data}
BRD = {c: np.array([(x["시장폭"] if x and x["시장폭"] is not None else 100) for x in ATT[c]]) for c in data}

def run(tag, x, slots=10, show_added=False):
    global IN
    IN = {c: np.where(BRD[c] < x, IN150[c], IN100[c]) for c in data}
    res = H.simulate(data, e_morning, exit_daily, size, rank=rank, slots=slots)
    print(f"  {tag:30s} " + H.line(res), flush=True)
    if show_added:
        for side in ("앞", "뒤"):
            by = collections.defaultdict(lambda: [0, 0.0]); big = []
            for t in res[side]["목록"]:
                c = t["code"]; b = data[c]; k = b["t"].index(t["산 때"])
                if not IN100[c][k]:
                    h = t["산 때"][:4] + ("상" if t["산 때"][4:6] <= "06" else "하")
                    by[h][0] += 1; by[h][1] += t["손익"] * t["칸"] / slots; big.append(t["손익"])
            big.sort()
            print(f"      더해진 매매 {side}: {sum(v[0] for v in by.values())}건 · 계좌 몫 {sum(v[1] for v in by.values()):+.1f}% · "
                  + ", ".join(f"{h} {v[0]}건 {v[1]:+.1f}" for h, v in sorted(by.items()))
                  + (f" · 가장 큰 3건 {big[-3:]} · 가운데 {np.median(big):+.1f}%" if big else ""), flush=True)

print("== 1시간봉 12회차 (확인: 약한 장일 때만 150위) ==", flush=True)
run("늘 100위(지금)", -1)
for x in (62, 65, 68, 70, 72, 75, 80):
    run(f"시장 폭 {x}% 아래면 150위", x, show_added=(x == 70))
for s in (8, 12):
    run(f"늘 100위 · 자리 {s}", -1, slots=s)
    run(f"70% 아래면 150위 · 자리 {s}", 70, slots=s)
print("끝", flush=True)
