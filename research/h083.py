"""1시간봉 83회차 — 자료 점검에서 찾은 빈틈 ①: 일봉 최고 규칙(새 RL 28회차)의 '45일 사이 증권사 목표가(가운데 값)가 내린 종목은 사지 않음'이
1시간봉 규칙에는 빠져 있었음. 같은 계산(study.target_timeline · nrl.target_cut과 같은 뜻)을 1시간봉에 넣어 봄.
목표가는 사는 날 **전날까지** 나온 것만(3달 넘게 새 목표가가 없으면 없음으로 봄). 45일 고원: 20 · 30 · 45 · 60 · 90일.
바탕: 1시간봉 최고 규칙(자리 바꾸기 폭<90). 씨앗 16 · 막힌 매매 직접 봄."""
import sys, bisect
sys.path.insert(0, "/home/user/stock-dash")
from datetime import date, timedelta
import numpy as np
import hlab as H
import study
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
TG = {}
for c in data:
    g = study.target_timeline(c)
    if g: TG[c] = ([d for d, _ in g], [x for _, x in g])
def tb(c, day, back=0):
    got = TG.get(c)
    if not got: return None
    days, vals = got
    if back:
        d = date(int(day[:4]), int(day[4:6]), int(day[6:8])) - timedelta(days=back); day = d.strftime("%Y%m%d")
    k = bisect.bisect_left(days, day)
    if k == 0: return None
    return vals[k - 1] if days[k - 1] >= study._months_before(day, 3) else None
def cut(c, day, back):
    a, b_ = tb(c, day), tb(c, day, back)
    return bool(a and b_ and a["목표가"] < b_["목표가"])
def e_cut(back):
    cache = {}
    for c, b in data.items():
        m = sigs[c].copy(); n = len(b["t"])
        for k in np.flatnonzero(m):
            day = b["t"][k + 1][:8] if k + 1 < n else b["t"][k][:8]
            if cut(c, day, back): m[k] = False
        cache[c] = m
    return lambda c, b: cache[c]
def trim(e):
    sg = {c: np.asarray(e(c, b), bool) for c, b in data.items()}; got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sg, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
print("== 1시간봉 83회차 (목표가 내림 빼기를 1시간봉에) ==", flush=True)
print(f"  목표가 자료 있는 종목 {len(TG)}/{len(data)}", flush=True)
base = None
for tag, e in [("지금(목표가 조건 없음)", lambda c, b: sigs[c])] + [(f"{n}일 사이 목표가 내림 빼기", e_cut(n)) for n in (20, 30, 45, 60, 90)]:
    res = H.simulate(data, e, EX, size, rank=rank, stale_of=stale90, seeds=16)
    tr = trim(e)
    nb = sum(int((sigs[c] & ~np.asarray(e(c, b), bool)).sum()) for c, b in data.items())
    msg = ""
    if base is None: base = res
    else:
        for s in ("앞", "뒤"):
            k0 = {(t["code"], t["산 때"]) for t in base[s]["목록"]}; k1 = {(t["code"], t["산 때"]) for t in res[s]["목록"]}
            gone = [t for t in base[s]["목록"] if (t["code"], t["산 때"]) in k0 - k1]
            msg += f" · {s} 빠진 매매 {len({(t['code'], t['산 때']) for t in gone})}건 평균 {np.mean([t['손익'] for t in gone]) if gone else 0:+.2f}%"
    print(f"  {tag:22s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']} · 막힌 신호 {nb}{msg}", flush=True)
print("끝", flush=True)
