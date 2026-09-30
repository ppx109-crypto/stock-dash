"""1시간봉 59회차 — 58회차: 고점 따라가기는 센 장(뒤)에선 조금 낫고 약한 장(앞)에선 짐 → 장에 따라 파는 법을 바꾸면?
센 장(판단하는 봉의 전 거래일 시장 폭 ≥ X%)이면 +13%에 팔지 않고 따라가기, 아니면 지금처럼 +13% 전량.
따라가기 두 가지: 고점 15% 되밀림 · 1시간봉 60봉선 아래. X = 60 · 70 · 80 · 90. 바탕은 1시간봉 최고 규칙(자리 바꾸기 폭<90)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
def regime_exit(X, how):
    trail = make_exit(trend="고점%", act=13, X=15) if how == "고점 15%" else make_exit(trend="힘", act=13, line=60)
    base = make_exit()
    def f(c, b, p, k):
        x = ATT[c][k]
        strong = x is not None and (x["시장폭"] if x["시장폭"] is not None else 0) >= X
        return (trail if strong else base)(c, b, p, k)
    return f
print("== 1시간봉 59회차 (센 장에서만 고점 따라가기) ==", flush=True)
CASES = [("지금(+13% 전량)", make_exit())]
for how in ("고점 15%", "60봉선"):
    for X in (60, 70, 80, 90):
        CASES.append((f"폭≥{X}이면 {how} 따라가기", regime_exit(X, how)))
for tag, ex in CASES:
    res = H.simulate(data, e_align_or_noon, ex, size, rank=rank, stale_of=stale90, seeds=16)
    tr = trimmed(ex)
    print(f"  {tag:24s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연(가운데): 앞 {tr['앞']} · 뒤 {tr['뒤']} · 반기(씨앗 0) 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
