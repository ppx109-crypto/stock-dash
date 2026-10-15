"""MPOS-0009 해부(고르기 · 판정 없음): ① P0 손실 달 40의 크기 · 봇별 기여 · 국면(MPOS-0001 decomp_out 재사용) ② 달 평균 · 흔들림으로 손실 달 수 설명(정규 근사)."""
import json, math, statistics as S, collections, sys
dec, res = sys.argv[1], sys.argv[2]
d = json.load(open(dec))["day"]
mon = collections.defaultdict(lambda: collections.defaultdict(float)); st = collections.defaultdict(collections.Counter)
for k, v in d.items():
    m = k[:6]; mon[m]["r"] = (1 + mon[m]["r"]) * (1 + v["r"]) - 1
    for b in ("add", "1d", "basket", "engine", "inverse"): mon[m][b] += v[b]
    st[m][v["st"]] += 1
full = [m for m in sorted(mon) if "201703" <= m <= "202608"]; loss = [m for m in full if mon[m]["r"] < 0]
B = ("add", "1d", "basket", "engine", "inverse")
out = {"달": len(full), "손실": len(loss), "손실 달 크기(%)": sorted(round(mon[m]["r"] * 100, 2) for m in loss),
       "−1%보다 얕은 손실 달": sum(1 for m in loss if mon[m]["r"] > -0.01),
       "손실 달 평균 기여 %p": {b: round(S.mean(mon[m][b] for m in loss) * 100, 3) for b in B},
       "이익 달 평균 기여 %p": {b: round(S.mean(mon[m][b] for m in full if m not in loss) * 100, 3) for b in B},
       "가장 끌어내린 봇": dict(collections.Counter(min(B, key=lambda b: mon[m][b]) for m in loss)),
       "국면별 손실/전체": {s: [sum(1 for m in loss if st[m].most_common(1)[0][0] == s), sum(1 for m in full if st[m].most_common(1)[0][0] == s)] for s in ("상승", "횡보", "하락")}}
v = list(json.load(open(res))["P0"]["달"].values()); mu, sd = S.mean(v), S.stdev(v)
nd = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
out["P0 달 μ · σ · μ/σ"] = [mu * 100, sd * 100, mu / sd]; out["정규 근사 손실 달"] = 114 * nd(-mu / sd)
need = {}
for t in (30, 20, 10, 1):
    lo, hi = 0.0, 5.0
    for _ in range(60):
        k = (lo + hi) / 2
        lo, hi = (k, hi) if 114 * nd(-k) > t else (lo, k)
    need[t] = {"μ/σ": k, "σ 그대로면 달 μ%": k * sd * 100, "μ 그대로면 달 σ%": mu / k * 100}
out["손실 달 목표별 필요"] = need
print(json.dumps(out, ensure_ascii=False, indent=1))
