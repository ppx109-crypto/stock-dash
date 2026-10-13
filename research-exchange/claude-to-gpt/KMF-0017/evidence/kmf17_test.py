"""KMF-0017 합성 시험(합치기 · 이익 잠금 · 세 봇 신호는 가짜로 바꿔 끼움)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf17 as M  # noqa: E402
import kmf as K  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def mk(prices, d="20260105"):
    rows, prev = [], prices[0]
    for j, p in enumerate(prices):
        rows.append((d, 544 + 5 * j, prev, max(prev, p) + 0.1, min(prev, p) - 0.1, p, 1)); prev = p
    return rows


def run(b, t, r, w, cfg):
    o = (M.M13.signals, M.M14.signals, M.M15.signals)
    M.M13.signals = lambda bb, c: list(t); M.M14.signals = lambda bb, c: list(r); M.M15.signals = lambda bb, c: list(w)
    try:
        return M.signals(b, cfg)
    finally:
        M.M13.signals, M.M14.signals, M.M15.signals = o


N = None
n = 30
b = mk([100.0] * n)
T = [N] * n; R = [N] * n; W = [N] * n
R[2] = -1; T[4] = 1; T[6] = 0; W[8] = 1; R[9] = 0
w = run(b, T, R, W, M.grid()[0])
chk("1 횡보만 → 팖 · 추세 원하면 뒤집음 · 추세 정리 뒤 횡보 자리", w[2] == -1 and w[4] == 1 and w[6] == -1)
chk("2 횡보 봇 정리 뒤 시간대 봇 자리(봉 9에 삼)", w[9] == 1)
w0 = run(b, T, R, W, M.grid()[1])
chk("3 시간대 봇 끈 칸(W0)은 횡보 정리 뒤 정리", w0[9] == 0)
up = [100.0 + 2 * j for j in range(12)] + [124.0 - 2 * j for j in range(18)]  # 오르다 내림
b2 = mk(up)
T2 = [N] * n; T2[1] = 1                                                          # 봉 1에 삼 → 봉 2 시가 102 체결
w = run(b2, T2, [N] * n, [N] * n, M.grid()[0])
# 봉 종가 손익: 봉 11 종가 122 → +20 − 0.08 ... 최고는 봉 11(122) · L40 못 미침 → 잠금 안 걸림
chk("4 그날 최고 손익이 +40 못 넘으면 잠금 안 걸림(정리 신호 없음)", 0 not in w)
big = [100.0 + 5 * j for j in range(12)] + [155.0 - 4 * j for j in range(18)]    # 크게 오르다 내림
b3 = mk(big)
w = run(b3, T2, [N] * n, [N] * n, M.grid()[0])
k0 = next(i for i, x in enumerate(w) if x == 0)
# 체결 105(봉 2 시가) · 봉 11 · 12 종가 155 → +49.92(최고) · 봉 15 종가 143 → +37.92(내려옴 12 · 안 걸림) · 봉 16 종가 139 → +33.92(내려옴 16 ≥ 15 · 걸림)
chk("5 최고 +40 넘은 뒤 15 넘게 내려온 봉에서 정리(0) · 그 뒤 더 안 듦", k0 == 16 and all(x is None for x in w[k0 + 1:]))
w = run(b3, T2, [N] * n, [N] * n, M.grid()[5])
chk("6 잠금 끈 칸은 정리 안 함", 0 not in w)
w2 = M.signals(M.prep(K._rows_before("20260210"))[:300], M.grid()[0])
w3 = M.signals(M.prep(K._rows_before("20260210"))[:200], M.grid()[0])
chk("7 앞 200봉만 줘도 그 앞 신호가 같음(실제 자료)", w2[:200] == w3)
chk("8 −25p · 칸 6개 · 잣대 2.29 · 시험 2 10-14부터 · 잠금 없으면 멈춤", K.DAY_STOP == -25.0 and len(M.grid()) == 6 and M.TEST2_MIN_PER_DAY == 2.29 and M.TEST2_FROM == "20261014" and not M.TEST2_OK.exists())
chk("9 잠금 통과(수급 파일 포함)", "market-data/investor_KSP.json" in M.verify_inputs())
print(f"모두 통과 {ok}개")
