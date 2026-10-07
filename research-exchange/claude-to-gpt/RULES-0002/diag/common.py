"""RULES-0002 공통: 기준점 폴더 고정 · 정확한 경계 비교 · 호가 단위 · 부트스트랩. 운영 모듈 · 네트워크 · 계좌 없음."""
import os
import socket
import sys
from fractions import Fraction as Fr
from pathlib import Path

import numpy as np


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지(진단 재생)")


def lock_base(base):
    """꺼낸 폴더를 맨 앞 경로 · 작업 폴더로 · 네트워크 막기 · 키 환경변수 지우기."""
    socket.socket = _blocked
    socket.create_connection = _blocked
    for k in list(os.environ):
        if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
            os.environ.pop(k)
    base = str(Path(base).resolve())
    os.chdir(base)
    sys.path[:0] = [base, base + "/research"]
    return base


def module_origins(base, main="/home/user/stock-dash"):
    """불러온 모듈 가운데 운영 폴더에서 온 것이 있으면 목록으로(없어야 함)."""
    bad = []
    for name, m in list(sys.modules.items()):
        f = getattr(m, "__file__", None) or ""
        if f.startswith(main + "/") and not f.startswith(base):
            bad.append((name, f))
    return bad


def read_patched(path, base, main="/home/user/stock-dash"):
    """원본 파일을 읽어 절대 경로만 꺼낸 폴더로 바꾼 글(원본 파일은 안 고침)."""
    return Path(path).read_text(encoding="utf-8").replace(main, base)


# ── 정확한 경계(교차곱) ──
def ge(close, price, pct):      # (close/price − 1)×100 ≥ pct
    return Fr(close) * 100 >= Fr(price) * (100 + pct)


def le(close, price, pct):      # ≤ pct
    return Fr(close) * 100 <= Fr(price) * (100 + pct)


def lt(close, price, pct):      # < pct
    return Fr(close) * 100 < Fr(price) * (100 + pct)


def tick(p):
    """2023-01-25 뒤 통합 호가 단위(원)."""
    for lim, t in ((2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500)):
        if p < lim:
            return t
    return 1000


def boundary_on_tick(price, pct):
    """진입가 × (1 + pct/100)이 정수이고 그 가격대 호가 단위의 배수인가(그 경계에 정확히 닿는 가격이 호가상 가능한가)."""
    b = Fr(price) * (100 + pct) / 100
    if b.denominator != 1 or b <= 0:
        return False
    v = int(b)
    return v % tick(v) == 0


RNG = np.random.default_rng(23)


def boot_ci(x, reps=2000, groups=None):
    """평균의 95% CI. groups가 있으면 묶음(종목) 단위 부트스트랩."""
    x = np.asarray(x, float)
    if len(x) == 0:
        return None
    if groups is None:
        m = [x[RNG.integers(0, len(x), len(x))].mean() for _ in range(reps)]
    else:
        g = np.asarray(groups)
        u = np.unique(g)
        idx = {k: np.flatnonzero(g == k) for k in u}
        m = []
        for _ in range(reps):
            pick = u[RNG.integers(0, len(u), len(u))]
            m.append(x[np.concatenate([idx[k] for k in pick])].mean())
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def block_boot_ci(d, reps=2000, block=20):
    """날마다 짝 차이의 평균 95% CI(이어 붙인 블록)."""
    d = np.asarray(d, float)
    n = len(d)
    if n < block * 2:
        return None
    m = []
    for _ in range(reps):
        starts = RNG.integers(0, n - block + 1, n // block + 1)
        s = np.concatenate([d[i:i + block] for i in starts])[:n]
        m.append(s.mean())
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def describe(x):
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)), "std": float(x.std(ddof=1)) if len(x) > 1 else 0.0}
