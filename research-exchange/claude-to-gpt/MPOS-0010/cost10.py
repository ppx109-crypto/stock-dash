"""MPOS-0010 비용 대리치(근사 계약 · GPT #428 고칠 것 1): 이것은 **잠재 장부 거래의 비용 대리치**이지 z100이 실제 체결한 금액 · 비용이 아닙니다.
- 기준 금액 A = 그 칸 z100 바탕 csv(덧붙임 전)의 산 날 전날 NAV × 0.5 × 칸 ÷ 10. 사고팔 때 같은 A를 씀(실제는 매수 시점 total() · 현금 · 상한 · 부분 정리로 다름).
- 금액 차이로 관문 부호가 뒤집힐 범위를 결과 전에 고정: A × 0.5 · A · A × 2 세 금액으로 셈(충격 ∝ √금액 → 약 0.71배 · 1.41배).
  관문 ⓑ는 **A × 2(가장 비싼 쪽)**에서도 앞 · 뒤 반 > 0 이어야 통과. 기전 비교는 A.
- 구성(보고): 수수료 0.015% · 슬리피지 0.05%(각 편도) · 매도세(판 해) · 충격(√(금액 ÷ 앞 20일 평균 거래대금) × 0.10) · ADV 없을 때 편도 0.2% 대입 여부.
python3 cost10.py <장부> <meta> <z100 바탕 csv> <출력>"""
import csv
import json
import sys

led, meta, base, out = sys.argv[1:5]
sys.path[:0] = ["research"]
import numpy as np  # noqa: E402
import perf2  # noqa: E402

L, Mt = json.load(open(led)), json.load(open(meta))
new = L[len(L) - len(Mt):] if Mt else []
nav = [(r["날"], float(r["NAV"])) for r in csv.DictReader(open(base, encoding="utf-8"))]


def adv_at(code, day):
    a = perf2.adv_series(code)
    v = a.get(day) if len(a) else None
    if v is None or not np.isfinite(v) or v <= 0:
        v = a[a.index <= day].iloc[-1] if len(a) and (a.index <= day).any() else float("nan")
    return float(v) if np.isfinite(v) and v > 0 else None


res = []
for r, m in zip(new, Mt):
    if r[2] == "99999999":
        res.append(None)
        continue
    prev = [v for d, v in nav if d < r[1]]
    A = (prev[-1] if prev else nav[0][1]) * 0.5 * r[4] / 10
    rt = {}
    for nm, k in (("반금액", 0.5), ("기준", 1.0), ("2배금액", 2.0)):
        b, s = perf2.side_costs(r[0], r[1], r[2], A * k, 1.0)
        rt[nm] = (b + s) * 100
    ib, isl = perf2.impact(r[0], r[1], A), perf2.impact(r[0], r[2], A)
    res.append({"기준 금액": A, "추정왕복비용": rt["기준"], "추정왕복비용_반금액": rt["반금액"], "추정왕복비용_2배금액": rt["2배금액"],
                "수수료슬리피지": 0.00065 * 2 * 100, "매도세": perf2.tax(r[2]) * 100, "충격": (ib + isl) * 100,
                "ADV 산 날": adv_at(r[0], r[1]), "ADV 없음 대입": adv_at(r[0], r[1]) is None or adv_at(r[0], r[2]) is None})
json.dump(res, open(out, "w"), ensure_ascii=False)
print("비용 대리치", sum(1 for x in res if x), "건")
