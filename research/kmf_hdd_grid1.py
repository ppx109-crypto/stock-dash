"""H 낙폭 줄이기 1차 격자(같은 158일 · 탐색 · 시도 수 모두 공개)."""
import sys, json, collections; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from kmf_hdd_base import *
def run(r0f=None, s3f=None, cap_r0=12.0, cap_s3=12.0, maxn_r0=2, maxn_s3=2, k=1.0, s=1.0, q=None, skip_after=0, rest_quiet=False):
    Zq = quiet(q) if q else Z; p = {}; lossrun = 0
    for d in DAYS:
        qd = Zq.get(d, False)
        if qd:
            if rest_quiet or (skip_after and lossrun >= skip_after): p[d] = 0.0; lossrun = 0 if skip_after and lossrun >= skip_after else lossrun; continue
            sig = K.sig_r0(d, k=k, s=s); sig = [x for x in sig if (r0f is None or r0f(d, x))]
            K.CAP = cap_r0; p[d] = K.execute(d, sig, maxn=maxn_r0); K.CAP = 12.0
            lossrun = lossrun + 1 if p[d] < 0 else 0
        else:
            sig = [x for x in R4.s3(d) if (s3f is None or s3f(d, x))]
            K.CAP = cap_s3; p[d] = K.execute(d, sig, maxn=maxn_s3); K.CAP = 12.0
    return p
def sl(d, x): return abs(R4.slope15(d, x[0]))
V = {"H(기준)": {}}
for c in (4, 6, 8): V[f"R0 날 하루 멈춤 −{c}"] = dict(cap_r0=float(c))
V["R0 하루 1번"] = dict(maxn_r0=1)
for k in (1.25, 1.5): V[f"R0 이격 k{k}"] = dict(k=k)
for s_ in (0.75, 1.5): V[f"R0 손절 {s_}ATR"] = dict(s=s_)
for t in (0.3, 0.5, 0.8): V[f"R0 기울기/ATR ≤ {t}일 때만"] = dict(r0f=(lambda d, x, t=t: sl(d, x) <= t))
for a, b in ((600, 900), (570, 840)): V[f"R0 진입 {a//60}:{a%60:02d}~{b//60}:{b%60:02d}"] = dict(r0f=(lambda d, x, a=a, b=b: a <= x[0] <= b))
for n in (1, 2): V[f"R0 손실 날 {n}번 이어지면 다음 조용한 날 쉼"] = dict(skip_after=n)
for qq in (0.4, 0.5): V[f"조용 문턱 q{qq}"] = dict(q=qq)
V["조용한 날 쉼(S3만)"] = dict(rest_quiet=True)
for c in (6, 8): V[f"S3 날 하루 멈춤 −{c}"] = dict(cap_s3=float(c))
V["S3 하루 1번"] = dict(maxn_s3=1)
out = {}
for name, kw in V.items():
    out[name] = stat(run(**kw)); print(f"| {name} | " + " | ".join(str(out[name][x]) for x in ("합", "MDD", "최악", "나쁜달", "앞반", "뒤반", "연속손실", "회복최장")) + " |")
json.dump(out, open(Path(__file__).resolve().parent / "kmf_hdd_grid1_out.json", "w"), ensure_ascii=False, indent=1); print("시도", len(V))
