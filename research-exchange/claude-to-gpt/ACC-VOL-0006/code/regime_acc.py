# 설명용(공개): 통합 계좌 NAV(A0 · A1 · A2)를 코스피 달 등락으로 상승(>+3%) · 횡보 · 하락(<−3%) 나눠 장별 연 환산 · 최악 달
import json, sys
import pandas as pd
S = sys.argv[1]
k = json.load(open("/home/user/stock-dash/market-data/index_KOSPI.json"))["rows"]
kc = {}
for r in k: kc[r["date"][:6]] = r["종가"]
ks = pd.Series(kc).sort_index(); kr = ks.pct_change()
def ann(x):
    return ((1 + x).prod() ** (12 / len(x)) - 1) * 100 if len(x) else float("nan")
for tag, name in (("a0", "A0 지금 조합"), ("a1", "A1 1일봉 장치"), ("a2", "A2 계좌 장치(H5)")):
    N = pd.read_csv(f"{S}/h5_nav_{tag}.csv", index_col=0); N.index = N.index.astype(str)
    m = N["NAV"].groupby(N.index.str[:6]).last(); r = m.pct_change().dropna()
    reg = r.index.map(lambda x: "상승" if kr.get(x, 0) > .03 else ("하락" if kr.get(x, 0) < -.03 else "횡보"))
    line = f"{name}: "
    for g in ("상승", "횡보", "하락"):
        x = r[reg == g]
        line += f"{g} {len(x)}달 연 {ann(x):+.0f}% · 최악 달 {x.min()*100:+.1f}% · 오른 달 {(x > 0).sum()}/{len(x)} | "
    down = r[reg != "상승"]
    print(line + f"횡보+하락 연 {ann(down):+.1f}%", flush=True)
x = kr.loc[r.index]
print("코스피: " + " | ".join(f"{g} 연 {ann(x[reg == g]):+.0f}%" for g in ("상승", "횡보", "하락")))
