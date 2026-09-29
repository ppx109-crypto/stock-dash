"""1시간봉 11회차(탐색 줄) — 8회차 실마리: 종목 모음을 150위까지 넓히면 약한 장(앞 반)이 크게 좋아지고 센 장(뒤 반)은 나빠짐.
→ **약한 장일 때만** 넓힌다: 전 거래일 시장 폭(100위 안 50일선>200일선 몫)이 X% 아래면 150위까지, 아니면 100위.
사는 때 = 아침 09시 시가(8회차에서 사는 때 차이는 잡음) · 후보(정배열, 없으면 12시) 둘 다 · 파는 법 = 일봉 규칙."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
src = open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0]
exec(src)
U150 = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=150)
IN100 = IN
IN150 = {c: np.array([U150.ok(c, t) for t in data[c]["t"]]) for c in data}
BRD = {c: np.array([(x["시장폭"] if x and x["시장폭"] is not None else 100) for x in ATT[c]]) for c in data}

def run(tag, weak_below, entry_name):
    global IN
    IN = {c: np.where(BRD[c] < weak_below, IN150[c], IN100[c]) for c in data}
    e = {"아침": e_morning, "후보": e_align_or_noon}[entry_name]
    res = H.simulate(data, e, exit_daily, size, rank=rank)
    print(f"  {tag:34s} " + H.line(res), flush=True)
    print(f"      반기(씨앗 0): 앞 {res['앞']['반기'] if res['앞'] else '-'} · 뒤 {res['뒤']['반기'] if res['뒤'] else '-'}", flush=True)

print("== 1시간봉 11회차 (약한 장일 때만 150위까지) ==", flush=True)
for entry_name in ("아침", "후보"):
    run(f"{entry_name} · 늘 100위(지금)", -1, entry_name)
    for x in (50, 60, 70, 80):
        run(f"{entry_name} · 시장 폭 {x}% 아래면 150위", x, entry_name)
    run(f"{entry_name} · 늘 150위", 101, entry_name)
print("끝", flush=True)
