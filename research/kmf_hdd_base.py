"""H 낙폭 줄이기 연구 공통: 조용함 판단은 원판과 같은 식(앞 20일 폭 가운데 값 · 그 앞 값들과만 순위 ≤ 0.6)이되 준비 문턱만 20개 → 10개(03-06 뒤는 원판과 같은 결정)."""
import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf_nb as K, kmf_rlk4 as R4, kmf_rl4 as R
def quiet(q=0.6, minh=10):
    out, hist = {}, []
    for d in K.DAYS:
        if d not in K.MED20: continue
        if len(hist) >= minh: out[d] = sum(1 for h in hist if h <= K.MED20[d]) / len(hist) <= q
        hist.append(K.MED20[d])
    return out
Z = quiet(); DAYS = [d for d in K.DAYS if d in Z]
assert all(Z[d] == R.Z[d] for d in R.Z if d in Z)
def stat(p, days=None):
    days = days or DAYS; v = [p[d] for d in days]; eq = pk = mdd = 0; cur = best = 0; uw = muw = 0; mon = collections.defaultdict(float)
    for d, x in zip(days, v):
        eq += x; mon[d[:6]] += x
        if eq >= pk: pk = eq; uw = 0
        else: uw += 1; muw = max(muw, uw)
        mdd = min(mdd, eq - pk)
        if x < 0: cur += 1; best = max(best, cur)
        elif x > 0: cur = 0
    half = len(days) // 2
    return {"합": round(sum(v), 1), "MDD": round(mdd, 1), "최악": round(min(v), 1), "연속손실": best, "회복최장": muw, "나쁜달": round(min(mon.values()), 1),
            "앞반": round(sum(v[:half]), 1), "뒤반": round(sum(v[half:]), 1)}
