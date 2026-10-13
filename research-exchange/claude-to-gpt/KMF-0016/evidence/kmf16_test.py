"""KMF-0016 합성 시험(합치는 규칙만 · 두 봇 신호는 가짜로 바꿔 끼움)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf16 as M  # noqa: E402
import kmf as K  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


b = [("20260105", 544 + 5 * j, 100, 101, 99, 100, 1) for j in range(10)] + [("20260106", 544 + 5 * j, 100, 101, 99, 100, 1) for j in range(5)]


def run(t_want, r_want, rule="trend"):
    o13, o14 = M.M13.signals, M.M14.signals
    M.M13.signals = lambda bb, c: list(t_want)
    M.M14.signals = lambda bb, c: list(r_want)
    try:
        return M.signals(b, {"rule": rule})
    finally:
        M.M13.signals, M.M14.signals = o13, o14


N = None
T = [N, N, 1, N, N, 0, N, N, N, N] + [N] * 5
R = [N, -1, N, N, N, N, N, N, 0, N] + [N] * 5
w = run(T, R)
chk("1 횡보 봇만 원하면 횡보 봇 자리(봉 1에 팖)", w[1] == -1)
chk("2 추세 봇이 원하면 추세 봇으로 뒤집음(봉 2에 삼)", w[2] == 1)
chk("3 추세 봇이 정리하면 횡보 봇이 아직 원하는 자리로(봉 5에 팖)", w[5] == -1)
chk("4 횡보 봇도 정리하면 정리(봉 8에 0)", w[8] == 0)
chk("5 바뀐 봉에서만 신호", [i for i, x in enumerate(w) if x is not None] == [1, 2, 5, 8])
T2 = [N] * 10 + [1, N, N, N, N]
R2 = [N, -1] + [N] * 13                                                        # 첫날 판 채로 날이 바뀜
w = run(T2, R2)
chk("6 날이 바뀌면 원하는 자리는 0에서 다시(전날 횡보 자리 안 이어감)", w[10] == 1 and w[1] == -1 and all(x is None for x in w[11:]))
w = run(T, R, "first")
chk("7 '먼저 든 봇' 규칙은 횡보 봇이 정리할 때까지 추세 봇 무시", w[1] == -1 and w[2] is None)
w2 = M.signals(M.prep(K._rows_before("20260210"))[:300], M.grid()[0])
w3 = M.signals(M.prep(K._rows_before("20260210"))[:200], M.grid()[0])
chk("8 앞 200봉만 줘도 그 앞 신호가 같음(미래 안 봄 · 실제 자료)", w2[:200] == w3)
chk("9 −25p · 칸 3개 · 잣대 2.32 · 시험 2 잠금 없으면 멈춤", K.DAY_STOP == -25.0 and len(M.grid()) == 3 and M.TEST2_MIN_PER_DAY == 2.32 and not M.TEST2_OK.exists())
chk("10 잠금 통과", bool(M.verify_inputs()))
print(f"모두 통과 {ok}개")
