"""MPOS-0010 추정 왕복 비용(반대 검토 결함 2): 새 문 매매마다 주문 크기 = 그 칸 결합 계좌의 산 날 전날 NAV × 0.5 × 칸 ÷ 10(z100 크기와 같은 식)으로
perf2.side_costs(산 날 · 판 날 · 금액)를 셈. 고정 나무에서 tree_run으로 돌림. python3 cost10.py <장부> <meta> <결합 바탕 csv> <출력>"""
import csv
import json
import sys

led, meta, base, out = sys.argv[1:5]
sys.path[:0] = ["research"]
import perf2  # noqa: E402

L, Mt = json.load(open(led)), json.load(open(meta))
new = L[len(L) - len(Mt):] if Mt else []
nav = [(r["날"], float(r["NAV"])) for r in csv.DictReader(open(base, encoding="utf-8"))]
res = []
for r, m in zip(new, Mt):
    if r[2] == "99999999":
        res.append(None)
        continue
    prev = [v for d, v in nav if d < r[1]]
    amt = (prev[-1] if prev else nav[0][1]) * 0.5 * r[4] / 10
    b, s = perf2.side_costs(r[0], r[1], r[2], amt, 1.0)
    res.append({"주문 금액": amt, "추정왕복비용": (b + s) * 100})
json.dump(res, open(out, "w"), ensure_ascii=False)
print("비용", sum(1 for x in res if x), "건")
