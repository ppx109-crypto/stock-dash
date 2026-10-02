"""I 28회차 — 코스닥 급등(I22) + 프로그램 비차익 매수 급증(program_Q) 뒤 코스닥150 인버스. 기관 차익 · 비차익 바구니 매수로 끌어올린 급등은 되돌아오나.
프로그램 비차익 5 · 10일 순매수가 지난 1년 위 10 · 20%(2017 ~ · 빈 값은 신호 없음). I22와 겹침 · 단독 · 신용융자 +5%와 셋 다 겹침. 나오는 법 54판."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

n = len(I.DAYS)
q = I.px("229200")
I.px("251340")
q10 = np.nan_to_num(I.ret(q, 10), nan=0) >= 0.10
prog = I.series("market-data/program_Q.json", "비차익순매수")
cr = I.series("market-data/funds.json", "신용융자잔고")
c20 = np.full(n, np.nan)
c20[20:] = cr[20:] / cr[:-20] - 1
c5 = np.nan_to_num(c20, nan=0) >= 0.05


def rsum(a, w):
    out = np.full(n, np.nan)
    for i in range(w - 1, n):
        x = a[i - w + 1:i + 1]
        if np.isfinite(x).all():
            out[i] = x.sum()
    return out


def high_rank(a, pct, look=250):
    out = np.zeros(n, bool)
    for i in range(look, n):
        h = a[i - look:i]
        h = h[np.isfinite(h)]
        if len(h) > 100 and np.isfinite(a[i]):
            out[i] = a[i] >= np.percentile(h, 100 - pct)
    return out


SIG = {"I22 단독": q10, "I22 · 신용 +5%": q10 & c5}
for w in (5, 10):
    for pct in (10, 20):
        h = high_rank(rsum(prog, w), pct)
        SIG[f"프로그램 비차익 {w}일 위 {pct}% 단독"] = h
        SIG[f"I22 · 프로그램 {w}일 위 {pct}%"] = q10 & h
        SIG[f"I22 · 신용 +5% · 프로그램 {w}일 위 {pct}%"] = q10 & c5 & h
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
print("== I 28회차: 코스닥 급등 + 프로그램 매수 급증 뒤 코스닥150 인버스 ==", flush=True)
for name, sig in SIG.items():
    rows = []
    for take in (0.015, 0.02, 0.03):
        for stop in (-0.015, -0.02, -0.03):
            for maxd in (5, 10, 20):
                for cool in (0, 10):
                    tr, d = I.sim(sig, "251340", stop, take, maxd, cool=cool)
                    js = [I.judge(tr, d, lo, hi) for _, lo, hi in PER]
                    ok = all(j["cagr"] > 0 and j["dd"] > -15 for j in js)
                    rows.append((ok, min(j["cagr"] for j in js), f"익절 {take*100:.1f} 손절 {stop*100:.1f} {maxd}일 쉬기 {cool}",
                                 " | ".join(f"{nm} {j['n']}건 연 {j['cagr']:+.1f} 골 {j['dd']:.1f}" for (nm, _, _), j in zip(PER, js))))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    print(f"[{name}] 신호 날 {int(sig.sum())} · 합격 {sum(x[0] for x in rows)}/54 · 맨 위 {rows[0][2]} (가장 나쁜 {rows[0][1]:+.1f}) {rows[0][3]}", flush=True)
print("끝", flush=True)
