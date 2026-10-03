"""I 51회차 — 더 나은 연구 방법(사용자 2026-10-03 "더 나은 연구할 수 있는 방법 제시 후 진행").
A 실제 호가 비용: 상품마다 그날 값의 호가 단위(ETF 2,000원 아래 1원 · 위 5원)로 사고팔기 비용 = 호가 1칸 / 값 + 수수료 0.03%.
  상품 · 해마다 평균 비용 표, 그리고 코스닥 과열 인버스(I22)를 이 비용으로 다시.
B 앞에서 고르고 뒤에서 시험: I22 설정(문턱 8 ~ 13% × 익절 1.5 · 2 · 3 × 손절 1.5 · 2 · 3 × 5 · 10 · 20일)을 2017 ~ 2021만으로 고르고(두 반 중 나쁜 쪽 연 수익이 큰 판) 2022 ~ 2026에 그대로.
C 운 섞어 보기: 최종 판(1일봉 + 빈칸 엔진 + 코스닥 인버스) 달마다 수익(2017-01 ~ 2025-12)을 3달 묶음으로 무작위로 다시 뽑아 1만 번 9년을 굴림 → 연 수익 · 골 분포, 골 < −15% 확률."""
import contextlib
import io
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

D, n = I.DAYS, len(I.DAYS)
print("== I 51회차 A: 실제 호가 비용(사고팔기 한 번 · %) ==", flush=True)
CODES = {"069500": "KODEX 200", "114800": "인버스", "251340": "코스닥 인버스", "252670": "인버스 2X", "133690": "나스닥100", "138230": "달러", "132030": "금", "148070": "국채10년"}
tickcost = {}
for c in CODES:
    p = I.px(c)
    tk = np.where(p < 2000, 1.0, 5.0)
    tickcost[c] = tk / p + 0.0003
yrs = [str(y) for y in range(2017, 2027)]
print("  상품          " + " ".join(f"{y:>6s}" for y in yrs), flush=True)
for c, nm in CODES.items():
    row = []
    for y in yrs:
        idx = [i for i, d in enumerate(D) if d.startswith(y)]
        v = np.nanmean(tickcost[c][idx]) * 100
        row.append(f"{v:6.2f}" if np.isfinite(v) else "     -")
    print(f"  {nm:12s} " + " ".join(row), flush=True)


def sim_tc(entry, code, stop, take, maxd, cool=0):
    """itools.sim과 같되 비용 = 그날 호가 비용(사는 날 · 파는 날 각각 반)."""
    px, tc = I.PX[code], tickcost[code]
    daily, trades, i = np.zeros(n), [], 0
    while i < n - 1:
        if not entry[i] or np.isnan(px[i]):
            i += 1
            continue
        p0 = px[i]
        daily[i] -= tc[i] / 2
        j = i + 1
        while j < n:
            if np.isnan(px[j]):
                j += 1
                continue
            daily[j] += px[j] / px[j - 1] - 1 if not np.isnan(px[j - 1]) else 0
            r = px[j] / p0 - 1
            if r <= stop or r >= take or j - i >= maxd:
                break
            j += 1
        j = min(j, n - 1)
        daily[j] -= tc[j] / 2
        trades.append((i, j, px[j] / p0 - 1 - (tc[i] + tc[j]) / 2))
        i = j + 1 + (cool if px[j] / p0 - 1 <= stop else 0)
    return trades, daily


q = I.px("229200")
r10 = np.nan_to_num(I.ret(q, 10), nan=0)
PER = (("B", "20170101", "20210101"), ("C1", "20210101", "20260101"), ("C2", "20260101", "20991231"))
for tag, fn in (("비용 0.2% 고정", lambda s: I.sim(s, "251340", -0.015, 0.015, 10)), ("실제 호가 비용", lambda s: sim_tc(s, "251340", -0.015, 0.015, 10))):
    tr, d = fn(r10 >= 0.10)
    print(I.line(f"I22 · {tag}", tr, d, PER)[0], flush=True)

print("\n== I 51회차 B: 앞(2017 ~ 2021)에서 고르고 뒤(2022 ~ 2026)에서 시험 ==", flush=True)
TR = (("앞1", "20170101", "20190701"), ("앞2", "20190701", "20220101"))
TE = (("뒤", "20220101", "20991231"),)
cands = []
for th in (0.08, 0.09, 0.10, 0.11, 0.12, 0.13):
    for take in (0.015, 0.02, 0.03):
        for stop in (-0.015, -0.02, -0.03):
            for maxd in (5, 10, 20):
                tr, d = sim_tc(r10 >= th, "251340", stop, take, maxd)
                tj = [I.judge(tr, d, lo, hi) for _, lo, hi in TR]
                ej = I.judge(tr, d, *TE[0][1:])
                cands.append((min(j["cagr"] for j in tj), th, take, stop, maxd, ej))
cands.sort(key=lambda x: x[0], reverse=True)
print("  앞에서 맨 위 5판 → 뒤 성적:", flush=True)
for sc, th, take, stop, maxd, ej in cands[:5]:
    print(f"   문턱 {th*100:.0f}% · 익절 {take*100:.1f} 손절 {stop*100:.1f} {maxd}일 | 앞 나쁜 쪽 연 {sc:+.1f} → 뒤 {ej['n']}건 이김 {ej['win']:.0f} 연 {ej['cagr']:+.1f} 골 {ej['dd']:.1f}", flush=True)
pos = np.mean([c[5]["cagr"] > 0 for c in cands[:20]]) * 100
print(f"  앞 맨 위 20판 중 뒤에서도 + 인 몫 {pos:.0f}% · 전체 486판 중 뒤 + 몫 {np.mean([c[5]['cagr'] > 0 for c in cands]) * 100:.0f}%", flush=True)

print("\n== I 51회차 C: 운 섞어 보기(최종 판 · 달마다 · 3달 묶음 · 1만 번 · 9년) ==", flush=True)
for k, v in dict(I_DIP="1", I_DOLLAR="2", I_GATE="idle20", I_L="20", I_TOP="2", I_CANDS="133690,138230,132030,148070", I_W="1", I_QINV="free").items():
    os.environ[k] = v
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    import i013 as M
for tag, series in (("1일봉만", M.d1), ("최종 판", M.mix)):
    months = sorted({x[:6] for x in D if "201701" <= x[:6] <= "202512"})
    mr = np.array([np.prod(1 + series[[i for i, x in enumerate(D) if x.startswith(m)]]) - 1 for m in months])
    rng = np.random.default_rng(7)
    blocks = [mr[i:i + 3] for i in range(0, len(mr) - 2)]
    cag, dds = [], []
    for _ in range(10000):
        path = np.concatenate([blocks[j] for j in rng.integers(0, len(blocks), 36)])
        eq = np.cumprod(1 + path)
        dds.append((eq / np.maximum.accumulate(eq) - 1).min() * 100)
        cag.append((eq[-1] ** (1 / 9) - 1) * 100)
    cag, dds = np.array(cag), np.array(dds)
    print(f"  {tag}: 연 수익 가운데 {np.median(cag):+.1f}% (아래 5% {np.percentile(cag, 5):+.1f}) · 골 가운데 {np.median(dds):.1f}% (나쁜 5% {np.percentile(dds, 5):.1f}%) · 골 < −15% 확률 {np.mean(dds < -15) * 100:.0f}% · 골 < −20% 확률 {np.mean(dds < -20) * 100:.0f}%", flush=True)
print("끝", flush=True)
