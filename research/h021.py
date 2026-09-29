"""1시간봉 21회차 — 짧은 판 B(센 재료만 · 4칸 · +8% · −5% · 35봉)의 질을 지키며 가동 올리기.
B는 골이 얕고(−8 ~ −11%) 행운뺌이 크지만 가동 27%. 늘리는 길:
- 종목 모음 150위까지(센 재료만)
- '센 재료'에 돌파 + 거래량 날을 더함(A그룹 꼴 + 가르침 날에 7봉 최고가 돌파 + 거래량 2배면 센 것으로 봄)
- 반은 +8% 지정가, 나머지 반은 1시간봉 20봉 EMA 아래로 닫힐 때까지(최대 70봉) — 짧게 벌고 긴 추세도 조금 탐
- 둘 다(150위 + 돌파 날) · 반익 + 따라가기까지"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import rna
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
U150 = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=150)
IN150 = {c: np.array([U150.ok(c, t) for t in data[c]["t"]]) for c in data}

def strong_ctx(x):
    return bool(x and x["가르침"] and (x["추세문"] or (door(x) is not None and x["3일연속"])))
def burst_bar(b, k):
    if k < 20 or b["c"][k] <= b["h"][k - 7:k].max(): return False
    v = b["v"][k - 20:k]
    return v.mean() > 0 and b["v"][k] >= 2 * v.mean()
def entry(wide=False, add_burst=False):
    def e(c, b):
        inn = IN150[c] if wide else IN[c]
        a = ATT[c]
        strong = np.array([strong_ctx(x) for x in a]) & inn
        okc = np.array([ok(x) for x in a]) & IN[c]
        s = H.states(c, b, "A")["정배열"] == 1
        edge = s & ~np.r_[False, s[:-1]]
        days = [t[:8] for t in b["t"]]; seen = set(); m = np.zeros(len(a), bool)
        for k in range(len(m)):
            if days[k] in seen: continue
            hit = strong[k] and (edge[k] or b["t"][k][8:] == "11")
            if add_burst and okc[k] and burst_bar(b, k): hit = True
            if hit:
                m[k] = True; seen.add(days[k])
        return m
    return e
_E20 = {}
def e20(c, b):
    if c not in _E20: _E20[c] = rna.ema(b["c"], 20)
    return _E20[c]
def exit_fixed(c, b, p, k): return "all" if k - p["i"] >= 35 else 0
def exit_trail(c, b, p, k):
    if p["칸"] < p["처음칸"]:
        if b["c"][k] < e20(c, b)[k] or k - p["i"] >= 70: return "all"
        return 0
    return "all" if k - p["i"] >= 35 else 0
take_all = lambda p: (p["price"] * 1.08, "all")
take_half = lambda p: (p["price"] * 1.08, p["처음칸"] // 2) if p["칸"] == p["처음칸"] else (None, 0)
stop5 = lambda p: p["price"] * 0.95
four = lambda c, b, k: 4

print("== 1시간봉 21회차 (짧은 판 B의 가동 올리기) ==", flush=True)
print(f"  {'견줌: 긴 판(지금 규칙)':30s} " + H.line(H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)), flush=True)
for tag, e, ex, tk in (("B(100위 · 센 재료)", entry(), exit_fixed, take_all),
                       ("B · 150위", entry(wide=True), exit_fixed, take_all),
                       ("B · 돌파 + 거래량 날 더함", entry(add_burst=True), exit_fixed, take_all),
                       ("B · 반은 +8% · 반은 20봉선 따라가기", entry(), exit_trail, take_half),
                       ("B · 150위 + 돌파 날", entry(True, True), exit_fixed, take_all),
                       ("B · 150위 + 돌파 날 + 반 따라가기", entry(True, True), exit_trail, take_half)):
    res = H.simulate(data, e, ex, four, rank=rank, take_of=tk, stop_of=stop5)
    print(f"  {tag:30s} " + H.line(res), flush=True)
    print(f"      반기(씨앗 0): 앞 {res['앞']['반기'] if res['앞'] else '-'} · 뒤 {res['뒤']['반기'] if res['뒤'] else '-'}", flush=True)
print("끝", flush=True)
