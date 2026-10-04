"""1시간봉 다시 보기 3단계(docs/RL-1HY.md) — 몫 조합을 정직한 계산(실제 비용 · 날마다 평가 · 되돌림 뺀 골)으로, 2단계 무작위 풀 판마다 견줌.
같은 번째 판끼리(1일봉 d1luck · 1시간봉 h1luck · 15분봉 m15luck) 장부를 몫만큼 칸을 줄여 한 계좌에 합침(a_mtm.account).
실제 비용: 1일봉 장부 −0.2%p(점검 A14) · 1시간봉 · 15분봉 −0.15%p(엔진 0.30 → 0.45%). 같은 날 사고 판 매매는 다음 거래일 판 것으로(손익 그대로).
H1_FILE(기본 kis_all 1년) · MIX_LO / MIX_HI. 엔진 · 인버스 몫은 넣지 않음(세 봇끼리만 견줌)."""
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import numpy as np
import a_mtm
import itools as I

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
LO, HI = os.environ.get("MIX_LO", "20250917"), os.environ.get("MIX_HI", "20260901")
H1F = os.environ.get("H1_FILE", "h1luck_kis_all_202509_202609.json")
D = [d for d in I.DAYS if LO <= d < HI]
nxt = {d: D[i + 1] for i, d in enumerate(D[:-1])}
src = {"1일봉": (json.load(open(SP + "d1luck.json")), 0.2), "1시간봉": (json.load(open(SP + H1F)), 0.15),
       "15분봉": (json.load(open(SP + "m15luck.json")), 0.15)}
COMBOS = [(50, 0, 50), (40, 20, 40), (35, 30, 35), (50, 25, 25), (25, 25, 50), (100, 0, 0), (0, 100, 0), (0, 0, 100)]
nd = min(len(v[0]["판"]) for v in src.values())


def led(name, i):
    j, extra = src[name]
    L = (j["온 풀"] if i < 0 else j["판"][i])["장부"]
    out = []
    for c, b, e, p, k in L:
        if not (LO <= b < HI):
            continue
        if e == b:
            e = nxt.get(e, e)
        out.append((c, b, e, p - extra, k))
    return out


def stat(i, combo):
    L = []
    for share, name in zip(combo, ("1일봉", "1시간봉", "15분봉")):
        if share:
            L += [(c, b, e, p, k * share / 100) for c, b, e, p, k in led(name, i)]
    z = np.zeros(len(D))
    rm = a_mtm.account(D, L, z, mode="mark"); rc = a_mtm.account(D, L, z, mode="cost")
    q, qc = np.cumprod(1 + rm), np.cumprod(1 + rc)
    return (q[-1] - 1) * 100, (qc / np.maximum.accumulate(qc) - 1).min() * 100, (q / np.maximum.accumulate(q) - 1).min() * 100


print(f"== 3단계 · {LO} ~ {HI} · 무작위 {nd}판 · 1시간봉 {H1F} ==", flush=True)
R = {cb: np.array([stat(i, cb) for i in range(nd)]) for cb in COMBOS}
F = {cb: stat(-1, cb) for cb in COMBOS}
base = R[(50, 0, 50)]
for cb in COMBOS:
    r = R[cb]
    win = np.mean((r[:, 0] > base[:, 0]) & (r[:, 1] > base[:, 1])) * 100
    print(f"  {'·'.join(map(str, cb)):9s} 온 풀 {F[cb][0]:+6.1f} 골뺌 {F[cb][1]:6.1f} | 무작위 수익 가운데 {np.median(r[:, 0]):+6.1f} 아래10% {np.percentile(r[:, 0], 10):+6.1f}"
          f" · 되돌림 뺀 골 가운데 {np.median(r[:, 1]):6.1f} 나쁜10% {np.percentile(r[:, 1], 10):6.1f} · 되돌림 셈 골 {np.median(r[:, 2]):6.1f}"
          f" | 지금(50·0·50)보다 수익↑·골↓ {win:4.0f}%", flush=True)
