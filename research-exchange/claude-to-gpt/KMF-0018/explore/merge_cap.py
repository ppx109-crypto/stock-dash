"""KMF-0018 탐색 2 — v12a 우선 1계약 + KMF 몫 하루 손실 한도 C(넘으면 그날 KMF 의도는 버림 · v12a는 계속).
K.simulate와 같은 체결 셈(다음 분 시가 · 하루 −25p 멈춤 · 15:30 정리 · 편도 0.04p)에 '누가 든 자리인지'만 더함.
KMF 몫 손익 = KMF가 든 자리의 실현 + 지금 평가(판단 시각 종가)."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_lab as ML  # noqa: E402
K = ML.K


def sim(rows, V, KK, cap, skip_after_v=False):
    days, ntr = {}, 0
    pos, own, entry, real, kreal, stopped, kdone, vseen = 0, None, 0.0, 0.0, 0.0, False, False, False
    for i, r in enumerate(rows):
        d, m, o, h, l, c = r[0], r[1], r[2], r[3], r[4], r[5]
        if i == 0 or rows[i - 1][0] != d:
            pos, own, entry, real, kreal, stopped, kdone, vseen = 0, None, 0.0, 0.0, 0.0, False, False, False
            days[d] = 0.0
        if i > 0 and rows[i - 1][0] == d and not stopped and m <= K.FLAT_AT:
            pm, pc = rows[i - 1][1], rows[i - 1][5]
            v, k = V[i - 1], KK[i - 1]
            if v:
                vseen = True
            if own == "K" and pos and kreal + pos * (pc - entry) - K.COST <= -cap:
                kdone = True
            if kreal <= -cap:
                kdone = True
            use_k = not kdone and not (skip_after_v and vseen)
            w, who = (v, "V") if v else ((k, "K") if (k and use_k) else (0, None))
            if w != pos:
                if pos:
                    g = pos * (o - entry) - K.COST
                    real += g; ntr += 1
                    if own == "K":
                        kreal += g
                    pos, own = 0, None
                if w and K.ENTRY_FROM <= pm <= K.ENTRY_TO and real > K.DAY_STOP:
                    pos, own, entry = w, who, o
                    real -= K.COST
                    if who == "K":
                        kreal -= K.COST
            elif pos and who and who != own:
                own = who                      # 같은 방향을 다른 쪽이 이어 받음(주문 없음)
        if pos and not stopped:
            stop_px = entry + pos * (K.DAY_STOP - real + K.COST)
            if (l <= stop_px) if pos > 0 else (h >= stop_px):
                px = min(o, stop_px) if pos > 0 else max(o, stop_px)
                real += pos * (px - entry) - K.COST; ntr += 1
                pos, stopped = 0, True
        elif not pos and real <= K.DAY_STOP:
            stopped = True
        last = i + 1 == len(rows) or rows[i + 1][0] != d
        if pos and (m >= K.FLAT_AT or last):
            real += pos * (c - entry) - K.COST; ntr += 1
            pos = 0
        days[d] = real
    return days, ntr


def summ(days, ntr):
    vals = sorted(days.items()); mon = defaultdict(float)
    for d, p in vals:
        mon[d[:6]] += p
    top = sorted(days.values(), reverse=True)
    return {"합계": round(sum(days.values()), 2), "거래": ntr, "하루 최악": [vals and min(vals, key=lambda x: x[1])[0], round(min(days.values()), 2)],
            "가장 나쁜 달": min((round(p, 2), m) for m, p in mon.items()), "손해 달": sum(1 for p in mon.values() if p < 0),
            "앞 01~05": round(sum(p for d, p in vals if d < "20260601"), 2), "뒤 06~10": round(sum(p for d, p in vals if d >= "20260601"), 2),
            "177일": round(sum(p for d, p in vals if d not in ML.M17.TOP10_KMF16), 2), "자기 위10일 뺀 합": round(sum(top[10:]), 2),
            "달별": {m: round(p, 1) for m, p in sorted(mon.items())}}


if __name__ == "__main__":
    rows = K._rows_before(ML.M17.END)
    ki = ML.kmf_intent_by_minute(rows); vs = ML.v12a_spans(sys.argv[1], rows)
    V, KK, cur, day = [], [], 0, None
    for r in rows:
        if r[0] != day:
            day, cur = r[0], 0
        cur = ki.get((r[0], r[1]), cur)
        v = 0
        for e, x, s, _ in vs.get(r[0], []):
            if e <= r[1] < x:
                v = s
        V.append(v); KK.append(cur)
    out = {}
    for cap in (999, 25, 15, 10, 7, 5):
        out[f"v12a 우선 · KMF 몫 −{cap}"] = summ(*sim(rows, V, KK, cap))
    out["v12a 우선 · v12a 첫 거래 뒤 KMF 끝"] = summ(*sim(rows, V, KK, 999, True))
    out["v12a만(같은 셈)"] = summ(*sim(rows, V, [0] * len(V), 999))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
