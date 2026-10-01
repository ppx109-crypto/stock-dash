"""두 규칙 매매 겹침(사용자 질문 2026-10-01: "1일봉 거래 대부분을 1시간봉에서도 했다는 뜻이야?").
같은 기간(2023-10-01 ~ 2026-09-30)에 일봉 새 82회차 규칙과 1시간봉 94회차 규칙의 매매 목록(씨앗 0)을 맞대어 봄.
- 같은 종목을 '산 날이 앞뒤 5거래일 안'에 다른 규칙도 샀으면 겹친 매매로 셈.
"""
import sys
from datetime import date
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import json
OUT = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/x001_"
part = sys.argv[1] if len(sys.argv) > 1 else "compare"
lo, hi = "20231001", "20260930"
if part == "hour":
    import hlab as H
    exec(open("research/h094.py", encoding="utf-8").read().split('print("== 1시간봉 94회차')[0])
    RK = rk_of(tiers(20, 5, 3))
    res = H.simulate(data, e_align_or_noon, EX, size, rank=RK, stale_of=stale90, seeds=1)
    hour = [(t["code"], t["산 때"][:8], t["손익"], t["칸"]) for side in ("앞", "뒤") if res.get(side) for t in res[side]["목록"]]
    json.dump(hour, open(OUT + "hour.json", "w"))
    sys.exit()
if part == "day":
    import ntools as T
    got = T.once("일봉 새 82회차")
    day = [(t["code"], t["산 날"], t["손익"], t.get("자리") or t.get("칸")) for side in ("앞", "뒤") if got.get(side)
           for t in got[side]["매매목록"]]
    json.dump(day, open(OUT + "day.json", "w"))
    sys.exit()
hour = [tuple(x) for x in json.load(open(OUT + "hour.json"))]
day = [tuple(x) for x in json.load(open(OUT + "day.json"))]
day = [x for x in day if lo <= x[1] <= hi]
hour = [x for x in hour if lo <= x[1] <= hi]
d = lambda s: date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def near(a, pool, days=7):
    return any(c == a[0] and abs((d(b) - d(a[1])).days) <= days for c, b, *_ in pool)


dh = [x for x in day if near(x, hour)]
hd = [x for x in hour if near(x, day)]
print(f"기간 {lo} ~ {hi}")
print(f"일봉 매매 {len(day)}건 · 1시간봉 매매 {len(hour)}건")
print(f"일봉 매매 중 1시간봉도 앞뒤 5거래일 안에 같은 종목을 산 것: {len(dh)}건 ({len(dh) / max(1, len(day)) * 100:.0f}%)")
print(f"1시간봉 매매 중 일봉도 앞뒤 5거래일 안에 같은 종목을 산 것: {len(hd)}건 ({len(hd) / max(1, len(hour)) * 100:.0f}%)")
print(f"종목 수: 일봉 {len({x[0] for x in day})} · 1시간봉 {len({x[0] for x in hour})} · 둘 다 {len({x[0] for x in day} & {x[0] for x in hour})}")
same_day = [x for x in day if any(c == x[0] and b == x[1] for c, b, *_ in hour)]
print(f"같은 날 같은 종목을 산 매매: {len(same_day)}건")
avg = lambda xs: sum(x[2] for x in xs) / max(1, len(xs))
print(f"평균 손익(한 매매): 일봉 겹친 {avg(dh):+.2f}% · 일봉만 {avg([x for x in day if x not in dh]):+.2f}% · "
      f"1시간봉 겹친 {avg(hd):+.2f}% · 1시간봉만 {avg([x for x in hour if x not in hd]):+.2f}%")
