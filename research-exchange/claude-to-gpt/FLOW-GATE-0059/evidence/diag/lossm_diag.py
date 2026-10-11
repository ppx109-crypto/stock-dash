"""FLOW-GATE-0059 사전등록 전 진단(판정 밖): 완료 114달 손실 여부 vs 전달 마지막 거래일까지 알 수 있는 값 12개.
달 값 · 손실 달: VOL-SIZE-0057 all_rows.json 기준 칸(= MIX-0054 최종). 값: regime_dev.features(그날 장 끝까지 값만).
3등분(전체) 표 + 앞 반(2017-03 ~ 2021-12) 3분위 문턱을 뒤 반(2022-01 ~ 2026-08)에 그대로 쓴 표."""
import json, os, sys
sys.path.insert(0, "research"); os.environ.setdefault("REG_BOX", "FLOW-GATE-0059")
import pandas as pd
import mix54_run as M, regime_dev as D
D.BASE_CSV = M.BASES / f"{M.name((0.5, 0.3))}.csv"; D.DATA, D.FEAT = None, None
_, nst = D.account(dict(D.R0, **M.OVERLAYS["L0.4_S0.4"]))
feat = D.FEAT[1]
mp = json.load(open("research-exchange/claude-to-gpt/VOL-SIZE-0057/evidence/all_rows.json"))[0]["month_pct"]
last = {}
for d in sorted(feat):
    last[d[:6]] = d
allm = sorted(last)
rec = []
for m in sorted(mp):
    d = last[allm[allm.index(m) - 1]]; f = feat[d]
    rec.append(dict(m=m, ret=mp[m], loss=mp[m] < 0, state=nst.get(d), r10=f.get("r10"), r5=f.get("r5"), v20=f.get("v20a"), vr=f.get("vol_ratio"),
                    ma20=f["close"] / f["ma20"] - 1, ma60=f["close"] / f["ma60"] - 1, ma200=f["close"] / f["ma200"] - 1, br=f.get("breadth"),
                    br20=f.get("br20"), F20=f.get("F20"), I20=f.get("I20"), prev=mp.get(allm[allm.index(m) - 1])))
X = pd.DataFrame(rec).set_index("m")
print("달", len(X), "손실", int(X.loss.sum()))
F, K = X[X.index < "202201"], X[X.index >= "202201"]
for c in ["r10", "r5", "v20", "vr", "ma20", "ma60", "ma200", "br", "br20", "F20", "I20", "prev"]:
    q1, q2 = F[c].quantile([1 / 3, 2 / 3])
    tab = lambda Y: [(len(z), round(z.loss.mean() * 100), round(z.ret.mean(), 2)) for z in (Y[Y[c] <= q1], Y[(Y[c] > q1) & (Y[c] <= q2)], Y[Y[c] > q2])]
    print(f"{c}: 앞 문턱 {q1:.4f} / {q2:.4f} · 앞 반 (달 · 손실% · 평균%) {tab(F)} · 뒤 반 {tab(K)}")
print("전달 끝 국면별", X.groupby("state").agg(n=("loss", "size"), loss=("loss", "mean")).round(2).to_dict("index"))
