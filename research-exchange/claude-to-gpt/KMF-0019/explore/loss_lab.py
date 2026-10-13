"""KMF-0019 탐색 1 — KMF-0017(한 계약 · 이익 잠금) 손실 파악 · MDD.
사용자 2026-10-13 "합병전 신규봇의 손실을 파악하고 mdd를 -15로 축소시키는 연구 시작해줘".
셈은 KMF-0017과 같음(5분봉 · 판단 = 봉 종가 · 체결 = 다음 봉 시가 · 하루 −25p · 편도 0.04p · 15:30 정리).
누가 든 자리인지(T 추세 · R 횡보 · W 시간대)만 더 적음. MDD = 날 끝 누적 손익의 고점 대비 가장 깊은 내림(p · 1계약)."""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K  # noqa: E402
import kmf13 as M13  # noqa: E402
import kmf14 as M14  # noqa: E402
import kmf15 as M15  # noqa: E402
import kmf16 as M16  # noqa: E402
import kmf17 as M17  # noqa: E402

K.DAY_STOP = -25.0


def parts(b):
    T = M16.intent(b, M13.signals(b, M13.grid()[0]))
    R = M16.intent(b, M14.signals(b, M14.grid()[0]))
    W = M16.intent(b, M15.signals(b, M15.grid()[0]))
    return T, R, W


def owner_of(T, R, W, k):
    return "T" if T[k] else ("R" if R[k] else ("W" if W[k] else None))


def sim_owned(b, want, own):
    """K.simulate와 같은 셈 + 거래마다 (날, 들어간 봉 시각, 나온 시각, 방향, 손익, 주인)."""
    days, trades = {}, []
    pos, who, entry, em, real, stopped = 0, None, 0.0, 0, 0.0, False
    for i, r in enumerate(b):
        d, m, o, h, l, c = r[0], r[1], r[2], r[3], r[4], r[5]
        if i == 0 or b[i - 1][0] != d:
            pos, who, entry, real, stopped = 0, None, 0.0, 0.0, False
            days[d] = 0.0
        if i > 0 and b[i - 1][0] == d and not stopped and m <= K.FLAT_AT:
            w = want[i - 1]; pm = b[i - 1][1]
            if w == "L0":
                w = 0 if pos > 0 else None
            elif w == "S0":
                w = 0 if pos < 0 else None
            if w is not None and w != pos:
                if pos:
                    g = pos * (o - entry) - 2 * K.COST
                    real += pos * (o - entry) - K.COST
                    trades.append((d, em, m, pos, round(g, 2), who)); pos = 0
                if w and K.ENTRY_FROM <= pm <= K.ENTRY_TO and real > K.DAY_STOP:
                    pos, entry, em, who = w, o, m, own[i - 1]
                    real -= K.COST
        if pos and not stopped:
            sp = entry + pos * (K.DAY_STOP - real + K.COST)
            if (l <= sp) if pos > 0 else (h >= sp):
                px = min(o, sp) if pos > 0 else max(o, sp)
                real += pos * (px - entry) - K.COST
                trades.append((d, em, m, pos, round(pos * (px - entry) - 2 * K.COST, 2), who + "·멈춤")); pos, stopped = 0, True
        elif not pos and real <= K.DAY_STOP:
            stopped = True
        last = i + 1 == len(b) or b[i + 1][0] != d
        if pos and (m >= K.FLAT_AT or last):
            real += pos * (c - entry) - K.COST
            trades.append((d, em, m, pos, round(pos * (c - entry) - 2 * K.COST, 2), who)); pos = 0
        days[d] = real
    return days, trades


def mdd(days):
    eq, peak, pk_d, worst, span = 0.0, 0.0, None, 0.0, None
    for d, p in sorted(days.items()):
        eq += p
        if eq > peak:
            peak, pk_d = eq, d
        if eq - peak < worst:
            worst, span = eq - peak, (pk_d, d)
    return round(worst, 2), span


def drawdowns(days, n=6):
    """고점 → 다음 새 고점 사이 구간들의 깊이."""
    out, eq, peak, pk_d, low, low_d = [], 0.0, 0.0, None, 0.0, None
    for d, p in sorted(days.items()):
        eq += p
        if eq >= peak:
            if low < peak - 0.001:
                out.append((round(low - peak, 2), pk_d, low_d, d))
            peak, pk_d, low, low_d = eq, d, eq, d
        elif eq < low:
            low, low_d = eq, d
    if low < peak:
        out.append((round(low - peak, 2), pk_d, low_d, "회복 안 됨"))
    return sorted(out)[:n]


def own_list(b, cfg):
    T, R, W = parts(b)
    return [owner_of(T, R, W, k) for k in range(len(b))]


if __name__ == "__main__":
    b = M17.prep(K._rows_before(M17.END))
    cfg = M17.grid()[0]
    want = M17.signals(b, cfg)
    days, tr = sim_owned(b, want, own_list(b, cfg))
    by = defaultdict(lambda: [0, 0.0, 0, 0.0])
    for t in tr:
        k = t[5]; by[k][0] += 1; by[k][1] += t[4]
        if t[4] < 0:
            by[k][2] += 1; by[k][3] += t[4]
    hour = defaultdict(float); side = defaultdict(float)
    for t in tr:
        hour[t[1] // 60] += t[4]; side["롱" if t[3] > 0 else "숏"] += t[4]
    loss_days = sorted(days.items(), key=lambda x: x[1])[:12]
    out = {"합계": round(sum(days.values()), 2), "MDD": mdd(days), "내림 구간 깊은 순": drawdowns(days),
           "주인별 [거래, 손익, 손해 거래, 손해 합]": {k: [v[0], round(v[1], 2), v[2], round(v[3], 2)] for k, v in by.items()},
           "들어간 시각(시)별 손익": {h: round(v, 1) for h, v in sorted(hour.items())}, "방향별": {k: round(v, 1) for k, v in side.items()},
           "나쁜 날 12": [(d, round(v, 2)) for d, v in loss_days],
           "−25 멈춤 날": sum(1 for v in days.values() if v <= -24.99), "손해 날": sum(1 for v in days.values() if v < 0), "날 수": len(days)}
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
