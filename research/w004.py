"""W 4회차(W3) — 옆걸음 박스: 시장 폭 50% 아래 날, 긴 추세가 평평한(장기 기울기 −0.3 ~ +0.3) 종목이 20일 볼린저 띠 아래쪽(밴드 자리 ≤ 0.1)에 오면 삼.
시총 100위 · 2칸씩 · 띠 아래쪽 깊은 것부터 · 씨앗 8.
Q_PART=1: A 중기선 회복(15일) · B 익절 6 손절 6 · 15일 · C 60일 고점 −8 ~ −20% 안에서 띠 아래(0.2) · 중기선 회복
Q_PART=2: A인데 시장 폭 상관없이(모든 날 · 견줌) · A + 단기 이격밴드 ≤ −1 · A인데 밴드 자리 ≤ 0(띠 밖)."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import lab
import wtools as W

SIZE = lambda r: 2
RANK = lambda r: r.get("밴드 자리") if r.get("밴드 자리") is not None else 9
LINE = lab.exit_back_to_line(15)
flat = lambda r: r.get("장기 기울기") is not None and -0.3 <= r["장기 기울기"] <= 0.3
low = lambda r, edge=0.1: r.get("밴드 자리") is not None and r["밴드 자리"] <= edge
A = lambda r: flat(r) and low(r)
part = os.environ.get("Q_PART", "1")
print(f"== W 4회차({part}): 옆걸음 박스 ==", flush=True)
if part == "1":
    W.run("A 평평 + 띠 아래쪽 · 중기선 회복", lambda r: W.weak(r) and A(r), size=SIZE, rank=RANK, exit_at=LINE)
    W.run("B 평평 + 띠 아래쪽 · 6/6/15일", lambda r: W.weak(r) and A(r), size=SIZE, rank=RANK, exit_at=lab.exit_fixed(6, 6, 15))
    W.run("C 60일 고점 −8 ~ −20% · 띠 아래(0.2) · 중기선 회복",
          lambda r: W.weak(r) and flat(r) and low(r, 0.2) and -20 <= (r.get("60일 전고점 대비") or 0) <= -8, size=SIZE, rank=RANK, exit_at=LINE)
else:
    W.run("A · 시장 폭 상관없이(견줌)", A, size=SIZE, rank=RANK, exit_at=LINE)
    W.run("A + 단기 이격밴드 ≤ −1", lambda r: W.weak(r) and A(r) and (r.get("단기 이격밴드") or 0) <= -1, size=SIZE, rank=RANK, exit_at=LINE)
    W.run("A · 밴드 자리 ≤ 0(띠 밖)", lambda r: W.weak(r) and flat(r) and low(r, 0.0), size=SIZE, rank=RANK, exit_at=LINE)
print("끝", flush=True)
