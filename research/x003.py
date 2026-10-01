"""연구용 순위 · 추세 문 표(.cache/hourly_tables.pkl) 뒤쪽 빈 날 채우기 — 15분봉 최종 시험(9월) 준비(2026-10-02).
일봉 표(study/features.json)가 2026-09-16까지라 그 뒤 날은 순위가 없어 시장 폭이 0으로 잡혔음.
매일 1일봉 운영 계산(final_group.compute)과 같은 lab.build(horizons=(0,))로 모든 종목 줄을 만들어 빈 날만 순위(caps.tag) · 추세 문을 붙여 넣음.
조용함 문턱은 표의 마지막 달 값(calm_by_month의 2026-09)을 씀 — 그 달 첫날 앞 줄로만 정한 값이라 미래 참조 없음."""
import pickle
import sys
from pathlib import Path
sys.path.insert(0, "/home/user/stock-dash")
import caps
import hlab as H
import lab
import rule
import study

path = Path(".cache") / "hourly_tables.pkl"
saved = pickle.loads(path.read_bytes())
ranks, trend = saved["ranks"], saved["trend"]
last = max(ranks)
print("표 마지막 날", last)
prices = study.load_prices()
codes = sorted(prices)
fresh = []
for s in range(0, len(codes), 40):
    part = {c: prices[c] for c in codes[s:s + 40]}
    for r in lab.build(part, horizons=(0,)):
        if r["date"] > last:
            fresh.append(r)
caps.tag(fresh, 150)
edge = saved.get("edge_2609")
if edge is None:
    rows_m = None
    import json
    edge = json.load(open("study/a_group.json", encoding="utf-8")).get("calm_edge")
print("새 줄", len(fresh), "· 조용함 문턱", edge)
added = 0
for r in fresh:
    if r.get(caps.RANK):
        ranks.setdefault(r["date"], {})[r["code"]] = r[caps.RANK]
        vol = r.get("변동성")
        if (r[caps.RANK] <= rule.TOP and vol is not None and vol <= edge
                and (r.get("추세 기울기") or -99) >= rule.SLOPE and (r.get("60일 전 대비") or -99) >= rule.SIXTY):
            trend[(r["code"], r["date"])] = True
            added += 1
saved["ranks"], saved["trend"] = ranks, trend
saved["filled_after"] = last
tmp = path.with_suffix(".tmp")
tmp.write_bytes(pickle.dumps(saved))
tmp.replace(path)
print("채운 날", sorted(d for d in ranks if d > last), "· 추세 문", added)
