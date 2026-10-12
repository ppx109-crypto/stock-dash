"""KMF-0014 합성 시험."""
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf14 as M  # noqa: E402
import kmf as K  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def mk(prices, d0=20260105):
    rows, k = [], 0
    for di in range(len(prices) // 76 + 1):
        for j in range(76):
            if k >= len(prices):
                break
            p = prices[k]; rows.append((str(d0 + di), 544 + 5 * j, p, p + 0.5, p - 0.5, p, 1)); k += 1
    return rows


pick = M.grid()[0]
rng = np.random.default_rng(1)
flat = list(100 + np.cumsum(rng.normal(0, 0.3, 300)) * 0.2)                  # 평평한 잔물결
S0 = 229                                                                       # 넷째 날 둘째 봉(09:09 · 그날 아직 든 자리 없음)
spike_up = flat[:S0] + [flat[S0 - 1] + 6] * 21                                  # 평평하다 갑자기 위로 튐
w = M.signals(mk(spike_up), pick)
chk("1 평평한 흐름에서 위로 크게 벌어지면 팖", w[S0] == -1 and 1 not in w[S0:])
spike_dn = flat[:S0] + [flat[S0 - 1] - 6] * 21
w = M.signals(mk(spike_dn), pick)
chk("2 아래로 크게 벌어지면 삼", w[S0] == 1)
trend = [100 + 0.8 * i for i in range(300)]
w = M.signals(mk(trend), pick)
chk("3 큰 흐름 선이 가파르면(추세) 안 듦", all(x is None for x in w))
run = flat[:S0] + [flat[S0 - 1] + 6] + [flat[S0 - 1] + 6 + 3 * i for i in range(1, 20)]
w = M.signals(mk(run), pick)
k = next(i for i, x in enumerate(w) if x == -1)
chk("4 판 뒤 3 × ATR 넘게 오르면 정리(0)", 0 in w[k + 1:])
w2 = M.signals(mk(run)[:240], pick)
chk("5 앞 240봉만 줘도 그 앞 신호가 같음(미래 안 봄)", w2 == w[:240])
chk("6 하루 멈춤 −25p · 고른 칸 + 이웃 10 · 이름 겹침 없음", K.DAY_STOP == -25.0 and len(M.grid()) == 11 and len({M.name(c) for c in M.grid()}) == 11)
chk("7 시험 2는 잠금 동의 없으면 멈춤 · 잣대 1.09p", not M.TEST2_OK.exists() and M.TEST2_MIN_PER_DAY == 1.09)
chk("8 잠금 통과", bool(M.verify_inputs()))
print(f"모두 통과 {ok}개")
