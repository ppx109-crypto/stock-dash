"""1시간봉 RL 도구 — 자료 읽기 · 그날 종목 모음 · 앞날 손익(다음 봉 시가에 삼) · 사건 연구 · 미래 참조 가드.

미래 참조 막기(docs/RL-1H-PLAN.md):
- 신호는 봉이 닫힌 뒤 그 봉까지의 값으로만 셈 → **다음 봉 시가**에 사고, k봉 뒤 종가에 판다고 봄.
- 그날 종목 모음은 **전 거래일** 시총 순위로 정함(오늘 오른 종목만 고르지 않게).
- 일봉 재료(수급 등)는 전날 것까지만.
"""
import bisect
from pathlib import Path

import numpy as np

import rna

HOME = Path("hourly-data")
COST = 0.30          # 왕복 비용 %(수수료 · 세금 · 미끄러짐을 넉넉히)
EARLY = ("2023100100", "2025040100")   # 앞 반
LATE = ("2025040100", "2099010100")    # 뒤 반


def load(codes=None):
    """{code: {'t': [YYYYMMDDHH], 'o','h','l','c','v': np.array}} — 시각 순."""
    found = {}
    for folder in sorted(HOME.iterdir()):
        if not folder.is_dir() or (codes and folder.name not in codes):
            continue
        lines = []
        for f in sorted(folder.glob("*.csv")):
            lines += [ln.split(",") for ln in f.read_text(encoding="utf-8").splitlines() if ln.count(",") == 5]
        if len(lines) < 200:
            continue
        lines.sort(key=lambda p: p[0])
        arr = np.array([[float(x) for x in p[1:]] for p in lines])
        found[folder.name] = {"t": [p[0] for p in lines], "o": arr[:, 0], "h": arr[:, 1], "l": arr[:, 2],
                              "c": arr[:, 3], "v": arr[:, 4]}
    return found


def ranks_by_day():
    """{YYYYMMDD: {code: 시총 순위}} — 일봉 표에서. 오늘 모음에는 **전 거래일** 순위를 씀."""
    import caps
    import lab
    rows = lab.load()
    caps.tag(rows, 150)
    got = {}
    for r in rows:
        if r["date"] >= "20230801" and r.get(caps.RANK):
            got.setdefault(r["date"], {})[r["code"]] = r[caps.RANK]
    return got


class Universe:
    """in(code, t): t시 봉의 날 기준 전 거래일 시총 순위가 top 안인가."""

    def __init__(self, ranks, top=100):
        self.days = sorted(ranks)
        self.ranks = ranks
        self.top = top

    def ok(self, code, stamp):
        k = bisect.bisect_left(self.days, stamp[:8]) - 1      # 오늘보다 앞선 마지막 거래일
        if k < 0:
            return False
        r = self.ranks[self.days[k]].get(code)
        return r is not None and r <= self.top


def forward(b, i, k, cost=COST):
    """i봉에서 신호 → i+1봉 시가에 사서 i+k봉 종가에 팜(%, 비용 뺌). 자료가 모자라면 None."""
    if i + k >= len(b["c"]) or i + 1 >= len(b["o"]):
        return None
    return (b["c"][i + k] / b["o"][i + 1] - 1) * 100 - cost


def edges(mask):
    """거짓 → 참으로 바뀐 봉만(겹치는 신호를 한 번으로)."""
    m = np.asarray(mask, bool)
    return np.flatnonzero(m & ~np.r_[False, m[:-1]])


def study(data, signal, uni, ks=(1, 3, 7, 14, 35), edge=True, periods=(("앞", EARLY), ("뒤", LATE))):
    """signal(code, b, st) → 봉마다 참/거짓 배열. 기간마다 k봉 앞날 손익의 평균 · 가운데 · 이긴 몫 · 건수."""
    out = {}
    for name, (lo, hi) in periods:
        got = {k: [] for k in ks}
        for code, b in data.items():
            if code.startswith("K"):          # 지수 폴더(KOSPI · KOSDAQ)는 종목이 아님
                continue
            mask = signal(code, b)
            idx = edges(mask) if edge else np.flatnonzero(mask)
            for i in idx:
                t = b["t"][i]
                if not (lo <= t < hi) or not uni.ok(code, t):
                    continue
                for k in ks:
                    f = forward(b, i, k)
                    if f is not None:
                        got[k].append(f)
        out[name] = {k: (len(v), float(np.mean(v)) if v else None, float(np.median(v)) if v else None,
                         float(np.mean(np.asarray(v) > 0) * 100) if v else None) for k, v in got.items()}
    return out


def show(tag, res, ks=(1, 3, 7, 14, 35)):
    parts = [f"  {tag:34s}"]
    for name, by in res.items():
        n = by[ks[0]][0]
        cells = " ".join(f"{k}봉 {by[k][1]:+.2f}({by[k][3]:.0f}%)" if by[k][1] is not None else f"{k}봉 -" for k in ks)
        parts.append(f"{name} {n:>6}건 {cells}")
    print(" | ".join(parts), flush=True)


_ST = {}


def states(code, b, spans_key="A"):
    key = (code, spans_key)
    if key not in _ST:
        _ST[key] = rna.states(b["c"], rna.SETS[spans_key])
    return _ST[key]


def guard_prefix(b, spans_key="A", cuts=(300, 900, 1500)):
    """앞부분만 넣고 센 RNA 값이 전체로 센 값의 같은 봉과 같은가(뒤 봉이 앞 값을 바꾸면 미래 참조)."""
    full = rna.states(b["c"], rna.SETS[spans_key])
    for n in cuts:
        if n >= len(b["c"]):
            continue
        part = rna.states(b["c"][:n], rna.SETS[spans_key])
        for name, arr in part.items():
            a, z = arr[n - 1], full[name][n - 1]
            if not ((np.isnan(a) and np.isnan(z)) or abs(a - z) < 1e-9):
                return f"{name} {n}봉째 {a} ≠ {z}"
    return None
