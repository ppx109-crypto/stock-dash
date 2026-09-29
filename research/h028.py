"""1시간봉 28회차(확인 줄) — 지수 1시간봉 날씨로 사는 때 거르기(코스피 · 코스닥).
가설: 긴 판 약한 반(앞)의 손실 매매는 지수가 1시간봉으로 꺾일 때 몰렸을 것. 종목 재료는 좋아도 지수가 1시간봉에서
내리막(종가 < EMA N 또는 EMA20 < EMA60)이면 그날은 사지 않음. 그 봉(신호 봉)까지 닫힌 지수 봉만 씀(같은 시각 · 없으면 앞 봉).
종목이 코스피냐 코스닥이냐에 따라 그 시장 지수(suffix.json)로, 또는 둘 다.
점검: 막은 매매의 손익(막지 않았다면) · 반기 · 문턱 고원(N = 20 · 60 · 120)."""
import sys, json, bisect
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import rna
from pathlib import Path
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

IDX = H.load(["KOSPI", "KOSDAQ"])
SUF = json.loads(Path("hourly-data/suffix.json").read_text(encoding="utf-8"))
E = {(nm, n): rna.ema(IDX[nm]["c"], n) for nm in IDX for n in (20, 60, 120)}
def idx_state(nm, T, rule):
    b = IDX[nm]; k = bisect.bisect_right(b["t"], T) - 1
    if k < 130: return True
    c = b["c"][k]
    if rule == "종가>EMA20": return c > E[(nm, 20)][k]
    if rule == "종가>EMA60": return c > E[(nm, 60)][k]
    if rule == "종가>EMA120": return c > E[(nm, 120)][k]
    if rule == "EMA20>EMA60": return E[(nm, 20)][k] > E[(nm, 60)][k]
    raise ValueError(rule)
def market(c): return "KOSDAQ" if SUF.get(c) == "KQ" else "KOSPI"
def gated(rule, which):
    def e(c, b):
        m = e_align_or_noon(c, b).copy()
        for k in np.flatnonzero(m):
            T = b["t"][k]
            names = {"제 시장": [market(c)], "코스피": ["KOSPI"], "코스닥": ["KOSDAQ"], "둘 다": ["KOSPI", "KOSDAQ"]}[which]
            if not all(idx_state(nm, T, rule) for nm in names): m[k] = False
        return m
    return e
print("== 1시간봉 28회차 (지수 1시간봉 날씨로 거르기) ==", flush=True)
print("  지수 봉:", {k: (len(v["t"]), v["t"][0], v["t"][-1]) for k, v in IDX.items()}, " 코스닥 종목 수:", sum(1 for c in data if market(c) == "KOSDAQ"), flush=True)
base = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)
print(f"  {'지금':26s} " + H.line(base), flush=True)
keyb = {s: {(t["code"], t["산 때"]): t for t in base[s]["목록"]} for s in ("앞", "뒤")}
for which in ("제 시장", "코스피", "둘 다"):
    for rule in ("종가>EMA20", "종가>EMA60", "종가>EMA120", "EMA20>EMA60"):
        res = H.simulate(data, gated(rule, which), exit_daily, size, rank=rank)
        chk = []
        for s in ("앞", "뒤"):
            now = {(t["code"], t["산 때"]) for t in res[s]["목록"]}
            gone = [t for k, t in keyb[s].items() if k not in now]
            chk.append(f"{s} 빠진 매매 {len(gone)}건 평균 {np.mean([t['손익'] for t in gone]) if gone else 0:+.2f}%")
        print(f"  {f'{which} · {rule}':26s} " + H.line(res), flush=True)
        print(f"      {' · '.join(chk)} · 반기 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
