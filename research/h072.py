"""1시간봉 72회차 — 공시 거르기(67회차)의 고원: 공시 뒤 막는 기간 5 · 10 · 20 · 40 · 60거래일 × (자사주 · 희석 둘 다 / 자사주만 / 희석만).
공시는 접수 다음 날부터(사는 봉에 붙는 전 거래일 재료의 날까지 접수된 것). 바탕: 1시간봉 최고 규칙. 씨앗 16."""
import sys, json
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
BUY = ("자기주식취득", "자기주식신탁체결"); DIL = ("유상증자", "전환사채", "신주인수권부사채", "교환사채")
EV, DAYS = {}, {}
for c in data:
    EV[c] = H._events(c)
    p = Path(f"price-data/{c}.json")
    DAYS[c] = [x[0] for x in json.loads(p.read_text(encoding="utf-8"))["closes"]] if p.exists() else []
def blocked(c, k, n, kinds):
    b = data[c]; x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    if not x: return False
    d = DAYS[c]; i = d.index(x["날"]) if x["날"] in d else None
    return i is not None and H._had(EV[c], kinds, d, i, n)
def entry_of(n, kinds):
    cache = {c: np.array([not blocked(c, k, n, kinds) if sigs[c][k] else False for k in range(len(b["t"]))]) for c, b in data.items()}
    return lambda c, b: sigs[c] & cache[c]
EX = make_exit()
def trim(entry):
    sg = {c: np.asarray(entry(c, b), bool) for c, b in data.items()}; got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sg, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
print("== 1시간봉 72회차 (공시 거르기 고원) ==", flush=True)
# 확인: 20일 · 둘 다가 ATT의 자사주20 · 희석20과 같은가
e20 = entry_of(20, BUY + DIL)
same = all(np.array_equal(e20(c, b), sigs[c] & ~np.array([bool((ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]) and ((ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k])["자사주20"] or (ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k])["희석20"])) for k in range(len(b["t"]))])) for c, b in list(data.items())[:60])
print(f"  20일 · 둘 다 = 67회차와 같은 신호: {same}", flush=True)
cases = [("지금(거르기 없음)", lambda c, b: sigs[c])]
for n in (5, 10, 20, 40, 60):
    cases.append((f"둘 다 {n}일", entry_of(n, BUY + DIL)))
for n in (10, 20, 40):
    cases.append((f"자사주만 {n}일", entry_of(n, BUY)))
    cases.append((f"희석만 {n}일", entry_of(n, DIL)))
for tag, e in cases:
    res = H.simulate(data, e, EX, size, rank=rank, stale_of=stale90, seeds=16)
    tr = trim(e)
    nb = sum(int((sigs[c] & ~np.asarray(e(c, b), bool)).sum()) for c, b in data.items())
    print(f"  {tag:16s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']} · 막힌 신호 {nb}", flush=True)
print("끝", flush=True)
