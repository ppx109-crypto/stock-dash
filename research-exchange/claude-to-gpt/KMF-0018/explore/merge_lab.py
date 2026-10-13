"""KMF-0018 탐색 — v12a(사용자 실전 봇 · 클로드 재생기 원장)와 KMF-0017을 1계약으로 합치기.
사용자 2026-10-13 "1계약으로 합병해보자".
- 1분봉 위에서 셈(K.simulate 그대로: 판단 = 그 분 종가 · 체결 = 다음 분 시가 · 하루 −25p · 편도 0.04p · 15:30 정리).
- v12a 자리: 원장 진입 판단 분 = 진입시각 라벨 + 4(5분봉 마감) · 청산 판단 분 = 청산가가 종가로 맞는 분(라벨 + 0 또는 + 4) · 못 맞추면 라벨 분.
- KMF-0017 자리: 5분봉 의도(마지막 분 라벨)를 그 분부터 이어 씀.
python3 merge_lab.py <v12a 원장 csv>"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K  # noqa: E402
import kmf17 as M17  # noqa: E402
import kmf16 as M16  # noqa: E402

K.DAY_STOP = -25.0


def kmf_intent_by_minute(rows):
    b = M17.prep(rows)
    want = M17.signals(b, M17.grid()[0])
    cur, day, out = 0, None, {}
    for i, x in enumerate(want):
        if b[i][0] != day:
            day, cur = b[i][0], 0
        if x in (1, -1, 0):
            cur = x
        elif x == "L0" and cur > 0:
            cur = 0
        elif x == "S0" and cur < 0:
            cur = 0
        out[(b[i][0], b[i][1])] = cur
    return out


def v12a_spans(path, rows):
    close = {(r[0], r[1]): r[5] for r in rows}
    spans = defaultdict(list)
    for t in list(csv.reader(open(path, encoding="utf-8-sig")))[1:]:
        d = t[0].replace("-", "")
        side = 1 if t[1] == "LONG" else -1
        h, m = map(int, t[2][:5].split(":")); e = h * 60 + m + 4
        h, m = map(int, t[4][:5].split(":")); L = h * 60 + m
        x = L
        for k in (0, 4, 1, 2, 3, 5):
            if abs(close.get((d, L + k), -1) - float(t[5])) < 1e-6:
                x = L + k; break
        spans[d].append((e, x, side, t[10]))
    return spans


def run(vpath):
    rows = K._rows_before(M17.END)
    ki = kmf_intent_by_minute(rows)
    vs = v12a_spans(vpath, rows)
    V, KK = [], []
    cur_k, day = 0, None
    for r in rows:
        d, m = r[0], r[1]
        if d != day:
            day, cur_k = d, 0
        cur_k = ki.get((d, m), cur_k)
        v = 0
        for e, x, s, _ in vs.get(d, []):
            if e <= m < x:
                v = s
        V.append(v); KK.append(cur_k)
    rules = {
        "v12a만": V,
        "KMF-0017만": KK,
        "v12a 우선": [v if v else k for v, k in zip(V, KK)],
        "KMF 우선": [k if k else v for v, k in zip(V, KK)],
        "같은 방향일 때만": [v if v and v == k else 0 for v, k in zip(V, KK)],
        "v12a 우선 · 반대면 쉼": [v if v and (k == 0 or k == v) else (0 if v else k) for v, k in zip(V, KK)],
    }
    top10 = M17.TOP10_KMF16
    out = {}
    for name, want in rules.items():
        days, trades = K.simulate(rows, want)
        vals = sorted(days.items())
        mon = defaultdict(float)
        for d, p in vals:
            mon[d[:6]] += p
        rest = {d: p for d, p in days.items() if d not in top10}
        top_own = sorted(days.values(), reverse=True)
        out[name] = {"합계": round(sum(days.values()), 2), "거래": len(trades),
                     "하루 최악": min(vals, key=lambda x: x[1]), "가장 나쁜 달": min(((round(p, 2), m) for m, p in mon.items())),
                     "손해 달": sum(1 for p in mon.values() if p < 0),
                     "앞 01~05": round(sum(p for d, p in vals if d < "20260601"), 2), "뒤 06~10": round(sum(p for d, p in vals if d >= "20260601"), 2),
                     "KMF16 위10일 뺀 177일": round(sum(rest.values()), 2), "자기 위10일 뺀 합": round(sum(top_own[10:]), 2),
                     "달별": {m: round(p, 1) for m, p in sorted(mon.items())}}
    return out


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False, indent=1, default=str))
