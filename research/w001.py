"""W 1회차 — 약세 · 옆걸음장(시장 폭 50% 아래) 되돌림(과매도 반등). 시총 100위 안 · 2칸씩(10칸) · 가장 깊이 빠진 것부터(단기 이격밴드 낮은 순) · 씨앗 8.
Q_PART=1(문 셋 · 파는 법 '중기선 회복 또는 10일'): 단기 이격밴드 ≤ −1.6 · 20일 −15% · 볼린저 하단 아래
Q_PART=2(단기 이격밴드 문 · 파는 법): 익절 5 · 손절 7 · 5일 / 익절 8 · 손절 8 · 10일 / 장기 기울기 > 0(긴 오름 속 눌림)만."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import lab
import nrl
import wtools as W

SIZE = lambda r: 2
RANK = lambda r: r.get("단기 이격밴드") or 0
LINE = lab.exit_back_to_line(10)


def hold(test):
    return lambda r: W.weak(r) and test(r)


A = lambda r: (r.get("단기 이격밴드") is not None and r["단기 이격밴드"] <= -1.6)
B = lambda r: (r.get("20일 전 대비") is not None and r["20일 전 대비"] <= -15)
C = lambda r: (r.get("밴드 자리") is not None and r["밴드 자리"] <= 0)

part = os.environ.get("Q_PART", "1")
print(f"== W 1회차({part}): 약세장 되돌림 ==", flush=True)
if part == "1":
    for tag, t in (("단기 이격밴드 ≤ −1.6 · 중기선 회복", A), ("20일 −15% · 중기선 회복", B), ("볼린저 하단 아래 · 중기선 회복", C)):
        W.run(tag, hold(t), size=SIZE, rank=RANK, exit_at=LINE)
else:
    W.run("단기 이격밴드 · 익절 5 손절 7 · 5일", hold(A), size=SIZE, rank=RANK, exit_at=lab.exit_fixed(5, 7, 5))
    W.run("단기 이격밴드 · 익절 8 손절 8 · 10일", hold(A), size=SIZE, rank=RANK, exit_at=lab.exit_fixed(8, 8, 10))
    W.run("단기 이격밴드 + 장기 기울기 > 0 · 중기선 회복", hold(lambda r: A(r) and (r.get("장기 기울기") or -1) > 0),
          size=SIZE, rank=RANK, exit_at=LINE)
print("끝", flush=True)
