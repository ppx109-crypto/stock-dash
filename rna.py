"""EMA의 RNA — 고정값(DNA)이 아니라 날마다 움직이는 이동평균의 상태들.

한 종목의 종가 줄에서, 주어진 EMA 기간들로 날마다 다음을 만듭니다(모두 그날 종가까지만 씀).
- 배열: 짧은 선이 바로 긴 선 위에 있는 짝의 수(0~선 수−1). 정배열 = 모두 줄 섬.
- 지속: 지금 배열 점수가 며칠째 이어지는지 · 정배열이 며칠째인지.
- 이격도: 종가 ÷ EMA − 1 (%), 선마다.
- 이격밴드: 이격도가 지난 120일 평균에서 몇 표준편차 떨어졌는지, 선마다.
- 이격속도: 이격도가 k일 사이 얼마나 벌어졌는지(%p), k = 1 · 3 · 5 · 10.
- 기울기: EMA가 5일 사이 몇 % 올랐는지, 선마다.
- 가속도: 기울기가 5일 사이 얼마나 바뀌었는지(%p), 선마다.
"""
import numpy as np

SETS = {"A": (5, 20, 60, 120, 180), "B": (5, 10, 20, 60, 120, 240)}
SPEEDS = (1, 3, 5, 10)
STEP = 5
BAND = 120


def ema(closes, span):
    a = np.asarray(closes, float)
    out = np.empty_like(a)
    k = 2.0 / (span + 1)
    out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = out[i - 1] + k * (a[i] - out[i - 1])
    out[:span] = np.nan            # 처음 span일은 아직 믿지 않음
    return out


def run_length(flags):
    out = np.zeros(len(flags), int)
    for i, f in enumerate(flags):
        out[i] = (out[i - 1] + 1 if i else 1) if f else 0
    return out


def _shift(a, k):
    out = np.full_like(a, np.nan)
    out[k:] = a[:-k]
    return out


def states(closes, spans):
    """{이름: 배열(날짜 길이)} — 이름 예: '배열', '정배열', '배열지속', '정배열지속', '이격20', '이격밴드20', '이격속도20_5', '기울기20', '가속도20'."""
    c = np.asarray(closes, float)
    lines = {s: ema(c, s) for s in spans}
    out = {}
    pairs = [lines[a] > lines[b] for a, b in zip(spans, spans[1:])]
    order = np.sum(pairs, axis=0).astype(float)
    valid = ~np.isnan(lines[spans[-1]])
    order[~valid] = np.nan
    out["배열"] = order
    full = (order == len(spans) - 1)
    out["정배열"] = full.astype(float)
    out["정배열지속"] = run_length(full).astype(float)
    same = np.r_[False, order[1:] == order[:-1]]
    streak = np.zeros(len(c))
    for i in range(len(c)):
        streak[i] = streak[i - 1] + 1 if i and same[i] else 1
    out["배열지속"] = streak
    for s, line in lines.items():
        gap = (c / line - 1) * 100
        out[f"이격{s}"] = gap
        roll = np.full(len(c), np.nan)
        sd = np.full(len(c), np.nan)
        for i in range(BAND, len(c)):
            w = gap[i - BAND:i]
            w = w[~np.isnan(w)]
            if len(w) > 30:
                roll[i], sd[i] = w.mean(), w.std()
        out[f"이격밴드{s}"] = np.where(sd > 0, (gap - roll) / sd, np.nan)
        for k in SPEEDS:
            out[f"이격속도{s}_{k}"] = gap - _shift(gap, k)
        slope = (line / _shift(line, STEP) - 1) * 100
        out[f"기울기{s}"] = slope
        out[f"가속도{s}"] = slope - _shift(slope, STEP)
    return out
