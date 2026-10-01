"""G11 — 시장 폭 문턱의 RNA(사용자 2026-10-02: 미니코스피 v11의 '가변 OPEN 문턱'처럼 고정 50% 대신 최근 분위).
문턱(날) = 그날 '앞' n거래일 시장 폭의 q분위(그날 값은 안 씀 → 미래 참조 없음). 앞 날이 n/2보다 적으면 고정 50.
VARIANTS: (이름, n, q, 섞기) — 섞기 'or50'이면 '고정 50 넘음' 또는 '분위 넘음이면서 40 넘음'."""
import numpy as np

VARIANTS = {
    "1": (("60일 하위 30%", 60, 0.3, None), ("60일 가운데", 60, 0.5, None), ("50 또는 120일 가운데(40↑)", 120, 0.5, "or50")),
    "2": (("120일 하위 30%", 120, 0.3, None), ("120일 가운데", 120, 0.5, None)),
}


def thresholds(br, n, q):
    days = sorted(br)
    out = {}
    for k, d in enumerate(days):
        past = [br[x] for x in days[max(0, k - n):k] if br[x] is not None]
        out[d] = float(np.quantile(past, q)) if len(past) >= n // 2 else 50.0
    return out


def make_gate(br, n, q, mix=None):
    thr = thresholds(br, n, q)

    def gate(day, b):
        if b is None:
            return False
        t = thr.get(day, 50.0)
        if mix == "or50":
            return b >= 50 or (b >= t and b >= 40)
        return b >= t
    gate.thr = thr
    return gate


def open_share(br, gate, since=None):
    days = [d for d in sorted(br) if (since is None or d >= since) and br[d] is not None]
    fixed = sum(br[d] >= 50 for d in days) / max(len(days), 1) * 100
    rna = sum(gate(d, br[d]) for d in days) / max(len(days), 1) * 100
    return round(fixed), round(rna)
