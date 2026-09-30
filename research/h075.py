"""1시간봉 75회차(확인 줄) — 희석 공시 거르기(72회차 후보)를 훨씬 긴 기간의 일봉 최고 규칙(새 RL 47회차, nrl.BASE_HOLD)에 씌워 봄: 2017~2020 · 2021~.
1시간봉 자료(2023-09~) 밖의 해들이라 '두 반에 맞춘 것'인지 가림. 공시는 신호 날 **앞날까지** 접수된 것만(그날 장 뒤 공시를 피하려 엄격히) · 20 · 40거래일.
참고: 일봉 옛 18회차에선 (다른 규칙에서) 공시 거르기가 오히려 나빴음."""
import sys, json, bisect
sys.path.insert(0, "/home/user/stock-dash")
import nrl
import hlab as H
from pathlib import Path
DIL = ("유상증자", "전환사채", "신주인수권부사채", "교환사채")
EV, DAYS = {}, {}
def dil(r, n):
    c = r["code"]
    if c not in EV:
        ev = H._events(c); EV[c] = sorted(x for k in DIL for x in ev.get(k, ()))
        p = Path(f"price-data/{c}.json")
        DAYS[c] = [x[0] for x in json.loads(p.read_text(encoding="utf-8"))["closes"]] if p.exists() else []
    d = DAYS[c]; i = bisect.bisect_left(d, r["date"])
    if i <= 0: return False
    lo = d[max(0, i - n)]
    e = EV[c]; j = bisect.bisect_right(e, lo)
    return j < len(e) and e[j] < r["date"]
print("== 1시간봉 75회차 (희석 공시 거르기 · 일봉 최고 규칙 2017~) ==", flush=True)
nrl.run("일봉 최고 규칙(47회차)")
for n in (10, 20, 40):
    nrl.run(f"+ 희석 공시 {n}거래일 거르기", holds=lambda r, n=n: nrl.BASE_HOLD(r) and not dil(r, n))
blocked = [r for r in nrl.inside if nrl.BASE_HOLD(r) and dil(r, 20)]
print(f"  20일 거르기로 막히는 신호 날: {len(blocked)} (2017~2020 {sum(r['date'] < '20210101' for r in blocked)} · 2021~ {sum(r['date'] >= '20210101' for r in blocked)}) · 종목 {len({r['code'] for r in blocked})}개", flush=True)
print("끝", flush=True)
