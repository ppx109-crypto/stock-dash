import sys, json; sys.path.insert(0, ".")
from feat import *
SIG = {d: {"R0": K.sig_r0(d), "S3": R4.s3(d)} for d in DAYS}
PNL = {d: {k: K.execute(d, SIG[d][k]) for k in ("R0", "S3")} for d in DAYS}
def run(choose):
    return {d: (PNL[d][choose(d)] if choose(d) else 0.0) for d in DAYS}
H = lambda d: "R0" if Z[d] else "S3"
# 60분 띠 순위: 앞 날들(평가 첫날 앞 준비 포함)과만 견줌
BH = {}; hist = []
for d in AD:
    if IDX[d] < 1: continue
    import bisect
    B, E10, E20b, keys = R4.TF[60]; i = bisect.bisect_left(keys, (d, 0)) - 1; b = abs(E10[i][0] - E20b[i][0]) / E10[i][1]
    BH[d] = (sum(1 for x in hist if x <= b) / len(hist)) if len(hist) >= 10 else None; hist.append(b)
V = {"H(기준)": H}
for k in (1.0, 1.5, 2.0):
    V[f"A z{k}: 조용 · |앞종가−EMA20|≥{k}ATR → 쉼"] = (lambda k: lambda d: (None if abs(F[d]["z"]) >= k else "R0") if Z[d] else "S3")(k)
for k in (1.0, 1.5, 2.0):
    V[f"B z{k}: 조용 · |z|≥{k} → S3"] = (lambda k: lambda d: ("S3" if abs(F[d]["z"]) >= k else "R0") if Z[d] else "S3")(k)
V["C 일봉 RNA 정렬 → 조용날 쉼"] = lambda d: (None if F[d]["rna"] != 0 else "R0") if Z[d] else "S3"
V["C2 일봉 RNA 정렬 → 조용날 S3"] = lambda d: ("S3" if F[d]["rna"] != 0 else "R0") if Z[d] else "S3"
for g in (0.3, 0.5):
    V[f"D 갭 |시가−앞종가|≥{g}ATR → 그날 쉼"] = (lambda g: lambda d: None if abs(F[d]["gap"]) >= g else H(d))(g)
V["E 60분 띠 순위≥0.8(벌어짐) → 그날 쉼"] = lambda d: None if (BH[d] is not None and BH[d] >= 0.8) else H(d)
V["E2 60분 띠 순위≤0.2(좁음) → 그날 쉼"] = lambda d: None if (BH[d] is not None and BH[d] <= 0.2) else H(d)
V["F 조용 무시: |z|≥1.5 → S3 · 아니면 R0"] = lambda d: "S3" if abs(F[d]["z"]) >= 1.5 else "R0"
res = {}; daily = {}
for name, ch in V.items():
    p = run(ch); s = stat(p); s["쉰날"] = sum(1 for d in DAYS if ch(d) is None); res[name] = s; daily[name] = {d: round(v, 4) for d, v in p.items()}
    print(name, s)
json.dump({"results": res, "n_variants_excl_base": len(V) - 1}, open("results.json", "w"), ensure_ascii=False, indent=1)
json.dump(daily, open("daily.json", "w"), ensure_ascii=False)
json.dump({d: {**{k: round(v, 3) for k, v in F[d].items()}, "quiet": Z[d], "band_rank": BH[d], "R0": round(PNL[d]["R0"], 2), "S3": round(PNL[d]["S3"], 2)} for d in DAYS}, open("features.json", "w"), ensure_ascii=False)
