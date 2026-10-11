"""AUDIT-MIX54-0066 — 지금 판(MIX-0054) 백테스트 진단(사용자 2026-10-11 "백테스트하여 보완할점 찾아줘") · 판정 없음 · 성과 고르기 없음.
① 기간별 · 바탕 대비 ② 나쁜 날 ③ 국면별 덧붙임 기여 · 해마다 ④ 상승에서 빠져나오기 직전 5일 비용 ⑤ 횡보 인버스 ⑥ 물속 기간
⑦ ETF 비용 민감도 ⑧ 덧붙임 규칙만(바탕 = 현금)을 판 고를 때 안 본 2010-03 ~ 2016 ⑨ 15:15 값과 종가 차(069500 · 1년)
python3 audit.py  (저장소 뿌리에서)"""
import csv, json, os, sys, statistics as S
sys.path.insert(0, "research"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("REG_BOX", "AUDIT-MIX54-0066")
import mix54_run as M, regime_dev as D
import overlay_live_main as O                      # main의 모의투자 덧붙임 판정(같은 규칙)
D.BASE_CSV = M.BASES / f"{M.name((0.5, 0.3))}.csv"; D.DATA, D.FEAT = None, None
cfg = dict(D.R0, **M.OVERLAYS["L0.4_S0.4"])
navs, nst = D.account(cfg); base, etf, br, flow = D.data(); ds = sorted(navs)
b0 = {d: base[d][0] / base[ds[0]][0] for d in ds}
def ann(nv, a, b, days=ds):
    sub = [d for d in days if a <= d <= b]; return ((nv[sub[-1]] / nv[sub[0]]) ** (250 / len(sub)) - 1) * 100
kx = {d: etf["069500"][d] for d in ds}
print("① 기간별 연 %: 판 · 바탕(덧붙임 없음) · KODEX200")
for a, b in (("20170201", "20260915"), ("20170201", "20221231"), ("20230101", "20260915")):
    print(f"  {a}~{b}: {ann(navs,a,b):.1f} · {ann(b0,a,b):.1f} · {ann(kx,a,b):.1f}")
r = {ds[j]: navs[ds[j]] / navs[ds[j-1]] - 1 for j in range(1, len(ds))}
rb = {ds[j]: b0[ds[j]] / b0[ds[j-1]] - 1 for j in range(1, len(ds))}
rk = {ds[j]: kx[ds[j]] / kx[ds[j-1]] - 1 for j in range(1, len(ds))}
ov = {d: r[d] - rb[d] for d in r}
print("② 나쁜 날 6(판 · 바탕 · KODEX200 · 전날 국면)")
for d in sorted(r, key=r.get)[:6]:
    print(f"  {d}: {r[d]*100:.2f} · {rb[d]*100:.2f} · {rk[d]*100:.2f} · {nst[d]}")
print("③ 국면별 덧붙임 기여(판 − 바탕 · 하루 합)")
for s in ("상승", "횡보", "하락"):
    v = [ov[d] for d in r if nst[d] == s]; print(f"  {s}: {len(v)}날 · 합 {sum(v)*100:.1f}%p")
for y in sorted({d[:4] for d in ds}):
    print(f"  {y}: {sum(v for d,v in ov.items() if d[:4]==y)*100:.1f}%p")
sw = [j for j in range(2, len(ds)) if nst[ds[j]] != nst[ds[j-1]]]
late = [sum(ov[ds[k]] for k in range(max(1, j-5), j)) for j in sw if nst[ds[j-1]] == "상승"]
ent = [sum(ov[ds[k]] for k in range(j, min(len(ds), j+5))) for j in sw if nst[ds[j]] == "상승"]
print(f"④ 국면 바뀜 {len(sw)} · 상승에서 빠져나오기 직전 5일 덧붙임 합 {sum(late)*100:.1f}%p({len(late)}번) · 상승 들어간 뒤 5일 합 {sum(ent)*100:.1f}%p")
side = [d for d in r if nst[d] == "횡보"]
print(f"⑤ 횡보 날 KODEX200 하루 평균 {S.mean(rk[d] for d in side)*100:.3f}% · 오른 날 {sum(1 for d in side if rk[d]>0)/len(side)*100:.1f}%")
pk, pki, longest = 0, 0, (0, None, None)
for i, d in enumerate(ds):
    if navs[d] >= pk: pk, pki = navs[d], i
    elif i - pki > longest[0]: longest = (i - pki, ds[pki], d)
print(f"⑥ 고점 회복 못한 가장 긴 기간 {longest[0]}거래일({longest[1]} ~ {longest[2]})")
for c in (0.0010, 0.0020):
    D.COST_ETF = c; n2, _ = D.account(cfg); print(f"⑦ ETF 비용 {c*100:.2f}% → 연 {ann(n2, ds[0], ds[-1]):.2f}%")
D.COST_ETF = 0.0005
px = {c: {d: float(x) for d, x in json.load(open(f"etf-data/{c}.json"))["closes"] if x} for c in ("069500", "122630", "114800")}
rows = sorted(px["069500"].items()); st = O.states(rows)
days = [d for d, _ in rows if d >= "20100301" and all(d in px[c] for c in ("122630", "114800"))]
code, ve, cash, pend = None, 0.0, 1.0, None; on = {days[0]: 1.0}
tgt = {"상승": ("122630", 0.4), "횡보": ("114800", 0.4), "하락": (None, 0.0)}
for j in range(1, len(days)):
    p, d = days[j-1], days[j]
    if code: ve *= px[code][d] / px[code][p]
    A = ve + cash; s = st[p]
    if s != pend or d[:6] != p[:6]:
        c2, w = tgt[s]; te = w * A
        A -= 0.0005 * (abs(te - ve) if c2 == code else ve + te)
        code = c2 if w > 0 else None; ve = w * A if code else 0.0; cash = A - ve; pend = s
    on[d] = ve + cash
k2 = {d: px["069500"][d] for d in days}
print("⑧ 덧붙임 규칙만(바탕 = 현금 · 레버리지 · 인버스 40%) 연 % · KODEX200")
for a, b in (("20100301", "20161231"), ("20170201", "20221231"), ("20230101", "20260915")):
    print(f"  {a}~{b}: {ann(on,a,b,days):.2f} · {ann(k2,a,b,days):.2f}")
print("  해마다:", {y: round((on[[d for d in days if d[:4]==str(y)][-1]] / on[[d for d in days if d[:4]==str(y)][0]] - 1) * 100, 1) for y in range(2010, 2027)})
bar = {}
for y in ("2025", "2026"):
    for row in csv.reader(open(f"etf-m15/069500/{y}.csv")):
        if row and row[0][8:12] == "1500": bar[row[0][:8]] = float(row[4])
g = [(px["069500"][d] / v - 1) * 100 for d, v in bar.items() if d in px["069500"]]
print(f"⑨ 069500 15:15 값 대 종가 차: {len(g)}날 · 절댓값 평균 {S.mean(map(abs,g)):.3f}% · 평균 {S.mean(g):.3f}% · 90% 분위 {sorted(map(abs,g))[int(.9*len(g))]:.3f}%")
