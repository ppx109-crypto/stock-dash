"""1시간봉 18회차(두 번째 줄) — 버는 종목에 더 태우기(불타기): 돈이 노는 시간 줄이기 · 이긴 매매에 자금을 더 일하게.
긴 판(지금 규칙) 그대로 사고, 들고 있는 동안 한 번만 더 삼(다음 봉 시가, 평균 단가로 합침 · 한 종목 최대 4칸 = 40% 지킴):
- A: +5%에 처음 닿고(봉 종가) 1시간봉 A 정배열이면 +2칸
- B: 이익 중(+2% 넘음)에 1시간봉 7봉 최고가 돌파 + 거래량 2배면 +2칸
- C: 들고 있는 동안 일봉 재료가 '3일 연속'으로 바뀌면 +2칸
- D: A와 같되 +8%에서
더한 뒤 파는 법은 일봉 규칙(평균 단가 기준). 바뀐 매매(더한 매매)의 손익을 따로 봄."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

E = e_align_or_noon
def with_add(kind, level=5, n=2):
    def go(c, b, p, k):
        r = exit_daily(c, b, p, k)
        if r:
            return r
        if p.get("더함") or p["칸"] + n > 4:
            return 0
        now = (b["c"][k] / p["price"] - 1) * 100
        if kind in ("A", "D"):
            before = b["c"][p["i"]:k].max() if k > p["i"] else -1
            if now >= level and (before / p["price"] - 1) * 100 < level and H.states(c, b, "A")["정배열"][k] == 1:
                return ("add", n)
        elif kind == "B":
            if now > 2 and k >= 7 and b["c"][k] > b["h"][k - 7:k].max():
                v = b["v"][max(0, k - 20):k]
                if len(v) and v.mean() > 0 and b["v"][k] >= 2 * v.mean():
                    return ("add", n)
        elif kind == "C":
            x = ATT[c][k + 1] if k + 1 < len(b["t"]) else None
            x0 = ATT[c][p["i"]]
            if x and x["3일연속"] and not (x0 and x0["3일연속"]):
                return ("add", n)
        return 0
    return go

print("== 1시간봉 18회차 (불타기: 버는 종목에 더 태우기) ==", flush=True)
base = H.simulate(data, E, exit_daily, size, rank=rank)
print(f"  {'지금(더 태우기 없음)':28s} " + H.line(base), flush=True)
for tag, kind, lvl in (("A: +5% · 1시간봉 정배열이면 +2칸", "A", 5), ("D: +8% · 1시간봉 정배열이면 +2칸", "D", 8),
                       ("B: 이익 중 돌파 + 거래량이면 +2칸", "B", 0), ("C: 3일 연속으로 바뀌면 +2칸", "C", 0)):
    res = H.simulate(data, E, with_add(kind, lvl), size, rank=rank)
    print(f"  {tag:28s} " + H.line(res), flush=True)
    print(f"      반기(씨앗 0): 앞 {res['앞']['반기'] if res['앞'] else '-'} · 뒤 {res['뒤']['반기'] if res['뒤'] else '-'}", flush=True)
print("끝", flush=True)
