"""REGIME-SW-0052 — 후보 0051에서 '횡보장 인버스' 몫이 정말 보탬인지 · 더 크면 나은지(0051 결과: side_inv 0.2가 격자 끝).
- 규칙은 0051 최종 그대로: n 24 · persist 3 · confirm r10m5 · above_only · band None · lev_vt None · 하락 1일봉만.
- 격자(18판): up_lev {0.15 · 0.20 · 0.25} × side_inv {0 · 0.1 · 0.2 · 0.3 · 0.4 · 0.5}(인버스 114800 · 1배)
- 고르기 · 손실 고원은 regime_rules4와 같음(세 장 각각 하루 −15% · 달 −10% · 작은 규칙 이웃 n 20 · 28 · persist 2 · 4 · r10m4 · r10m6도 모두 같은 잣대 안 · 더 번 몫 절반 이상).
- 판정: ROBUST_CANDIDATE / NO_ROBUST. 덧붙여 '횡보 인버스 0 대 고른 값'의 연수익 · 손실 차를 보고(같은 레버리지끼리).
REG_BOX=REGIME-SW-0052 python3 research/regime_rules5.py"""
import os
import sys

os.environ.setdefault("REG_BOX", "REGIME-SW-0052")
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_rules4 as R4  # noqa: E402

R4.NS = [24]
R4.PS = [3]
R4.LEVS = [0.15, 0.20, 0.25]
R4.SIDES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
R4.LOG = R4.D.BOX / "LOG.md"

if __name__ == "__main__":
    R4.main()
