"""56회차 — 사용자 "+50%까지는 아니고 +20% 정도도 만족". 목표를 +20%로: 산 뒤 +20%에 먼저 닿나, 손절선(−7 · −10%)에 먼저 닿나.
신호는 55회차와 같음(문턱은 그 달 앞 자료로만 정한 분위 · 다음 날 종가에 삼 · 같은 종목 20일 안 다시 안 셈).
매매 결과(종가로만 판정 — 장중 값 없음, 보수적): +20% 닿으면 +20%에 팜 · 손절선 닿으면 그 종가에 팜(더 빠졌으면 그 값) · 60일 안 둘 다 없으면 60일째 종가.
비용 0.30% 뺌. 보는 것: 60일 안 +20% 간 몫 · +20% 먼저 몫(이긴 몫) · 매매당 평균 손익 · 보유일 가운데 — 세 시기."""
import sys, json, bisect, pickle
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
exec(open("research/h055.py", encoding="utf-8").read().split('def outcome(code, day):')[0])
COST = 0.30
def trade(code, day, tp=20.0, sl=10.0, hold=60):
    d, c = path(code); k = bisect.bisect_left(d, day)
    if k + hold + 1 >= len(c): return None
    buy = c[k + 1]
    for j in range(k + 2, k + 2 + hold):
        r = (c[j] / buy - 1) * 100
        if r >= tp: return (tp - COST, j - k - 1, "익절", True)
        if r <= -sl: return (r - COST, j - k - 1, "손절", False)
    r = (c[k + 1 + hold] / buy - 1) * 100
    return (r - COST, hold, "기간", False)
def reach(code, day, goal=20.0, hold=60):
    d, c = path(code); k = bisect.bisect_left(d, day)
    if k + hold + 1 >= len(c): return None
    return (c[k + 2:k + 2 + hold].max() / c[k + 1] - 1) * 100 >= goal
def evaluate(tag, cond, gap=20):
    last = {}; res = {n: [] for n, _, _ in PER}
    for x in data:
        p = per(x[1])
        if p is None or not cond(x): continue
        code = x[0]; d, _ = path(code); k = bisect.bisect_left(d, x[1])
        if code in last and k - last[code] < gap: continue
        last[code] = k
        a = trade(code, x[1], 20, 10); b = trade(code, x[1], 20, 7); g = reach(code, x[1])
        if a and b and g is not None: res[p].append((a, b, g))
    lines = []
    for n, _, _ in PER:
        r = res[n]
        if not r: lines.append(f"{n} 0건"); continue
        g = np.mean([x[2] for x in r]) * 100
        w10 = np.mean([x[0][3] for x in r]) * 100; m10 = np.mean([x[0][0] for x in r]); h10 = np.median([x[0][1] for x in r])
        w7 = np.mean([x[1][3] for x in r]) * 100; m7 = np.mean([x[1][0] for x in r])
        lines.append(f"{n} {len(r):>5}건 · 60일 안 +20% {g:4.1f}% · [−10% 손절] 이긴 몫 {w10:4.1f}% 매매당 {m10:+5.2f}% 보유 {h10:.0f}일 · [−7% 손절] 이긴 몫 {w7:4.1f}% 매매당 {m7:+5.2f}%")
    print(f"  {tag}\n      " + "\n      ".join(lines), flush=True)
b = qbin
print("== 56회차 (+20% 목표 · 손절과 함께) ==", flush=True)
evaluate("모든 날(기준)", lambda x: True, gap=60)
evaluate("조용한 추세(지금 A그룹 꼴 비슷: 변동성 아래 40% · 추세 기울기 위 30%)", lambda x: (b("변동성", x) if b("변동성", x) is not None else 9) <= 2 and (b("추세 기울기", x) or 0) >= 4)
evaluate("변동성 위 10%", lambda x: b("변동성", x) == 5)
evaluate("모멘텀형: 추세 기울기 위 10% · 변동성 위 30%", lambda x: b("추세 기울기", x) == 5 and (b("변동성", x) or 0) >= 4)
evaluate("모멘텀형 + 작은 종목(순위 뒤 30%)", lambda x: b("추세 기울기", x) == 5 and (b("변동성", x) or 0) >= 4 and (b("순위", x) or 0) >= 4)
evaluate("모멘텀형 + 거래량비 위 30%", lambda x: b("추세 기울기", x) == 5 and (b("변동성", x) or 0) >= 4 and (b("거래량비", x) or 0) >= 4)
evaluate("정배열폭 · 모임폭 위 10%", lambda x: b("정배열폭", x) == 5 and b("모임폭", x) == 5)
evaluate("크게 빠진 뒤(EMA20 이격 · 60일 전고점 대비 아래 10%)", lambda x: b("EMA20 이격", x) == 0 and b("60일 전고점 대비", x) == 0)
evaluate("크게 빠진 뒤 + 변동성 위 30%", lambda x: b("EMA20 이격", x) == 0 and b("60일 전고점 대비", x) == 0 and (b("변동성", x) or 0) >= 4)
evaluate("흑자 전환 · 변동성 위 30%", lambda x: x[3].get("흑자 전환") == 1 and (b("변동성", x) or 0) >= 4)
evaluate("흑자 전환 · 추세 기울기 위 30%", lambda x: x[3].get("흑자 전환") == 1 and (b("추세 기울기", x) or 0) >= 4)
evaluate("20일 수익 위 10% · 거래량비 위 10% · 작은 종목", lambda x: b("20일 전 대비", x) == 5 and b("거래량비", x) == 5 and (b("순위", x) or 0) >= 4)
print("끝", flush=True)
