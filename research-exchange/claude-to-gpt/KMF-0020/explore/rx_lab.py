"""KMF-0020 탐색 2 — 메꿈 봇 RX: 횡보 봇(R)이 틀렸을 때 뒤집어 따라가기.
R이 든 뒤 봉 종가가 R 판단가에서 s×ATR 넘게 불리해지면 → 반대로 뒤집음(추세 따라가기) · 그날 R은 더 안 함.
뒤집은 자리 출구: 5분봉 n개 채널(롱이면 앞 n봉 저점 아래 종가) · N봉 지나도 이익 없으면 정리.
KMF-0017 자리 순서(T → R자리(RX) → W) · 이익 잠금 · 하루 −25p 그대로. 판단 = 봉 종가 · 체결 = 다음 봉 시가 · 편도 0.04p.
ATR = 5분봉 14개 평균 실제 범위(그 봉까지). python3 rx_lab.py"""
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "KMF-0019/explore"))
import mdd_lab as D  # noqa: E402
K, M13, M14, M15, M16, M17, L = D.K, D.M13, D.M14, D.M15, D.M16, D.M17, D.L


def atr14(b):
    out, tr, pc = [], [], None
    for r in b:
        h, l, c = r[3], r[4], r[5]
        t = h - l if pc is None else max(h - l, abs(h - pc), abs(l - pc))
        tr.append(t); tr = tr[-14:]; out.append(sum(tr) / len(tr)); pc = c
    return out


def rx(b, R, A, s, n, N):
    out = [0] * len(b); day = None
    for k, r in enumerate(b):
        if r[0] != day:
            day, mode, ent, rdir, age = r[0], "follow", None, 0, 0
        c = r[5]
        if mode == "follow":
            if R[k] and ent is None:
                ent, d0 = c, R[k]
            if R[k] == 0:
                ent = None
            if ent is not None and R[k]:
                if (c - ent) * d0 <= -s * A[k]:
                    mode, rdir, age = "rev", -d0, 0
                    out[k] = rdir; continue
                out[k] = R[k]
            else:
                out[k] = 0
        elif mode == "rev":
            age += 1
            lo = min(x[4] for x in b[max(0, k - n):k]) if k else c
            hi = max(x[3] for x in b[max(0, k - n):k]) if k else c
            prof = (c - b[k - age][5]) * rdir if k - age >= 0 else 0
            if (rdir > 0 and c < lo) or (rdir < 0 and c > hi) or (N and age >= N and prof <= 0):
                mode = "done"; out[k] = 0
            else:
                out[k] = rdir
        else:
            out[k] = 0
    return out


if __name__ == "__main__":
    b = M17.prep(K._rows_before(M17.END))
    T = M16.intent(b, M13.signals(b, M13.grid()[0])); R = M16.intent(b, M14.signals(b, M14.grid()[0])); W = M16.intent(b, M15.signals(b, M15.grid()[0]))
    A = atr14(b); K.DAY_STOP = -25.0
    base, _ = K.simulate(b, D.signals(b, T, R, W, (40, 15)))
    print("기준 KMF-0017", json.dumps(D.summ(base), ensure_ascii=False))
    res = []
    for s, n, N in itertools.product((1.0, 1.5, 2.0, 2.5), (2, 3, 4, 6), (0, 4, 8)):
        RX = rx(b, R, A, s, n, N)
        for order in ("TRW", "RTW"):
            if order == "TRW":
                want = D.signals(b, T, RX, W, (40, 15))
            else:
                want = D.signals(b, RX, T, W, (40, 15))
            days, _ = K.simulate(b, want)
            res.append({"판": f"RX_s{s}_n{n}_N{N}_{order}", **D.summ(days)})
    (HERE / "rx_lab_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res))
    res.sort(key=lambda x: -x["MDD"])
    for x in res[:10]:
        print(json.dumps(x, ensure_ascii=False))
    print("합계 상위")
    for x in sorted(res, key=lambda x: -x["합계"])[:6]:
        print(json.dumps(x, ensure_ascii=False))
