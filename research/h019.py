"""1시간봉 19회차 — 하루 먼저 사고 · 하루 먼저 팔기(사용자 목표 ① 오르기 전에 미리 산다 · 빠른 회전).
지금 규칙은 '어제 종가로 정배열 문이 열리면 오늘' 삼. 1시간봉이 있으면 **오늘 장중 가격을 '오늘 종가라면'으로 넣어**
오늘 문이 열릴 종목을 오늘 사고, 정배열이 오늘 깨질 종목을 오늘 팔 수 있음.
미래 참조 없음: 일봉 단순평균은 어제까지 종가 + 지금 봉 종가(가짜 오늘 종가)로만 셈 · 수급 · 시장 폭은 어제 것.
- 먼저 사기: 어제는 문이 닫혀 있었는데 지금 봉 종가로 세면 정배열 문(3>15>20>90>150>200 · 간격 19~53%)이 열리고, 어제 시장 폭 ≥ 50 · 어제 가르침 수급이면 다음 봉 시가에 삼(봉 13 · 14시만 = 장 끝 무렵 · 또는 아무 봉)
- 먼저 팔기: 정배열 문으로 산 것이 지금 봉 종가로 세면 정배열이 깨지면 다음 봉 시가에 팜(13 · 14시 봉만)"""
import sys, json
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

DL = {}
for c in data:
    rows = json.load(open(f"price-data/{c}.json"))["closes"]
    rows = [x for x in rows if x[0] >= "20220101"]
    d = [x[0] for x in rows]; cl = np.array([x[1] for x in rows], float)
    DL[c] = (d, np.r_[0.0, np.cumsum(cl)], {day: i for i, day in enumerate(d)})
def provisional(c, b, k):
    """지금 봉 종가를 오늘 종가로 보고 센 (정배열, 간격). 어제까지 종가 + 지금 값만 씀."""
    d, cs, at = DL[c]
    i = at.get(b["t"][k][:8])
    if i is None or i < 200: return None
    now = b["c"][k]
    def sma(n): return (cs[i] - cs[i - n + 1] + now) / n          # 어제까지 n−1일 + 지금 값
    m = {n: sma(n) for n in (3, 15, 20, 90, 150, 200)}
    return (m[3] > m[15] > m[20] > m[90] > m[150] > m[200], (m[3] / m[200] - 1) * 100)
_PV = {}
def prov_arr(c, b):
    if c not in _PV:
        al = np.zeros(len(b["t"]), bool); gap = np.full(len(b["t"]), np.nan)
        for k in range(len(b["t"])):
            r = provisional(c, b, k)
            if r: al[k], gap[k] = r
        _PV[c] = (al, gap)
    return _PV[c]

def early_entry(hours=("13", "14")):
    def e(c, b):
        base = e_align_or_noon(c, b)
        al, gap = prov_arr(c, b)
        a = ATT[c]; days = [t[:8] for t in b["t"]]
        m = base.copy(); seen = {days[k] for k in np.flatnonzero(base)}
        for k in range(len(m)):
            x = a[k]
            if not x or ok(x) or not IN[c][k] or (hours and b["t"][k][8:] not in hours): continue
            if al[k] and 19 <= gap[k] < 53 and (x["시장폭"] or 0) >= 50 and x["가르침"] and days[k] not in seen:
                m[k] = True; seen.add(days[k])
        return m
    return e
def early_exit(hours=("13", "14")):
    def go(c, b, p, k):
        r = exit_daily(c, b, p, k)
        if r: return r
        kind = door(ATT[c][p["i"]]) or "정배열"
        if kind == "정배열" and (not hours or b["t"][k][8:] in hours):
            al, _ = prov_arr(c, b)
            if not al[k] and k - p["i"] >= 1: return "all"
        return 0
    return go

print("== 1시간봉 19회차 (하루 먼저 사고 · 팔기) ==", flush=True)
for tag, e, x in (("지금", e_align_or_noon, exit_daily),
                  ("먼저 사기(13 · 14시 봉)", early_entry(), exit_daily),
                  ("먼저 사기(아무 봉)", early_entry(None), exit_daily),
                  ("먼저 팔기(13 · 14시 봉)", e_align_or_noon, early_exit()),
                  ("먼저 사기 + 먼저 팔기(13 · 14시)", early_entry(), early_exit())):
    res = H.simulate(data, e, x, size, rank=rank)
    print(f"  {tag:28s} " + H.line(res), flush=True)
    print(f"      반기(씨앗 0): 앞 {res['앞']['반기'] if res['앞'] else '-'} · 뒤 {res['뒤']['반기'] if res['뒤'] else '-'}", flush=True)
print("끝", flush=True)
