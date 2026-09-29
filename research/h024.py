"""1시간봉 24회차 — 돌파 뒤 되밀림에서 사기(15회차: 돌파 + 거래량 뒤 약한 장에선 7~14봉 되밀렸다가 35봉 뒤 기준보다 크게 오름).
무엇을 = A그룹 꼴 + 가르침(전 거래일). 돌파 봉 = 1시간봉 종가가 7봉 최고가를 넘고 거래량 20봉 평균 2배(그 봉까지 앎).
사는 때: 돌파 봉 뒤 N봉 안(7 · 14)에 종가가 돌파 봉 종가보다 X%(1 · 2 · 3) 아래로 되밀렸다가, 다시 1시간봉 20봉 EMA 위로 닫힌 봉 다음 시가.
사건 연구(14 · 35봉 앞날) + 계좌(긴 판 · 짧은 판 B식 반 +8% · 반 따라가기)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import rna
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

_E = {}
def ema20(c, b):
    if c not in _E: _E[c] = rna.ema(b["c"], 20)
    return _E[c]
def burst_idx(c, b):
    okc = ctx_now(c, b)
    out = []
    for k in range(20, len(b["t"])):
        if not okc[k]: continue
        if b["c"][k] > b["h"][k - 7:k].max():
            v = b["v"][k - 20:k]
            if v.mean() > 0 and b["v"][k] >= 2 * v.mean():
                out.append(k)
    return out
def pullback(n, x):
    def e(c, b):
        m = np.zeros(len(b["t"]), bool)
        e20 = ema20(c, b); okc = ctx_now(c, b)
        for k0 in burst_idx(c, b):
            dipped = False
            for k in range(k0 + 1, min(k0 + 1 + n, len(b["t"]) - 1)):
                if b["c"][k] <= b["c"][k0] * (1 - x / 100): dipped = True
                if dipped and okc[k] and b["c"][k] > e20[k] and b["c"][k - 1] <= e20[k - 1]:
                    m[k] = True; break
        return m
    return e
K = (7, 14, 35)
print("== 1시간봉 24회차 (돌파 뒤 되밀림에서 사기) ==", flush=True)
H.show("재료 날 아무 봉", H.study(data, lambda c, b: ctx_now(c, b), uni, K, edge=False), K)
H.show("돌파 + 거래량 봉(15회차)", H.study(data, lambda c, b: np.isin(np.arange(len(b["t"])), burst_idx(c, b)), uni, K, edge=False), K)
for n in (7, 14):
    for x in (1, 2, 3):
        H.show(f"{n}봉 안 −{x}% 되밀림 뒤 20봉선 위로", H.study(data, pullback(n, x), uni, K, edge=False), K)
def exit_trail(c, b, p, k):
    if p["칸"] < p["처음칸"]:
        if b["c"][k] < ema20(c, b)[k] or k - p["i"] >= 70: return "all"
        return 0
    return "all" if k - p["i"] >= 35 else 0
take_half = lambda p: (p["price"] * 1.08, p["처음칸"] // 2) if p["칸"] == p["처음칸"] else (None, 0)
stop5 = lambda p: p["price"] * 0.95
print("-- 계좌", flush=True)
for n, x in ((7, 2), (14, 2), (14, 3)):
    E = pullback(n, x)
    res = H.simulate(data, E, exit_daily, size, rank=rank)
    print(f"  {f'긴 판 · {n}봉 안 −{x}% 되밀림':26s} " + H.line(res), flush=True)
    res = H.simulate(data, E, exit_trail, lambda c, b, k: 4, rank=rank, take_of=take_half, stop_of=stop5)
    print(f"  {f'짧은 판 · {n}봉 안 −{x}% 되밀림':26s} " + H.line(res), flush=True)
print("끝", flush=True)
