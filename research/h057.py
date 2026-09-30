"""57회차 — 사용자 "+10%로 해주고 +10% 상승 2일 전 혹은 4일 전 매수로 진행할 수 있는 매수 · 매도 · 손절 · 청산 규칙 조합".
① 사건: 그날 신호 → 다음 날 종가에 삼 → 그 뒤 H일(2 · 4) 안 종가가 +10% 이상(라벨만 앞날). 특징별 들어올림(세 시기).
② 규칙 조합: 사는 조건(문턱은 그 달 앞 자료로만 정한 분위) × 익절 +10% × 손절 −3 · −5 · −7% × 기간 청산 2 · 4 · 6 · 10일.
   판정은 종가로만(장중 고가 · 저가 없음 — 보수적). 비용 0.30%. 매매당 손익 · 이긴 몫 · 한 해 신호 수 · 세 시기."""
import sys, json, bisect, pickle
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
exec(open("research/h055.py", encoding="utf-8").read().split('def outcome(code, day):')[0])
b = qbin
COST = 0.30
# 종가 경로를 한 번에 붙여 둠(빠르게)
IDX = {}
for x in data:
    d, c = path(x[0]); IDX[(x[0], x[1])] = bisect.bisect_left(d, x[1])
def fwd_max(code, k, h):
    d, c = path(code)
    if k + 1 + h >= len(c): return None
    return (c[k + 2:k + 2 + h].max() / c[k + 1] - 1) * 100
# ① 들어올림 표(짧은 사건)
FE = ["변동성", "밴드 폭", "모임폭", "추세 기울기", "단기 기울기", "20일 전 대비", "60일 전 대비", "거래량비", "EMA20 이격", "60일 전고점 대비", "밴드 자리", "순위", "정배열폭"]
print("== 57회차 (+10% · 2 · 4일 앞 매수 규칙) ==", flush=True)
for H in (2, 4):
    lab = {}
    for x in data:
        v = fwd_max(x[0], IDX[(x[0], x[1])], H)
        if v is not None: lab[(x[0], x[1])] = v >= 10
    base = {n: np.mean([lab[(x[0], x[1])] for x in data if (x[0], x[1]) in lab and per(x[1]) == n]) for n, _, _ in PER}
    print(f"  [H={H}일 안 +10%] 기본 확률 " + " · ".join(f"{n} {base[n] * 100:.2f}%" for n, _, _ in PER), flush=True)
    for f in FE:
        cnt = {}
        for x in data:
            key = (x[0], x[1])
            if key not in lab or per(x[1]) is None: continue
            q = b(f, x)
            if q is None: continue
            t = cnt.setdefault(q, {n: [0, 0] for n, _, _ in PER})
            t[per(x[1])][0] += 1; t[per(x[1])][1] += lab[key]
        names = ["아래10", "10~30", "30~50", "50~70", "70~90", "위10"]
        line = " | ".join(f"{names[q]} " + "·".join(f"{(cnt[q][n][1] / cnt[q][n][0]) / base[n]:.1f}" if cnt[q][n][0] else "-" for n, _, _ in PER) for q in sorted(cnt))
        print(f"      {f:10s} {line}", flush=True)
# ② 규칙 조합
def trade(code, k, tp, sl, hold):
    d, c = path(code)
    if k + 1 + hold >= len(c): return None
    buy = c[k + 1]
    for j in range(k + 2, k + 2 + hold):
        r = (c[j] / buy - 1) * 100
        if r >= tp: return (tp - COST, True)
        if r <= -sl: return (r - COST, False)
    return ((c[k + 1 + hold] / buy - 1) * 100 - COST, False)
CONDS = {
    "모든 날(기준)": lambda x: True,
    "변동성 위 10%": lambda x: b("변동성", x) == 5,
    "변동성 위 10% · 거래량비 위 10%": lambda x: b("변동성", x) == 5 and b("거래량비", x) == 5,
    "단기 기울기 위 10% · 거래량비 위 10%": lambda x: b("단기 기울기", x) == 5 and b("거래량비", x) == 5,
    "20일 수익 위 10% · 거래량비 위 10% · 작은 종목": lambda x: b("20일 전 대비", x) == 5 and b("거래량비", x) == 5 and (b("순위", x) or 0) >= 4,
    "크게 빠진 뒤(EMA20 이격 · 60일 고점 대비 아래 10%) · 변동성 위 30%": lambda x: b("EMA20 이격", x) == 0 and b("60일 전고점 대비", x) == 0 and (b("변동성", x) or 0) >= 4,
    "밴드 아래 끝(밴드 자리 아래 10%) · 변동성 위 30%": lambda x: b("밴드 자리", x) == 0 and (b("변동성", x) or 0) >= 4,
    "조용한 추세(변동성 아래 40% · 추세 기울기 위 30%)": lambda x: (b("변동성", x) if b("변동성", x) is not None else 9) <= 2 and (b("추세 기울기", x) or 0) >= 4,
    "정배열폭 · 모임폭 위 10%": lambda x: b("정배열폭", x) == 5 and b("모임폭", x) == 5,
}
GRID = [(sl, hold) for sl in (3, 5, 7) for hold in (2, 4, 6, 10)]
YEARS = {"2017~19": 3.0, "2020~22": 3.0, "2023~26": 3.6}
print("  -- 규칙 조합(익절 +10% · 손절 · 기간 청산) · 칸마다 '매매당 손익%(이긴 몫%)' 세 시기 · 한 해 신호 수", flush=True)
for tag, cond in CONDS.items():
    picks = {n: [] for n, _, _ in PER}; last = {}
    for x in data:
        p = per(x[1])
        if p is None or not cond(x): continue
        k = IDX[(x[0], x[1])]
        if x[0] in last and k - last[x[0]] < 5: continue          # 같은 종목 5일 안 다시 안 삼
        last[x[0]] = k
        picks[p].append((x[0], k))
    best = []
    rows = []
    for sl, hold in GRID:
        cells = []
        allpos = True
        for n, _, _ in PER:
            r = [trade(c, k, 10, sl, hold) for c, k in picks[n]]
            r = [t for t in r if t]
            m = np.mean([t[0] for t in r]) if r else float("nan"); w = np.mean([t[1] for t in r]) * 100 if r else float("nan")
            allpos &= (m > 0)
            cells.append(f"{m:+.2f}({w:.0f})")
        rows.append((sl, hold, cells, allpos))
    per_year = " · ".join(f"{len(picks[n]) / YEARS[n]:.0f}" for n, _, _ in PER)
    print(f"  {tag} — 한 해 신호 {per_year}", flush=True)
    for sl, hold, cells, allpos in rows:
        print(f"      손절 −{sl}% · {hold}일 청산: " + " · ".join(cells) + ("   ← 세 시기 모두 플러스" if allpos else ""), flush=True)
print("끝", flush=True)
