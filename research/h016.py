"""1시간봉 16회차 — 긴 판 + 짧은 판 섞기(사용자 목표: 빠른 회전으로 수익률 올리기 · 14회차 다음 자리).
한 계좌(10칸)에서 사는 신호는 지금 규칙 그대로(A그룹 꼴 + 가르침, 정배열 된 봉 다음 · 없으면 12시). 산 매매의 '판'을 산 때 정함:
- 센 재료(추세 문 또는 3일 연속)로 산 것 → 짧은 판(장중 +8% 지정가 익절 · −5% 손절 · 35봉) / 나머지 → 긴 판(일봉 규칙 파는 법)
- 반대로도: 센 재료 → 긴 판, 나머지 → 짧은 판
- 섞은 판: 센 재료는 짧은 판으로 사되 35봉이 지나도 1시간봉 A 정배열이면 긴 판으로 넘김
- 돌파 + 거래량(7봉 최고가 돌파 · 거래량 2배)인 봉에서 산 긴 판은 4칸(15회차: 한 매매의 질이 높음)
짧은 판 칸 수 2 · 4."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

E = e_align_or_noon
def strong_at(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    return bool(x and (x["추세문"] or x["3일연속"]))
TAG = {}
def sized(short_when, short_size=4, burst_big=False):
    def f(c, b, k):
        s = strong_at(c, b, k)
        is_short = s if short_when == "strong" else (not s if short_when == "weak" else False)
        TAG[(c, k + 1)] = "short" if is_short else "long"
        if is_short:
            return short_size
        if burst_big and k >= 7 and b["c"][k] > b["h"][k - 7:k].max():
            v = b["v"][max(0, k - 20):k]
            if len(v) and v.mean() > 0 and b["v"][k] >= 2 * v.mean():
                return 4
        return size(c, b, k)
    return f
def mixed_exit(hand_over=False):
    def go(c, b, p, k):
        if TAG.get((c, p["i"])) == "short":
            if k - p["i"] >= 35:
                if hand_over and H.states(c, b, "A")["정배열"][k] == 1:
                    TAG[(c, p["i"])] = "long"
                    return 0
                return "all"
            return 0
        return exit_daily(c, b, p, k)
    return go
def take_short(p):
    return (p["price"] * 1.08, "all") if TAG.get((p["code"], p["i"])) == "short" else (None, 0)
def stop_short(p):
    return p["price"] * 0.95 if TAG.get((p["code"], p["i"])) == "short" else None

print("== 1시간봉 16회차 (긴 판 + 짧은 판 섞기) ==", flush=True)
res = H.simulate(data, E, exit_daily, size, rank=rank)
print(f"  {'긴 판만(지금)':34s} " + H.line(res), flush=True)
for tag, sw, ss, ho, bb in (("센 재료 → 짧은 판(4칸)", "strong", 4, False, False),
                            ("센 재료 → 짧은 판(2칸)", "strong", 2, False, False),
                            ("센 재료 → 짧은 판, 35봉 뒤 정배열이면 긴 판", "strong", 4, True, False),
                            ("나머지 → 짧은 판(2칸) · 센 재료는 긴 판", "weak", 2, False, False),
                            ("긴 판만 + 돌파 · 거래량 봉이면 4칸", "none", 4, False, True),
                            ("센 재료 짧은 판 + 돌파 · 거래량 4칸", "strong", 4, False, True)):
    TAG.clear()
    if sw == "none":
        res = H.simulate(data, E, exit_daily, sized("never", 4, True), rank=rank)
    else:
        res = H.simulate(data, E, mixed_exit(ho), sized(sw, ss, bb), rank=rank, take_of=take_short, stop_of=stop_short)
    print(f"  {tag:34s} " + H.line(res), flush=True)
    print(f"      반기(씨앗 0): 앞 {res['앞']['반기'] if res['앞'] else '-'} · 뒤 {res['뒤']['반기'] if res['뒤'] else '-'}", flush=True)
print("끝", flush=True)
