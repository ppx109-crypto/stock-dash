"""I 3회차 — 급락 되돌림 다듬기(I2b) · 코스닥(I2c). 사용자 결정: 1배만 · 목표 골 −15% 안(세 기간 모두) · 코스닥도 봄.
P=1 KODEX 200(069500): 5일 급락 문턱 −4 ~ −8% × 익절 3 ~ 6 × 손절 3 ~ 5 × 기간 10 · 20 × 손절 뒤 쉬기 0 · 10 · 20일
     + 나눠 사기(문턱에서 반 · 3%p 더 빠지면 나머지 반) + 큰 흐름 거르기(200일선 위/아래).
P=2 코스닥150(229200, 2015-10 ~): 같은 판을 코스닥 자체 급락으로 · 코스피 · 코스닥 중 5일 더 빠진 쪽을 삼(둘 다 문턱 넘을 때).
잣대: 세 기간 모두 연 + 이고 골 −15% 안 → '합격'. 합격 판 수 · 고원 · 가장 나은 판."""
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

part = os.environ.get("P", "1")
cost = float(os.environ.get("I_COST", "0.002"))


def grid(sigs, code, label):
    rows = []
    for tag, sig, weight2 in sigs:
        for take in (0.03, 0.04, 0.05, 0.06):
            for stop in (-0.03, -0.04, -0.05):
                for maxd in (10, 20):
                    for cool in (0, 10, 20):
                        if weight2 is None:
                            tr, d = I.sim(sig, code, stop, take, maxd, cost=cost, cool=cool)
                        else:            # 나눠 사기: 문턱에서 반 · 더 빠진 신호에서 반
                            t1, d1 = I.sim(sig, code, stop, take, maxd, cost=cost, cool=cool, weight=0.5)
                            t2, d2 = I.sim(weight2, code, stop, take, maxd, cost=cost, cool=cool, weight=0.5)
                            tr, d = t1 + t2, d1 + d2
                        js = [I.judge(tr, d, lo, hi) for _, lo, hi in I.PERIODS]
                        js = [j for j in js if j and j["n"] > 0]
                        if len(js) < (3 if code == "069500" else 2):
                            continue
                        ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                        worst = min(j["cagr"] for j in js)
                        dd = min(j["dd"] for j in js)
                        text, _ = I.line(f"{tag} | 익절 {take*100:.0f} 손절 {stop*100:.0f} {maxd}일 쉬기 {cool}", tr, d)
                        rows.append((ok, worst, dd, text))
    good = [r for r in rows if r[0]]
    print(f"\n[{label}] 판 {len(rows)} · 합격(세 기간 모두 + · 골 −15% 안) {len(good)}", flush=True)
    for r in sorted(good, key=lambda r: -r[1])[:8]:
        print(f"  ✔ 가장 나쁜 연 {r[1]:+5.1f} 가장 깊은 골 {r[2]:6.1f} " + r[3].strip(), flush=True)
    if not good:
        for r in sorted(rows, key=lambda r: (-(r[2] > -15), -r[1]))[:5]:
            print(f"  · 가장 나쁜 연 {r[1]:+5.1f} 가장 깊은 골 {r[2]:6.1f} " + r[3].strip(), flush=True)
    return good


def sigs_for(px):
    r5 = I.ret(px, 5)
    m200 = I.ma(px, 200)
    out = []
    for th in (-0.04, -0.05, -0.06, -0.07, -0.08):
        s = np.nan_to_num(r5, nan=0) <= th
        deeper = np.nan_to_num(r5, nan=0) <= th - 0.03
        out.append((f"5일 {th*100:.0f}%", s, None))
        out.append((f"5일 {th*100:.0f}% 나눠 사기", s, deeper))
        up = np.nan_to_num(px > m200, nan=0).astype(bool)
        out.append((f"5일 {th*100:.0f}% · 200일선 위", s & up, None))
        out.append((f"5일 {th*100:.0f}% · 200일선 아래", s & ~up, None))
    return out


if part == "1":
    print(f"== I 3회차(P=1): KODEX 200 급락 되돌림 다듬기 · 비용 {cost*100:.1f}% ==", flush=True)
    grid(sigs_for(I.K200), "069500", "KODEX 200")
else:
    kq = I.PX["229200"]
    print(f"== I 3회차(P=2): 코스닥150 급락 되돌림 · 비용 {cost*100:.1f}% ==", flush=True)
    grid(sigs_for(kq), "229200", "코스닥150(자기 급락)")
    # 코스피 · 코스닥 중 5일 더 빠진 쪽(둘 다 문턱 넘을 때 · 하나만 넘으면 그쪽)
    r5k, r5q = I.ret(I.K200, 5), I.ret(kq, 5)
    for th in (-0.05, -0.06):
        sk = np.nan_to_num(r5k, nan=0) <= th
        sq = np.nan_to_num(r5q, nan=0) <= th
        pick_q = sq & (np.nan_to_num(r5q, nan=0) <= np.nan_to_num(r5k, nan=0))
        pick_k = sk & ~pick_q
        rows = []
        for take in (0.03, 0.04, 0.05):
            for stop in (-0.04, -0.05):
                t1, d1 = I.sim(pick_k, "069500", stop, take, 20, cost=cost)
                t2, d2 = I.sim(pick_q, "229200", stop, take, 20, cost=cost)
                text, worst = I.line(f"더 빠진 쪽 5일 {th*100:.0f}% | 익절 {take*100:.0f} 손절 {stop*100:.0f} 20일", t1 + t2, d1 + d2)
                print("  " + text.strip(), flush=True)
print("끝", flush=True)
