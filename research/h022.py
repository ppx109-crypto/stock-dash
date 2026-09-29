"""1시간봉 22회차 — 기계학습(걸어가며 학습)으로 1시간봉 짧은 오름 맞히기(사용자 결정: 도구로 섞기 · 48회차 교훈: 거르기 전 넓은 후보에서).
후보: A그룹 꼴 + 가르침(전 거래일) 재료가 켜진 날의 모든 봉(종목 모음 100위). 라벨: 다음 봉 시가에 사서 14봉(약 2.3일) 뒤 종가(비용 뺌).
재료(모두 그 봉까지 / 일봉은 전날까지): 1시간봉 RNA(A조합 이격 · 이격밴드 · 이격속도 · 기울기 · 가속도 · 배열 · 지속) · 시간대 · 그 봉 오름 · 거래량 배수 ·
7 · 35봉 최고가까지 거리 · 오늘 시가 대비 · 코스피 1시간봉 배열 · 코스피 오늘 오름 · 일봉 간격 · 시장 폭 · 추세 문 · 3일 연속 · 수급 부호.
걸어가며: 달마다 그 달 첫날보다 7거래일 앞선 봉까지로만 학습(라벨이 미래로 새지 않게) → 그 달 점수. 2024-04부터 점수.
평가: 점수 위 20% 봉 vs 전체의 14 · 35봉 앞날(두 반) · 점수 위 20%만 사는 짧은 판(반 +8% · 반 따라가기 · 4칸) 계좌."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import rna
from sklearn.ensemble import HistGradientBoostingRegressor
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

MK = H.load(["KOSPI"])["KOSPI"]; MK_AT = {t: i for i, t in enumerate(MK["t"])}; MKS = H.states("KOSPI", MK, "A")
def day_open_idx(b, k):
    j = k
    while j > 0 and b["t"][j - 1][:8] == b["t"][k][:8]: j -= 1
    return j
FEAT = ["이격20", "이격60", "이격180", "이격밴드20", "이격밴드60", "이격속도20_1", "이격속도20_3", "이격속도60_5", "기울기20", "기울기60",
        "가속도20", "배열", "정배열지속"]
rows = []
for c, b in data.items():
    a = ATT[c]; st = H.states(c, b, "A"); n = len(b["t"])
    v = b["v"]; cs = np.r_[0.0, np.cumsum(v)]
    for k in range(40, n - 15):
        x = a[k]
        if not (x and ok(x) and IN[c][k]): continue
        t = b["t"][k]
        f = [float(st[name][k]) for name in FEAT]
        avg = (cs[k] - cs[k - 20]) / 20
        j0 = day_open_idx(b, k)
        mi = MK_AT.get(t)
        mj = day_open_idx(MK, mi) if mi is not None else None
        f += [int(t[8:]), (b["c"][k] / b["o"][k] - 1) * 100, v[k] / avg if avg > 0 else np.nan,
              (b["c"][k] / b["h"][k - 7:k].max() - 1) * 100, (b["c"][k] / b["h"][k - 35:k].max() - 1) * 100,
              (b["c"][k] / b["o"][j0] - 1) * 100,
              float(MKS["배열"][mi]) if mi is not None else np.nan,
              (MK["c"][mi] / MK["o"][mj] - 1) * 100 if mi is not None else np.nan,
              x["간격"], x["시장폭"] if x["시장폭"] is not None else np.nan, float(x["추세문"]), float(x["3일연속"]),
              float(np.sign(x["수급5"].get("외국인") or 0)), float(np.sign(x["수급5"].get("투신") or 0)),
              float(np.sign(x["수급5"].get("연기금") or 0)), float(np.sign(x["수급5"].get("사모") or 0))]
        y = (b["c"][k + 14] / b["o"][k + 1] - 1) * 100 - H.COST
        y35 = (b["c"][min(k + 35, n - 1)] / b["o"][k + 1] - 1) * 100 - H.COST
        rows.append((c, k, t, f, y, y35))
X = np.array([r[3] for r in rows], float); X[~np.isfinite(X)] = np.nan
Y = np.array([r[4] for r in rows]); Y35 = np.array([r[5] for r in rows]); T = np.array([r[2] for r in rows])
print(f"후보 봉 {len(rows)} · 재료 {X.shape[1]}", flush=True)
months = sorted({t[:6] for t in T if t >= "20240401"})
all_days = sorted({t[:8] for t in T})
score = np.full(len(rows), np.nan)
for m in months:
    first = next((d for d in all_days if d[:6] == m), None)
    if not first: continue
    cut = all_days[max(0, all_days.index(first) - 7)]
    tr = T < cut
    te = np.array([t[:6] == m for t in T])
    if tr.sum() < 1500 or te.sum() == 0: continue
    mdl = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=60, random_state=0)
    mdl.fit(X[tr], np.clip(Y[tr], -15, 15))
    score[te] = mdl.predict(X[te])
has = ~np.isnan(score)
print(f"점수 받은 봉 {has.sum()} (2024-04~)", flush=True)
def report(tag, mask):
    for name, (lo, hi) in (("앞", ("2024040100", "2025040100")), ("뒤", H.LATE)):
        mm = mask & (T >= lo) & (T < hi)
        if mm.sum() < 30: print(f"    {tag} {name}: 적음"); continue
        print(f"    {tag} {name}: {mm.sum()}봉 · 14봉 {Y[mm].mean():+.2f}%(이긴 {np.mean(Y[mm] > 0) * 100:.0f}%) · 35봉 {Y35[mm].mean():+.2f}%", flush=True)
print("== 1시간봉 22회차 (걸어가며 학습한 점수) ==", flush=True)
report("점수 받은 봉 전체", has)
for q in (0.8, 0.9):
    thr = {}
    for m in months:
        prev = has & np.array([t[:6] < m for t in T])     # 문턱은 지난달까지 점수로만(그 달 뒤쪽 점수를 미리 보지 않게)
        if prev.sum() >= 200: thr[m] = np.quantile(score[prev], q)
    top = has & np.array([score[i] >= thr.get(T[i][:6], np.inf) for i in range(len(T))])
    report(f"점수 위 {int((1 - q) * 100)}%", top)
# 상관(달마다 부호)
for m in months:
    sel = has & np.array([t[:6] == m for t in T])
    if sel.sum() > 50:
        print(f"  {m} 상관 {np.corrcoef(score[sel], Y[sel])[0, 1]:+.2f}", end="")
print(flush=True)
print("끝", flush=True)
