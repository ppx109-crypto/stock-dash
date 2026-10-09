"""INV-0021 — 통합 계좌 F(LOSS-ATTR-0013 evidence/F_attr.csv)의 코스닥 인버스 손익을 '든 구간'별로 묶음. 인자: F_attr.csv 경로."""
import csv
import sys
A = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
eps, cur = [], None
for r in A:
    x = float(r["inverse"]) / float(r["NAV전"])
    if x != 0:
        if cur is None:
            cur = [r["날"], r["날"], 0.0, 0]
        cur[1] = r["날"]; cur[2] += x; cur[3] += 1
    elif cur:
        eps.append(cur); cur = None
if cur:
    eps.append(cur)
for nm, g in (("앞 반(2017~2020)", [e for e in eps if e[0] < "20210101"]), ("뒤 반(2021~2026-09)", [e for e in eps if e[0] >= "20210101"])):
    print(nm, "구간", len(g), "· 이긴 구간", sum(1 for e in g if e[2] > 0), "· 계좌 기여 합 %+.1f%%p" % (sum(e[2] for e in g) * 100),
          "· 가장 나쁜 구간 %+.2f%%p" % (min(e[2] for e in g) * 100), "· 평균 든 날 %.1f" % (sum(e[3] for e in g) / len(g)))
print("가장 나쁜 구간 5(시작일 · 든 날 · 계좌 기여 %p):", [(e[0], e[3], round(e[2] * 100, 2)) for e in sorted(eps, key=lambda e: e[2])[:5]])
