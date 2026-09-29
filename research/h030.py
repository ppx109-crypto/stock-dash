"""1시간봉 30회차(탐색 줄) — 종목 무리(같이 움직이는 종목) 흐름.
업종 코드는 절반만 있어(DART induty_code 196/435) 값으로 무리를 만듦: 달이 바뀔 때마다 **그 전 120거래일** 일봉 수익률 상관이
가장 높은 10종목 = 그 달의 무리(미래 참조 없음). 무리 힘 = 무리 가운데 일봉 정배열(전 거래일) 몫.
가설: 재료가 켜진 종목 가운데 무리도 함께 오르는(테마가 도는) 종목이 더 멀리 감 → ① 무리 힘으로 거르기 ② 무리 힘이 세면 4칸 ③ 사는 순서.
점검: 막은 매매 손익 · 반기 · 문턱 고원(0.2 · 0.3 · 0.4 · 0.5)."""
import sys, json, bisect
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
from pathlib import Path
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

# 일봉 종가 표(2022~)
closes = {}
for c in data:
    rows = [x for x in json.loads(Path(f"price-data/{c}.json").read_text(encoding="utf-8"))["closes"] if x[0] >= "20220101"]
    closes[c] = dict((x[0], x[1]) for x in rows)
days = sorted({d for m in closes.values() for d in m})
cl = list(closes)
M = np.full((len(days), len(cl)), np.nan)
di = {d: i for i, d in enumerate(days)}
for j, c in enumerate(cl):
    for d, v in closes[c].items(): M[di[d], j] = v
R = np.diff(np.log(M), axis=0)          # R[i] = days[i] → days[i+1]
PEERS = {}                              # 달(YYYYMM) → {code: [peers]}
for ym in sorted({d[:6] for d in days if d >= "20230801"}):
    i0 = bisect.bisect_left(days, ym + "01")          # 그 달 첫 거래일 앞까지
    X = R[max(0, i0 - 121):i0 - 1]                      # 끝 = days[i0-1] 종가까지
    ok_col = np.sum(~np.isnan(X), axis=0) >= 100
    Xf = np.where(np.isnan(X), 0, X)
    Xf = (Xf - Xf.mean(0)) / (Xf.std(0) + 1e-12)
    C = (Xf.T @ Xf) / len(Xf)
    got = {}
    for j, c in enumerate(cl):
        if not ok_col[j]: continue
        cc = C[j].copy(); cc[j] = -9; cc[~ok_col] = -9
        got[c] = [cl[t] for t in np.argsort(-cc)[:10]]
    PEERS[ym] = got
CTXD = {c: CTX[c] for c in CTX}
def peer_power(c, day):
    """day(전 거래일) 기준 무리 힘 — 무리는 day가 속한 달의 것(그 달 첫날 전까지로 만든)."""
    ps = PEERS.get(day[:6], {}).get(c)
    if not ps: return None
    v = [CTXD[p][day]["정배열"] for p in ps if p in CTXD and day in CTXD[p]]
    return sum(v) / len(v) if len(v) >= 5 else None
PP = {}
def pp_bar(c, b):
    if c in PP: return PP[c]
    ds = sorted(CTX[c]); out = np.full(len(b["t"]), np.nan); last = None; val = np.nan
    for k, t in enumerate(b["t"]):
        if t[:8] != last:
            last = t[:8]; pd = H.prev_day(ds, t)
            v = peer_power(c, pd) if pd else None
            val = np.nan if v is None else v
        out[k] = val
    PP[c] = out
    return out
def gate(th):
    return lambda c, b: e_align_or_noon(c, b) & (np.nan_to_num(pp_bar(c, b), nan=0) >= th)
def size_pp(th):
    def f(c, b, k):
        v = pp_bar(c, b)[k]
        return 4 if (size(c, b, k) == 4 or (not np.isnan(v) and v >= th)) else 2
    return f
def rank_pp(c, b, k):
    v = pp_bar(c, b)[k]
    return rank(c, b, k) + (-(0 if np.isnan(v) else v),)

print("== 1시간봉 30회차 (종목 무리 흐름) ==", flush=True)
print("  무리 예:", {k: PEERS["202501"].get(k, [])[:5] for k in ("005930", "000660")}, flush=True)
base = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)
print(f"  {'지금':24s} " + H.line(base), flush=True)
keyb = {s: {(t["code"], t["산 때"]): t for t in base[s]["목록"]} for s in ("앞", "뒤")}
# 무리 힘별 매매 손익(견줌 목록)
for s in ("앞", "뒤"):
    buck = {}
    for t in base[s]["목록"]:
        k = data[t["code"]]["t"].index(t["산 때"])
        v = pp_bar(t["code"], data[t["code"]])[k - 1]
        g = "모름" if np.isnan(v) else ("0~.2" if v < .2 else ".2~.4" if v < .4 else ".4~.6" if v < .6 else ".6~")
        buck.setdefault(g, []).append(t["손익"])
    print(f"  {s} 무리 힘별 매매:", {g: f"{len(v)}건 {np.mean(v):+.2f}%" for g, v in sorted(buck.items())}, flush=True)
for th in (0.2, 0.3, 0.4, 0.5):
    res = H.simulate(data, gate(th), exit_daily, size, rank=rank)
    chk = []
    for s in ("앞", "뒤"):
        now = {(t["code"], t["산 때"]) for t in res[s]["목록"]}
        gone = [t for k, t in keyb[s].items() if k not in now]
        chk.append(f"{s} 빠진 {len(gone)}건 평균 {np.mean([t['손익'] for t in gone]) if gone else 0:+.2f}%")
    print(f"  {f'거르기 무리 힘 ≥ {th}':24s} " + H.line(res), flush=True)
    print(f"      {' · '.join(chk)} · 반기 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
for th in (0.4, 0.6):
    res = H.simulate(data, e_align_or_noon, exit_daily, size_pp(th), rank=rank)
    print(f"  {f'무리 힘 ≥ {th}면 4칸':24s} " + H.line(res), flush=True)
res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank_pp)
print(f"  {'무리 힘 센 것 먼저 사기':24s} " + H.line(res), flush=True)
print("끝", flush=True)
