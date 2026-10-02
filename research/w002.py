"""W 2회차(W4) — 약세 · 옆걸음장(시장 폭 50% 아래)에서 혼자 강한 종목. 시총 100위 · 2칸씩 · 60일 수익 큰 것부터 · 씨앗 8.
Q_PART=1: A 혼자 정배열(간격 19 ~ 53%) · 정배열 깨짐/−10%/+8→+1로 팖(1일봉 정배열 쪽 파는 법) / B 52주 신고가 근처(−3% 안) · 익절 15 손절 7 · 20일 /
          C 60일 +25% · 20일 플러스 · 익절 15 손절 7 · 20일
Q_PART=2: A + 공통 수급(가르침) / A인데 시장 폭 40% 아래만 / A를 신고가 근처로 좁힘."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import lab
import nrl
import wtools as W

SIZE = lambda r: 2
RANK = lambda r: -(r.get("60일 전 대비") or -99)
FIX = lab.exit_fixed(15, 7, 20)


def alone(r):
    f = nrl.F.form_of(nrl.shape, r)
    return bool(f.get("정배열") and f.get("간격") is not None and 19 <= f["간격"] < 53)


near_high = lambda r: (r.get("250일 전고점 대비") is not None and r["250일 전고점 대비"] >= -3)
strong = lambda r: (r.get("60일 전 대비") or -99) >= 25 and (r.get("20일 전 대비") or -99) > 0
part = os.environ.get("Q_PART", "1")
print(f"== W 2회차({part}): 약세장에서 혼자 강한 종목 ==", flush=True)
if part == "1":
    W.run("A 혼자 정배열 · 정배열 쪽 파는 법", lambda r: W.weak(r) and alone(r), size=SIZE, rank=RANK, exit_at=nrl.broken)
    W.run("B 52주 신고가 근처 · 15/7/20일", lambda r: W.weak(r) and near_high(r), size=SIZE, rank=RANK, exit_at=FIX)
    W.run("C 60일 +25% · 15/7/20일", lambda r: W.weak(r) and strong(r), size=SIZE, rank=RANK, exit_at=FIX)
else:
    W.run("A + 수급(가르침)", lambda r: W.weak(r) and alone(r) and nrl.teacher(r), size=SIZE, rank=RANK, exit_at=nrl.broken)
    W.run("A · 시장 폭 40% 아래만", lambda r: nrl.BR.get(r["date"], 100) < 40 and alone(r), size=SIZE, rank=RANK, exit_at=nrl.broken)
    W.run("A + 신고가 근처", lambda r: W.weak(r) and alone(r) and near_high(r), size=SIZE, rank=RANK, exit_at=nrl.broken)
print("끝", flush=True)
