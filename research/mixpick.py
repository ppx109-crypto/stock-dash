"""최종 판단(docs/RL-1HY.md 17회차~) — 1일봉 · 1시간봉 · 15분봉 몫(10% 단위 · 합 100)을 무작위 풀 판마다 정직한 계산으로 재고 잣대로 고름.
PICK_LO / PICK_HI(YYYYMMDD) · PICK_D1 · PICK_H1 · PICK_M15(scratchpad 파일) · PICK_N(판 수 · 기본 200) · PICK_ONLY(쉼표 '50_0_50,...'면 그 몫만).
실제 비용: 1일봉 −0.2%p · 1시간봉 · 15분봉 −0.15%p. 같은 날 사고 판 매매는 다음 거래일 판 것으로. 엔진 · 인버스는 뺌(세 봇끼리).
줄마다: 해마다 수익 가운데 · 아래 10% · 되돌림 뺀 골 가운데 · 비(수익 ÷ |골|) 가운데 · 2024 수익 가운데(창에 있으면)."""
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import numpy as np
import a_mtm
import itools as I

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
LO, HI = os.environ["PICK_LO"], os.environ["PICK_HI"]
D = [d for d in I.DAYS if LO <= d < HI]
nxt = {d: D[i + 1] for i, d in enumerate(D[:-1])}
SRC = [(json.load(open(SP + os.environ[k])), extra) for k, extra in (("PICK_D1", 0.2), ("PICK_H1", 0.15), ("PICK_M15", 0.15))]
N = min([int(os.environ.get("PICK_N", "200"))] + [len(j["판"]) for j, _ in SRC])
if os.environ.get("PICK_ONLY"):
    COMBOS = [tuple(int(x) for x in c.split("_")) for c in os.environ["PICK_ONLY"].split(",")]
else:
    COMBOS = [(a, b, 100 - a - b) for a in range(0, 101, 10) for b in range(0, 101 - a, 10)]
m24 = np.array([d[:4] == "2024" for d in D])


def led(s, i):
    j, extra = SRC[s]
    out = []
    for c, b, e, p, k in j["판"][i]["장부"]:
        if LO <= b < HI:
            out.append((c, b, nxt.get(e, e) if e == b else e, p - extra, k))
    return out


LED = [[led(s, i) for i in range(N)] for s in range(3)]
z = np.zeros(len(D))
yrs = len(D) / 250
rows = []
for cb in COMBOS:
    st = []
    for i in range(N):
        L = [(c, b, e, p, k * sh / 100) for s, sh in enumerate(cb) if sh for c, b, e, p, k in LED[s][i]]
        rm = a_mtm.account(D, L, z, mode="mark"); rc = a_mtm.account(D, L, z, mode="cost")
        q, qc = np.cumprod(1 + rm), np.cumprod(1 + rc)
        ann = (q[-1] ** (1 / yrs) - 1) * 100
        dd = (qc / np.maximum.accumulate(qc) - 1).min() * 100
        y24 = (np.prod(1 + rm[m24]) - 1) * 100 if m24.any() else np.nan
        st.append((ann, dd, ann / max(abs(dd), 1e-9), y24))
    a = np.array(st)
    rows.append((cb, np.median(a[:, 0]), np.percentile(a[:, 0], 10), np.median(a[:, 1]), np.median(a[:, 2]), np.median(a[:, 3])))
    print(f"  {'·'.join(map(str, cb)):9s} 해마다 {rows[-1][1]:+6.1f} 아래10% {rows[-1][2]:+6.1f} · 되돌림 뺀 골 {rows[-1][3]:6.1f} · 비 {rows[-1][4]:5.2f} · 2024 {rows[-1][5]:+6.1f}", flush=True)
json.dump([[list(r[0])] + [float(x) for x in r[1:]] for r in rows], open(SP + f"mixpick_{LO}_{HI}.json", "w"))
if not os.environ.get("PICK_ONLY"):
    ok = [r for r in rows if not (r[5] == r[5] and r[5] < 0)]
    ok.sort(key=lambda r: -r[4])
    top = {r[0] for r in ok[:max(1, len(ok) // 5)]}
    for r in ok:
        a, b, c = r[0]
        nb = [(a + da, b + db, c - da - db) for da, db in ((10, 0), (-10, 0), (0, 10), (0, -10), (10, -10), (-10, 10))]
        nb = [x for x in nb if min(x) >= 0 and x in {q[0] for q in rows}]
        if all(x in top for x in nb):
            print(f"== 고른 몫(비 가장 큰 · 이웃도 맨 위 20%): {'·'.join(map(str, r[0]))} · 해마다 {r[1]:+.1f} · 골 {r[3]:.1f} · 비 {r[4]:.2f} · 2024 {r[5]:+.1f}", flush=True)
            break
    else:
        print("== 고원을 넘는 몫 없음", flush=True)
