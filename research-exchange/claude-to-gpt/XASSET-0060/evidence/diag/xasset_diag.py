"""XASSET-0060 사전등록 전 진단(판정 밖): 국내 상장 해외 · 금 · 달러 · 채권 ETF 달 수익 vs MIX-0054 최종 판 달 수익(완료 114달).
+ 바탕 장부 평균 현금 몫(덧붙임 앞)."""
import json, csv
import pandas as pd
rows = json.load(open("research-exchange/claude-to-gpt/VOL-SIZE-0057/evidence/all_rows.json"))
mp = pd.Series(rows[0]["month_pct"]); neg = set(rows[0]["neg_list"])
for c in ["133690", "132030", "261240", "148070", "143850", "114820", "153130", "195930", "241180", "245340"]:
    s = pd.Series({a: float(b) for a, b in json.load(open(f"etf-data/{c}.json"))["closes"]})
    m = (s.groupby(s.index.str[:6]).last().pct_change() * 100).reindex(mp.index)
    L, P = m[mp.index.isin(neg)], m[~mp.index.isin(neg)]
    print(c, "달", int(m.notna().sum()), "손실 달 평균", round(L.mean(), 2), "이익 달 평균", round(P.mean(), 2), "상관", round(m.corr(mp), 2))
import sys; sys.path.insert(0, "research")
import mix54_run as M
b = [(r["날"], float(r["NAV"]), float(r["현금"])) for r in csv.DictReader(open(M.BASES / f"{M.name((0.5, 0.3))}.csv"))]
b = [x for x in b if "20170201" <= x[0] <= "20260915"]
print("바탕 장부 평균 현금 몫(덧붙임 앞)", round(sum(c / n for _, n, c in b) / len(b) * 100, 1), "%")
