"""W 5회차(W5) — 약세 · 옆걸음장(시장 폭 50% 아래)에서 외국인 · 기관이 사 모으는 종목(수급 되돌림). 시총 100위 · 2칸씩 · 씨앗 8.
수급 힘 = 그 기간 순매수 합 ÷ 20일 평균 거래량(전날까지). 힘이 큰 것부터 삼.
Q_PART=1: A 외국인+기관 20일 힘 ≥ 0.5 · 15/7/20일 / B A + 20일 수익 −10 ~ +5(값은 안 오름 = 모으는 중) / C 연기금 20일 힘 ≥ 0.2 · 15/7/20일
Q_PART=2: D B · 10/7/15일 / E B + 장기 기울기 > 0 / F 외국인 · 기관 · 투신 모두 10일 플러스 · 개인 마이너스 · 20일 수익 −10 ~ +5"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import lab
import nrl
import ntools as T
import wtools as W

SIZE = lambda r: 2
FIX = lab.exit_fixed(15, 7, 20)
SHORT = lab.exit_fixed(10, 7, 15)


def power(cols, n=20):
    return lambda r: T.flow_strength(r, n, cols)


fi = power(("외국인", "기관"))
pen = power(("연기금",))
rank_by = lambda f: (lambda r: -(f(r) or -99))
flat = lambda r: -10 <= (r.get("20일 전 대비") or -99) <= 5
A = lambda r: W.weak(r) and (fi(r) or -9) >= 0.5
B = lambda r: A(r) and flat(r)


def F(r):
    s = [nrl.flow_sum(r, 10, c) for c in ("외국인", "기관", "투신", "개인")]
    return W.weak(r) and None not in s and s[0] > 0 and s[1] > 0 and s[2] > 0 and s[3] < 0 and flat(r)


part = os.environ.get("Q_PART", "1")
print(f"== W 5회차({part}): 약세장 수급 되돌림 ==", flush=True)
if part == "1":
    W.run("A 외국인+기관 20일 힘 ≥ 0.5 · 15/7/20일", A, size=SIZE, rank=rank_by(fi), exit_at=FIX)
    W.run("B A + 20일 수익 −10 ~ +5 · 15/7/20일", B, size=SIZE, rank=rank_by(fi), exit_at=FIX)
    W.run("C 연기금 20일 힘 ≥ 0.2 · 15/7/20일", lambda r: W.weak(r) and (pen(r) or -9) >= 0.2, size=SIZE, rank=rank_by(pen), exit_at=FIX)
else:
    W.run("D B · 10/7/15일", B, size=SIZE, rank=rank_by(fi), exit_at=SHORT)
    W.run("E B + 장기 기울기 > 0", lambda r: B(r) and (r.get("장기 기울기") or -9) > 0, size=SIZE, rank=rank_by(fi), exit_at=FIX)
    W.run("F 넷 모두(외 · 기 · 투 +, 개 −) 10일 · 값 평평", F, size=SIZE, rank=rank_by(fi), exit_at=FIX)
print("끝", flush=True)
