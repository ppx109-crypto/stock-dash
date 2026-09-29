"""1시간봉 9회차(사용자 요청: 1시간봉 기준 최적 손절 · 익절) — 파는 숫자를 하나씩 위아래로 흔듦(봉 종가로 판단 → 다음 봉 시가).
사는 때 = 1시간봉 A 정배열 된 봉 다음, 없으면 12시 · 무엇을 = A그룹 꼴.
추세 문 매매: 반익 +5% · 전량 +13% · 손절 −5% · 60봉 / 정배열 문 매매: 손절 −10% · 본전 지키기(+8% 뒤 +1%) · 일봉 정배열 깨짐."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

def make_exit(half=5, take=13, tstop=5, bars=60, astop=10, reach=8, back=1, abars=None):
    def go(c, b, p, k):
        now = (b["c"][k] / p["price"] - 1) * 100
        kind = door(ATT[c][p["i"]]) or "정배열"
        held = k - p["i"]
        if kind == "추세":
            if now >= take or now <= -tstop or held >= bars: return "all"
            before = b["c"][p["i"]:k].max() if k > p["i"] else -1
            if half and now >= half and (before / p["price"] - 1) * 100 < half and p["칸"] == p["처음칸"]:
                return max(1, p["처음칸"] // 2)
            return 0
        if now <= -astop: return "all"
        if (p["peak"] / p["price"] - 1) * 100 >= reach and now <= back: return "all"
        if abars and held >= abars: return "all"
        if k + 1 < len(b["t"]):
            nx = ATT[c][k + 1]
            if nx is not None and not nx["정배열"]: return "all"
        return 0
    return go

E = e_align_or_noon
rows = [("지금(5 · 13 · −5 · 60봉 / −10 · 8→1)", {})]
rows += [(f"추세 손절 −{s}%", {"tstop": s}) for s in (3, 4, 6, 8)]
rows += [(f"추세 전량 +{t}%", {"take": t}) for t in (8, 10, 16, 20, 30)]
rows += [(f"추세 반익 +{h}%", {"half": h}) for h in (3, 4, 7)] + [("추세 반익 없음", {"half": 0})]
rows += [(f"추세 최대 {n}봉", {"bars": n}) for n in (30, 90, 120)]
rows += [(f"정배열 손절 −{s}%", {"astop": s}) for s in (5, 7, 12, 15)]
rows += [(f"본전 지키기 +{r}% 뒤 +{bk}%", {"reach": r, "back": bk}) for r, bk in ((5, 1), (6, 1), (10, 1), (8, 3), (12, 3))]
rows += [(f"정배열 최대 {n}봉", {"abars": n}) for n in (60, 120)]
print("== 1시간봉 9회차 (손절 · 익절 숫자 흔들기) ==", flush=True)
for tag, kw in rows:
    res = H.simulate(data, E, make_exit(**kw), size, rank=rank)
    print(f"  {tag:30s} " + H.line(res), flush=True)
print("끝", flush=True)
