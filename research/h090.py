"""1시간봉 90회차 — '덜 몰린 것 먼저'를 **같은 봉 시각에 나온 신호끼리만** 순위(0 ~ 1)로 견줌: 그 봉이 닫힌 뒤 이미 모두 아는 후보들이라 미래 참조 없음
(86 · 88회차의 '같은 날' 순위는 아침 신호가 그날 11시 신호까지 함께 봤음). 세 무리 · 무리 안 무작위 · 씨앗 16 + 잡음 세계 6. 한 봉에 신호가 하나면 가운데 무리."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
SRC89 = open("research/h089.py", encoding="utf-8").read()
pre = SRC89.split("TF = monthly_tier(")[0].replace("== 1시간봉 89회차 (그달 앞 신호로 정한 무리 순서) ==", "== 1시간봉 90회차 (같은 봉 시각 후보끼리 순위) ==")
exec(pre)
bybar = {}
for (c, k) in F: bybar.setdefault(data[c]["t"][k], []).append((c, k))
print(f"  봉 시각 {len(bybar)}개 · 신호 둘 이상인 시각 {sum(len(v) > 1 for v in bybar.values())}개 · 그 안의 신호 {sum(len(v) for v in bybar.values() if len(v) > 1)}개", flush=True)
def bar_tier(fn, good_high):
    T = {}
    for t, L in bybar.items():
        if len(L) == 1: T[L[0]] = 1; continue
        v = np.array([fn(c, k) for c, k in L], float)
        v = np.where(np.isnan(v), np.nanmedian(v) if np.any(~np.isnan(v)) else 0, v)
        r = np.argsort(np.argsort(v)) / (len(v) - 1)
        if not good_high: r = 1 - r
        for z, x in zip(L, r): T[z] = min(int(x * 3), 2)
    return T
TF = bar_tier(flow, False); TP = bar_tier(SC["프로그램 5일 세기"], False); TR = bar_tier(SC["20일 수익"], True)
TB = {z: TF[z] + TR[z] for z in F}
exec(SRC89.split("TB = {z: TF[z] + TR[z] for z in F}")[1].split('CASES = {')[0])
CASES = {"지금": rank, "수급 약한 무리 먼저(같은 봉)": tier_rank(TF), "프로그램 약한 무리 먼저(같은 봉)": tier_rank(TP),
         "20일 수익 큰 무리 먼저(같은 봉)": tier_rank(TR), "둘 합(수급 약 + 20일 수익 큼)": tier_rank(TB),
         "거꾸로: 수급 센 무리 먼저": tier_rank({z: 2 - v for z, v in TF.items()})}
exec("CASES_KEEP = CASES\n" + SRC89.split('"둘 합(수급 약 + 20일 수익 큼)": tier_rank(TB)}')[1])
