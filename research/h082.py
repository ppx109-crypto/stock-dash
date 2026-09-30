"""1시간봉 82회차 — 들고 있는 종목에 희석 공시(유상증자 · CB · BW · EB)가 새로 나오면 판다(80회차: 2024-10-30 고려아연 유상증자 발표로 하루 −13.8%).
판단: 봉이 닫힌 뒤 그 봉에 붙은(또는 다음 봉에 붙을) 일봉 재료의 날까지 접수된 공시 중 산 날 뒤의 것 — 공시는 접수 다음 날부터 앎 → 다음 봉 시가에 팜.
견줌: 최고 규칙 · 최고 + 희석 공시 거르기(사기 전) · 최고 + 사기 전 거르기 + 들고 있다 공시 나면 팔기. 바뀐 매매를 직접 봄."""
import sys, json, bisect
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
BASE = make_exit()
DIL = ("유상증자", "전환사채", "신주인수권부사채", "교환사채")
EV = {c: sorted(x for k in DIL for x in H._events(c).get(k, ())) for c in data}
def e_dil(c, b):
    m = np.asarray(e_align_or_noon(c, b), bool).copy(); n = len(b["t"])
    for k in np.flatnonzero(m):
        x = ATT[c][k + 1] if k + 1 < n else ATT[c][k]
        if x and x["희석20"]: m[k] = False
    return m
def sell_on_dil(c, b, p, k):
    r = BASE(c, b, p, k)
    if r: return r
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    x0 = ATT[c][p["i"]]
    if x and x0:
        e = EV[c]; j = bisect.bisect_right(e, x0["날"])
        if j < len(e) and e[j] <= x["날"]: return "all"
    return 0
def trim(e, ex):
    sg = {c: np.asarray(e(c, b), bool) for c, b in data.items()}; got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sg, ex, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
print("== 1시간봉 82회차 (들고 있다가 희석 공시 나면 팔기) ==", flush=True)
base0 = {}
for tag, e, ex in (("최고", e_align_or_noon, BASE), ("최고 + 사기 전 희석 거르기", e_dil, BASE), ("+ 들고 있다 희석 공시 나면 팔기", e_dil, sell_on_dil)):
    res = H.simulate(data, e, ex, size, rank=rank, stale_of=stale90, seeds=16)
    tr = trim(e, ex)
    print(f"  {tag:26s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
    for s in ("앞", "뒤"):
        L = {(t["code"], t["산 때"]): t for t in res[s]["목록"] if not t["나눠"]}
        if tag.startswith("최고 +"): base0[s] = L
        if tag.startswith("+ 들고"):
            ch = [(k, base0[s][k]["손익"], L[k]["손익"]) for k in L if k in base0.get(s, {}) and abs(L[k]["손익"] - base0[s][k]["손익"]) > 0.01 and L[k]["판 때"] != base0[s][k]["판 때"]]
            print(f"      [{s}] 바뀐 매매 {len(ch)}건 · 전 {np.mean([a for _, a, _ in ch]) if ch else 0:+.2f}% → 뒤 {np.mean([b_ for _, _, b_ in ch]) if ch else 0:+.2f}% · " + " ".join(f"{k[0]}:{a:+.0f}→{b_:+.0f}" for k, a, b_ in ch[:8]), flush=True)
print("끝", flush=True)
