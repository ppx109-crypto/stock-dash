"""1시간봉 61회차 — 장 시작 · 마감 시간대. 바탕: 1시간봉 최고 규칙(정배열 된 봉 다음, 없으면 12시 · 자리 바꾸기 폭<90 · 일봉 파는 법).
① 산 봉 · 판 봉의 시각별 매매 수 · 매매당 손익(씨앗 0, 두 반)
② 사는 시각 바꾸기: 15시 봉 신호 버림(다음 날 09시 시가로 넘어가는 것 막기) · 09시 봉 신호 버림(장 첫 시간 흔들림) · 둘 다 ·
   정배열이 늦게 되면 버림(13 · 14시 뒤) · 모자라면 사는 시각 10 · 11 · 13 · 14시로(고원)
판단은 모두 봉 종가(그 봉까지) → 다음 봉 시가. 씨앗 16 · 큰 매매 뺀 연."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
def trim_of(entry):
    sg = {c: np.asarray(entry(c, b), bool) for c, b in data.items()}
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sg, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
def hours(b): return np.array([t[8:] for t in b["t"]])
def drop(hh_set, base=e_align_or_noon):
    def f(c, b):
        m = np.asarray(base(c, b), bool).copy()
        return m & ~np.isin(hours(b), list(hh_set))
    return f
def align_or(hh, last=None):
    def f(c, b):
        al = e_align(c, b); hr = hours(b)
        if last: al = al & (hr <= last)
        nn = ctx_now(c, b) & (hr == hh); days = [t[:8] for t in b["t"]]
        seen = set(); m = np.zeros(len(b["t"]), bool)
        for k in range(len(m)):
            if (al[k] or nn[k]) and days[k] not in seen:
                m[k] = True; seen.add(days[k])
        return m
    return f

print("== 1시간봉 61회차 (장 시작 · 마감 시간대) ==", flush=True)
res = H.simulate(data, e_align_or_noon, EX, size, rank=rank, stale_of=stale90, seeds=16)
for s in ("앞", "뒤"):
    L = res[s]["목록"]
    for key, name in (("산 때", "산"), ("판 때", "판")):
        tab = {}
        for t in L:
            tt = t[key] if not str(t[key]).startswith("끝") else t[key][1:]
            tab.setdefault(tt[8:10], []).append(t["손익"])
        print(f"  {s} {name} 봉 시각: " + " · ".join(f"{h}시 {len(v)}건 {np.mean(v):+.2f}%" for h, v in sorted(tab.items())), flush=True)
CASES = [("지금(정배열 다음, 없으면 11시 봉 → 12시 시가)", e_align_or_noon),
         ("15시 봉 신호 버림", drop({"15"})), ("09시 봉 신호 버림", drop({"09"})), ("09 · 15시 봉 신호 버림", drop({"09", "15"})),
         ("정배열은 13시 봉까지만", align_or("11", last="13")), ("정배열은 14시 봉까지만", align_or("11", last="14"))]
for hh in ("09", "10", "12", "13", "14"):
    CASES.append((f"없으면 {hh}시 봉 → 다음 봉 시가", align_or(hh)))
for tag, e in CASES:
    r = H.simulate(data, e, EX, size, rank=rank, stale_of=stale90, seeds=16)
    tr = trim_of(e)
    print(f"  {tag:34s} " + H.line(r), flush=True)
    print(f"      큰 매매 뺀 연(가운데): 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
