"""W 3회차 — W 첫 후보(약세장 혼자 정배열 + 공통 수급)를 1일봉 규칙(새 82)과 **한 계좌**에 함께: W는 1일봉 정배열 문이 쉬는 날(시장 폭 50% 아래)에만
사므로 1일봉 몫을 줄이지 않고 빈 칸을 씀. 크기 · 순서 · 파는 법은 1일봉 규칙 그대로(W 줄은 정배열 쪽 파는 법). 씨앗 8 · 두 반.
Q_PART=1: 기준(새 82) · 82 + W(수급) · 82 + W(수급 + 신고가 근처) / Q_PART=2: 82 + W(수급) 비용 0.5% · 82 + W(수급) W 줄 2칸 고정."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import wtools as W


def alone(r):
    f = nrl.F.form_of(nrl.shape, r)
    return bool(f.get("정배열") and f.get("간격") is not None and 19 <= f["간격"] < 53)


near_high = lambda r: (r.get("250일 전고점 대비") is not None and r["250일 전고점 대비"] >= -3)
wrow = lambda r: W.weak(r) and alone(r) and nrl.teacher(r) and not nrl.target_cut(r)
wrow_h = lambda r: wrow(r) and near_high(r)
part = os.environ.get("Q_PART", "1")
print(f"== W 3회차({part}): 1일봉 규칙과 한 계좌에 함께 ==", flush=True)
if part == "1":
    T.once("기준(새 82 혼자)")
    T.once("82 + W(약세장 혼자 정배열 + 수급)", holds=lambda r: nrl.BASE_HOLD(r) or wrow(r))
    T.once("82 + W(+ 신고가 근처)", holds=lambda r: nrl.BASE_HOLD(r) or wrow_h(r))
else:
    T.once("82 + W(수급) · 비용 0.5%", holds=lambda r: nrl.BASE_HOLD(r) or wrow(r), cost=0.5)
    T.once("기준 · 비용 0.5%", cost=0.5)
    T.once("82 + W(수급) · W 줄 2칸", holds=lambda r: nrl.BASE_HOLD(r) or wrow(r),
           size=lambda r: 2 if (wrow(r) and not nrl.BASE_HOLD(r)) else nrl.BASE_SIZE(r))
print("끝", flush=True)
