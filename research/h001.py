"""1시간봉 1회차 — 뼈대 0~2단계: 자료 점검 · 기준값(아무 봉이나 샀을 때) · 시간대별 · 정배열 사건 · 미래 참조 가드.
신호 봉이 닫힌 뒤 다음 봉 시가에 사서 k봉 뒤 종가에 판다고 봄(왕복 비용 0.30% 뺌). 종목 모음 = 전 거래일 시총 100위 안.
앞 반 2023-10 ~ 2025-03 · 뒤 반 2025-04 ~ 2026-09."""
import sys, json, os
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import rna

data = H.load()
uni = H.Universe(H.ranks_by_day(), top=100)
codes = [c for c in data if not c.startswith("K")]
n_bars = sum(len(data[c]["t"]) for c in codes)
print(f"종목 {len(codes)} · 봉 {n_bars} · 처음 {min(data[c]['t'][0] for c in codes)} · 끝 {max(data[c]['t'][-1] for c in codes)}", flush=True)
hours = {}
for c in codes:
    for t in data[c]["t"]:
        hours[t[8:]] = hours.get(t[8:], 0) + 1
print("시간대별 봉 수", dict(sorted(hours.items())), flush=True)
per_day = [len({t[:8] for t in data[c]["t"]}) for c in codes]
print(f"종목당 날 수 가운데 {int(np.median(per_day))}", flush=True)

# 가드 ① 앞부분만 넣은 RNA = 전체의 같은 봉
bad = [H.guard_prefix(data[c]) for c in codes[:5]]
print("가드 ① 앞부분 RNA 같음:", "통과" if not any(bad) else bad, flush=True)

# 일봉(전날까지) 정배열 — price-data 일봉 종가로 SMA 3>15>20>90>150>200, **전 거래일 값**을 오늘 봉에 씀
def daily_aligned(code):
    p = f"price-data/{code}.json"
    if not os.path.exists(p): return {}
    rows = json.load(open(p))["closes"]
    d = [x[0] for x in rows]; c = np.array([x[1] for x in rows], float)
    out = {}
    cs = np.r_[0, np.cumsum(c)]
    for i in range(200, len(c)):
        sma = {n: (cs[i + 1] - cs[i + 1 - n]) / n for n in (3, 15, 20, 90, 150, 200)}
        out[d[i]] = sma[3] > sma[15] > sma[20] > sma[90] > sma[150] > sma[200]
    days = sorted(out)
    prev = {}
    for k in range(1, len(days)):
        prev[days[k]] = out[days[k - 1]]      # 오늘 봉에는 어제 값
    return prev
DA = {c: daily_aligned(c) for c in codes}
def day_ok(code, b):
    m = DA.get(code, {})
    return np.array([bool(m.get(t[:8], False)) for t in b["t"]])

K = (1, 3, 7, 14, 35)
print("== 1시간봉 1회차 ==  (평균 %(이긴 몫))", flush=True)
H.show("기준: 아무 봉(겹침 허용)", H.study(data, lambda c, b: np.ones(len(b["c"]), bool), uni, K, edge=False))
for hh in ("09", "10", "11", "12", "13", "14", "15"):
    H.show(f"기준: {hh}시 봉에서 신호", H.study(data, lambda c, b, hh=hh: np.array([t[8:] == hh for t in b["t"]]), uni, K, edge=False))
rng = np.random.default_rng(0)
H.show("가드 ② 무작위 신호(5%)", H.study(data, lambda c, b: rng.random(len(b["c"])) < 0.05, uni, K, edge=False))
H.show("가드 ③ 미래 엿보기(다음 봉이 오르면) ← 이렇게 크면 안 됨", H.study(
    data, lambda c, b: np.r_[b["c"][1:] > b["c"][:-1], False], uni, K, edge=False))
def sA(c, b): return H.states(c, b, "A")
def sB(c, b): return H.states(c, b, "B")
H.show("A(5·20·60·120·180봉) 정배열 됨", H.study(data, lambda c, b: sA(c, b)["정배열"] == 1, uni, K))
H.show("B(5·10·20·60·120·240봉) 정배열 됨", H.study(data, lambda c, b: sB(c, b)["정배열"] == 1, uni, K))
H.show("A 정배열 7봉째(하루 이어짐)", H.study(data, lambda c, b: sA(c, b)["정배열지속"] == 7, uni, K))
H.show("A 정배열 35봉째(닷새 이어짐)", H.study(data, lambda c, b: sA(c, b)["정배열지속"] == 35, uni, K))
H.show("A 정배열 중 20봉선 되올라섬(눌림 뒤)", H.study(
    data, lambda c, b: (sA(c, b)["배열"] >= 3) & (sA(c, b)["이격20"] > 0) & (np.r_[np.nan, sA(c, b)["이격20"][:-1]] <= 0), uni, K))
H.show("일봉 정배열(전날) + A 정배열 됨", H.study(data, lambda c, b: (sA(c, b)["정배열"] == 1) & day_ok(c, b), uni, K))
H.show("일봉 정배열(전날) + 20봉선 되올라섬", H.study(
    data, lambda c, b: day_ok(c, b) & (sA(c, b)["이격20"] > 0) & (np.r_[np.nan, sA(c, b)["이격20"][:-1]] <= 0), uni, K))
H.show("일봉 정배열(전날)인 날 아무 봉", H.study(data, lambda c, b: day_ok(c, b), uni, K, edge=False))
print("끝", flush=True)
