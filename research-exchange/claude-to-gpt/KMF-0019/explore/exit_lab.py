"""KMF-0019 탐색 4 — 손실은 짧게 · 이익은 길게(v12a식 출구)로 세 봇(T 추세 · R 횡보 · W 시간대) 다시 셈.
1분봉 위에서 셈: 들기 = 5분봉 의도가 새로 켜진 봉(마지막 분 라벨) 다음 분 시가 · 편도 0.04p · 15:30 정리.
출구(골라 켬):
  N  — 들어간 뒤 N분이 지나도 평가 손익 ≤ 0 이면 정리(조기 손절)
  B  — 신호 5분봉 반대 끝에 멈춤(봉 안에서 닿으면 그 값 · 시가가 넘었으면 시가)
  n  — 1분 채널 트레일: 1분 종가가 앞 n분 저점(롱) / 고점(숏)을 넘어서면 정리
  X  — 의도가 꺼지거나 뒤집히면 정리(1) / 무시하고 출구 규칙만(0)
  DS — 하루 멈춤 · LK — 이익 잠금(그날 +L 뒤 G 내려오면 그날 끝)
정리 뒤에는 의도가 새로 켜질 때까지 다시 안 듦.  python3 exit_lab.py <v12a 원장>"""
import itertools
import json
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "KMF-0018/explore"))
import loss_lab as L  # noqa: E402
import mdd_lab as D  # noqa: E402
import merge_cap as MC  # noqa: E402
K, M13, M14, M15, M16, M17 = L.K, L.M13, L.M14, L.M15, L.M16, L.M17
ML = MC.ML


def intents(b, comp, T, R, W):
    out = {}
    for k, r in enumerate(b):
        v = 0
        for c in comp:
            x = {"T": T, "R": R, "W": W}[c][k]
            if x:
                v = x; break
        out[(r[0], r[1])] = (v, r[3], r[4])
    return out


def run(rows, it, N, B, n, X, DS, LK):
    days, desire = {}, [0] * len(rows)
    i, nr = 0, len(rows)
    while i < nr:
        d = rows[i][0]; j = i
        while j < nr and rows[j][0] == d:
            j += 1
        pos, entry, real, peak, halt, stopped, pend, emin, stop_px, cur = 0, 0.0, 0.0, 0.0, False, False, None, 0, None, 0
        hi = deque(maxlen=n or 1); lo = deque(maxlen=n or 1)
        for k in range(i, j):
            _, m, o, h, l, c = rows[k][:6]
            # ① 앞 분 결정 체결
            if pend is not None and not stopped and m <= K.FLAT_AT:
                tgt, pm, sp = pend
                if tgt != pos:
                    if pos:
                        real += pos * (o - entry) - K.COST; pos = 0
                    if tgt and K.ENTRY_FROM <= pm <= K.ENTRY_TO and real > -DS and not halt:
                        pos, entry, emin = tgt, o, m; real -= K.COST
                        stop_px = sp if B else None
                        if stop_px is not None and ((pos > 0 and stop_px >= o) or (pos < 0 and stop_px <= o)):
                            stop_px = None                 # 시가가 이미 멈춤 밖 → 멈춤 없이(다음 출구에 맡김)
            pend = None
            # ② 봉 안 멈춤: 신호 봉 반대 끝 · 하루 멈춤
            if pos and stop_px is not None and ((l <= stop_px) if pos > 0 else (h >= stop_px)):
                px = min(o, stop_px) if pos > 0 else max(o, stop_px)
                real += pos * (px - entry) - K.COST; pos = 0
            if pos:
                sp2 = entry + pos * (-DS - real + K.COST)
                if (l <= sp2) if pos > 0 else (h >= sp2):
                    px = min(o, sp2) if pos > 0 else max(o, sp2)
                    real += pos * (px - entry) - K.COST; pos = 0; stopped = True
            if not pos and real <= -DS:
                stopped = True
            last = k == j - 1
            if pos and (m >= K.FLAT_AT or last):
                real += pos * (c - entry) - K.COST; pos = 0
            # ③ 분 종가 결정
            tgt = pos
            if not stopped and m < K.FLAT_AT:
                v = it.get((d, m))
                if v is not None:
                    nv, bh, bl = v
                    if nv != cur:                          # 의도 바뀜(5분봉 마감)
                        if nv and nv != pos:
                            tgt = nv; sp = bl if nv > 0 else bh
                            pend = (tgt, m, sp)
                        elif X and pos and nv != pos:
                            tgt = 0
                        cur = nv
                if pos and pend is None:
                    mtm = pos * (c - entry)
                    if N and m - emin >= N and mtm <= 0:
                        tgt = 0
                    if n and len(lo) == n and ((pos > 0 and c < min(lo)) or (pos < 0 and c > max(hi))):
                        tgt = 0
                mt = real + (pos * (c - entry) - K.COST if pos else 0.0)
                peak = max(peak, mt)
                if LK and peak >= LK[0] and mt <= peak - LK[1]:
                    halt = True; tgt = 0
                if pend is None and tgt != pos:
                    pend = (tgt, m, None)
                if halt and pend and pend[0]:
                    pend = (0, m, None) if pos else None
            hi.append(h); lo.append(l)
            desire[k] = pend[0] if pend else pos
        days[d] = real
        i = j
    return days, desire


if __name__ == "__main__":
    rows = K._rows_before(M17.END)
    b = M17.prep(rows)
    T = M16.intent(b, M13.signals(b, M13.grid()[0]))
    R = M16.intent(b, M14.signals(b, M14.grid()[0]))
    W = M16.intent(b, M15.signals(b, M15.grid()[0]))
    vs = ML.v12a_spans(sys.argv[1], rows)
    V = []
    for r in rows:
        v = 0
        for e, x, s, _ in vs.get(r[0], []):
            if e <= r[1] < x:
                v = s
        V.append(v)
    res = []
    comps = ("TRW", "TR", "TW", "T", "R", "W")
    its = {c: intents(b, c, T, R, W) for c in comps}
    for comp, N, B, n, X, DS, LK in itertools.product(comps, (0, 10, 20, 30), (0, 1), (0, 15, 30, 60), (1, 0), (25, 10), ((40, 15), None)):
        days, desire = run(rows, its[comp], N, B, n, X, DS, LK)
        s = D.summ(days)
        rec = {"판": f"{comp}_N{N}_B{B}_n{n}_X{X}_DS{DS}_LK{LK}", **s}
        res.append(rec)
    (HERE / "exit_lab_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res))
    base = [r for r in res if r["판"] == "TRW_N0_B0_n0_X1_DS25_LK(40, 15)"][0]
    print("기준(이 셈으로 KMF-0017에 가까운 판)", json.dumps(base, ensure_ascii=False))
    res.sort(key=lambda x: -x["MDD"])
    print("MDD 얕은 순 12"); [print(json.dumps(x, ensure_ascii=False)) for x in res[:12]]
    for lim in (-15, -20, -25, -33, -40, -50, -70):
        c = [x for x in res if x["MDD"] >= lim]
        if c:
            x = max(c, key=lambda x: x["합계"]); print("MDD", lim, "이내 최고 합계:", json.dumps(x, ensure_ascii=False))
