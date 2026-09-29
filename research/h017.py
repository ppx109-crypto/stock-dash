"""1시간봉 17회차 — '돈이 노는 시간 줄이기'(사용자 목표: 자금이 더 빨리 · 많이 일해 수익률 ↑). 지금 가동 62~67%.
① 칸을 잘게: 20칸 계좌에서 한 종목 20% · 10%(4 · 2칸) / 30% · 15%(6 · 3칸) → 더 많은 종목을 함께 담음
② 신호를 넓힘(긴 판 그대로): 수급(가르침) 없이도 1시간봉 A 정배열이 된 봉이면 삼 · 정배열 문의 시장 폭 50 → 40%
③ 둘을 함께
연 = 처음 자금 기준 복리 없는 한 해 몫(칸 수가 달라도 견줄 수 있음) · 파는 법 = 일봉 규칙."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

def door2(x, breadth=50):
    if not x: return None
    if x["추세문"]: return "추세"
    if x["정배열"] and 19 <= x["간격"] < 53 and (x["시장폭"] or 0) >= breadth: return "정배열"
    return None
def make_entry(need_flow=True, breadth=50, align_without_flow=False):
    def e(c, b):
        a = ATT[c]
        base = np.array([door2(x, breadth) is not None and (x["가르침"] or not need_flow) for x in a]) & IN[c]
        s = H.states(c, b, "A")["정배열"] == 1
        edge = s & ~np.r_[False, s[:-1]]
        loose = np.array([door2(x, breadth) is not None for x in a]) & IN[c] & edge if align_without_flow else np.zeros(len(a), bool)
        nn = base & hour_is(b, "11")
        days = [t[:8] for t in b["t"]]; seen = set(); m = np.zeros(len(a), bool)
        for k in range(len(m)):
            if ((base[k] & edge[k]) or nn[k] or loose[k]) and days[k] not in seen:
                m[k] = True; seen.add(days[k])
        return m
    return e
def sizer(big, small):
    def f(c, b, k):
        x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
        return big if x and (x["추세문"] or x["3일연속"]) else small
    return f
# 파는 법의 갈래(추세 · 정배열)는 산 때 재료로 — 넓힌 시장 폭에서도 정배열 갈래로
def exit_any(c, b, p, k):
    return exit_daily(c, b, p, k)

print("== 1시간봉 17회차 (돈이 노는 시간 줄이기) ==", flush=True)
rows = [("지금: 10칸 · 4/2칸", make_entry(), 10, sizer(4, 2)),
        ("20칸 · 4/2칸(20% · 10%)", make_entry(), 20, sizer(4, 2)),
        ("20칸 · 6/3칸(30% · 15%)", make_entry(), 20, sizer(6, 3)),
        ("10칸 · 수급 없이도 1시간봉 정배열이면", make_entry(align_without_flow=True), 10, sizer(4, 2)),
        ("10칸 · 정배열 문 시장 폭 40%", make_entry(breadth=40), 10, sizer(4, 2)),
        ("20칸 · 4/2칸 · 수급 없이도 정배열이면", make_entry(align_without_flow=True), 20, sizer(4, 2)),
        ("20칸 · 6/3칸 · 수급 없이도 정배열이면", make_entry(align_without_flow=True), 20, sizer(6, 3))]
for tag, e, slots, sz in rows:
    res = H.simulate(data, e, exit_any, sz, rank=rank, slots=slots)
    print(f"  {tag:34s} " + H.line(res), flush=True)
    print(f"      반기(씨앗 0): 앞 {res['앞']['반기'] if res['앞'] else '-'} · 뒤 {res['뒤']['반기'] if res['뒤'] else '-'}", flush=True)
print("끝", flush=True)
