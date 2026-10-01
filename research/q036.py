"""15분봉 35회차 — 뒤 반 큰 하락(2026-05-29 → 07-20 · 14회차)을 줄이는 일봉 시장 신호(전 거래일까지 값만).
Q_PART=1: 시장 폭(100위 안 50일선>200일선 몫)이 5거래일 전보다 10%p 넘게 떨어졌으면 새로 안 삼 · 5%p
Q_PART=2: 코스피 종가가 20일선 아래면 10:45 사기 쉼 · 모든 사기 쉼
최종 후보(22회차) 위 · 161종목 · 씨앗 16.
"""
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
CTX = W["CTX"]

BR = {}
for c in CTX:
    for d, x in CTX[c].items():
        if x.get("시장폭") is not None:
            BR[d] = x["시장폭"]
BD = sorted(BR)
BDROP = {BD[k]: BR[BD[k]] - BR[BD[k - 5]] for k in range(5, len(BD))}

kr = json.load(open("market-data/index_KOSPI.json", encoding="utf-8"))["rows"]
kd = [r["date"] for r in kr]
kc = np.array([r["종가"] for r in kr], float)
ma20 = np.r_[np.full(19, np.nan), np.convolve(kc, np.ones(20) / 20, "valid")]
BELOW = {d: bool(c < m) for d, c, m in zip(kd, kc, ma20) if not np.isnan(m)}


def cut_by(test, noon_only=False):
    def f(c, b):
        m = SGF[c].copy()
        for k in np.flatnonzero(m):
            if noon_only and HH[c][k] != "1045":
                continue
            x = mat(c, b, k)
            if x and test(x["날"]):          # x["날"] = 전 거래일
                m[k] = False
        return m
    return f


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 35회차({part}): 일봉 시장 신호로 하락 줄이기 ({len(data)}종목) ==", flush=True)
if part == "1":
    for th in (10, 5):
        go(f"시장 폭 5일 −{th}%p 넘게 떨어지면 안 삼", cut_by(lambda d, th=th: (BDROP.get(d) or 0) <= -th))
else:
    go("코스피 20일선 아래면 10:45 사기 쉼", cut_by(lambda d: BELOW.get(d, False), noon_only=True))
    go("코스피 20일선 아래면 모든 사기 쉼", cut_by(lambda d: BELOW.get(d, False)))
print("끝", flush=True)
