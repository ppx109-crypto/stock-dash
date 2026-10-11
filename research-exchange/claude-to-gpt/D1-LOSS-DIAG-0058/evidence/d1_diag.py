"""D1-LOSS-DIAG-0058 진단 셈(판정 밖 · 성과 고르기 없음).
입력: Z_ATTR 장부(봇별 날마다 손익 · 저장소에 안 올림 · 경로는 인수) · 같은 실행의 NAV 장부 ·
      VOL-SIZE-0057 all_rows.json 기준 칸(최종 판 달 값 · 손실 달 목록) · market-data/index_KOSPI.json ·
      event-data/*.json(공시 목록 · 날짜만) · dart-events/*.json(주요사항 · 접수번호 앞 8자리 = 접수일)
python3 d1_diag.py <attr.csv> <base.csv>"""
import collections
import glob
import hashlib
import json
import os
import sys
import pandas as pd

sys.path.insert(0, "research")
os.environ.setdefault("REG_BOX", "D1-LOSS-DIAG-0058")
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402

ATTR, BASE = sys.argv[1], sys.argv[2]
ROWS = "research-exchange/claude-to-gpt/VOL-SIZE-0057/evidence/all_rows.json"
sha = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
print("입력 sha256", {"attr": sha(ATTR), "base": sha(BASE), "all_rows": sha(ROWS), "kospi": sha("market-data/index_KOSPI.json")})

A = pd.read_csv(ATTR, dtype={"날": str, "최대종목": str, "최악종목": str})
B = pd.read_csv(BASE, dtype={"날": str})
assert list(A.날) == list(B.날)
base = json.load(open(ROWS))[0]
neg = set(base["neg_list"])
k = pd.DataFrame(json.load(open("market-data/index_KOSPI.json"))["rows"]).set_index("date")["종가"]
km = k.groupby(k.index.str[:6]).last().pct_change() * 100
kr = k.pct_change() * 100

D.BASE_CSV = M.BASES / f"{M.name((0.5, 0.3))}.csv"
D.DATA, D.FEAT = None, None
_, nst = D.account(dict(D.R0, **M.OVERLAYS["L0.4_S0.4"]))

A["m"] = A.날.str[:6]
A["share1d"] = (B["일봉"] / B["NAV"]).values
A["state"] = A.날.map(nst)
g = A.groupby("m")
nav0 = g["NAV전"].first()
mon = pd.DataFrame({b: g[b].sum() / nav0 * 100 for b in ("1d", "basket", "engine", "inverse")})
mon["share1d"] = g["share1d"].mean() * 100
mon["kospi"] = km
mon["up"] = g["state"].apply(lambda s: (s == "상승").mean() * 100)
mon["down"] = g["state"].apply(lambda s: (s == "하락").mean() * 100)
mon = mon.loc["201703":"202608"]
mon["neg"] = mon.index.isin(neg)
L, P = mon[mon.neg], mon[~mon.neg]
print("완료 달", len(mon), "· 손실", len(L), "· 이익", len(P))
print("1일봉 달 손익 평균 %p: 손실 달", round(L["1d"].mean(), 2), "· 이익 달", round(P["1d"].mean(), 2))
print("1일봉 손익 < 0 인 달: 손실 달 중", int((L["1d"] < 0).sum()), "· 이익 달 중", int((P["1d"] < 0).sum()))
print("1일봉 평균 몫 %: 손실 달", round(L.share1d.mean(), 1), "· 이익 달", round(P.share1d.mean(), 1))
print("1일봉 달 손익 vs 코스피 상관", round(mon["1d"].corr(mon.kospi), 2))
# 국면 분류(배타 · GPT #241 정정 2): 하락 날이 하루라도 있음 → '하락 낌' · 아니면 상승 날 > 50% → '상승 위주' · 나머지 '횡보 위주'
mon["cls"] = ["하락 낌" if d > 0 else ("상승 위주" if u > 50 else "횡보 위주") for u, d in zip(mon.up, mon.down)]
for c in ("상승 위주", "횡보 위주", "하락 낌"):
    x = mon[mon.cls == c]
    print(f"{c}: 달 {len(x)} · 손실 달 {int(x.neg.sum())} · 1일봉 평균 {x['1d'].mean():.2f}%p · 코스피 {x.kospi.mean():.2f}%")
L2 = L.assign(worst=L[["1d", "basket", "engine", "inverse"]].idxmin(axis=1))
d1m = L2[L2.worst == "1d"]
print("바탕 봇 중 1일봉이 가장 크게 깎은 손실 달", len(d1m))
A2 = A[(A.날 >= "20170301") & (A.날 <= "20260831")].copy()
A2["d1r"] = A2["1d"] / A2["NAV전"] * 100
A2["w"] = A2["최악종목손익"] * 100
A2["kospi"] = A2.날.map(kr)
t = A2[A2.m.isin(d1m.index)]
print("그 달들 1일봉 손익 합", round(t.d1r.sum(), 1), "· 하루 −0.5%p 아래 날", int((t.d1r < -0.5).sum()), "/", len(t), "합", round(t[t.d1r < -0.5].d1r.sum(), 1))
neg_d = A2[A2.d1r < 0]
print("1일봉 잃은 날 손실 합", round(neg_d.d1r.sum(), 1), "· 그날 최악 한 종목 몫", round(neg_d.w.sum() / neg_d.d1r.sum() * 100, 1), "%")
ev = A2[A2.w < -0.5]
print("한 종목 하루 −0.5% 넘게 깎은 날", len(ev), "· 합", round(ev.w.sum(), 1))
for lo, hi in ((-99, -3), (-3, -1.5), (-1.5, 0), (0, 99)):
    x = ev[(ev.kospi > lo) & (ev.kospi <= hi)]
    print(f"  그날 코스피 {lo} ~ {hi}%: {len(x)}날 · 합 {x.w.sum():.1f}%p")
days = sorted(A2.날)
idx = {d: i for i, d in enumerate(days)}
E = {}
for f in glob.glob("event-data/*.json"):
    for x in json.load(open(f))["rows"]:
        E.setdefault(os.path.basename(f)[:6], []).append((x["date"], x["kind"]))
hits, n = collections.Counter(), 0
for r in ev.itertuples():
    win = set(days[max(0, idx[r.날] - 1):idx[r.날] + 1])
    ks = {kd for dt, kd in E.get(r.최악종목, ()) if dt in win}
    if ks:
        n += 1
        hits.update(ks)
print("공시 목록(event-data) 종목 수", len(E), "· 급락 종목이 그 안에 있는 비율", round(ev.최악종목.isin(E.keys()).mean() * 100, 1), "%")
print("급락 날 · 전 거래일에 공시가 있던 날", n, "/", len(ev), dict(hits.most_common(8)))
