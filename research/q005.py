"""15분봉 4회차 — 지금 가장 나은 판(0회차 + 정오 대신 10:45 봉 뒤 · 11:00 시가)의 '같은 때 순서'와 '10:45 사기 거르기'
(docs/DATA-AUDIT-15M.md 4절 ④). 10:45 봉에는 그때까지 정배열이 안 된 후보가 한꺼번에 나와, 칸이 모자랄 때 누구를 먼저 사느냐가 큼.
- 순서: 지금(추세 문 → 3일 연속 → 수급 순서 무리) 뒤에 장중 재료를 하나 더 붙임 — 같은 시각 거래량 배수 · 오늘 평균값 대비 ·
  오늘 수익(높은 것 먼저 / 낮은 것 먼저). 값은 신호 봉이 닫힌 때까지만(m15feat).
- 10:45 사기만 거르기(정배열 신호로 사는 것은 그대로): 오늘 평균값 아래 · 오늘 수익 −1% 아래 · 장중 시장 흐름 −0.5% 아래면 안 삼.
씨앗 16 · 두 반 · 비용 0.30%(+ 가장 나은 것은 0.5%).
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q002.py", encoding="utf-8").read().split('nan_ok = lambda')[0])

DR = {c: F.day_ret(b) for c, b in data.items()}
nan0 = lambda v: np.nan_to_num(v, nan=0.0)


def rank_plus(T, feat=None, high_first=True):
    def r(c, b, k):
        x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
        extra = 0.0
        if feat is not None:
            v = feat[c][k]
            extra = 0.0 if np.isnan(v) else (-v if high_first else v)
        return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, -T.get((c, k), 0), extra)
    return r


def noon_cut(test):
    """10:45 봉 사기 가운데 test(c, k)가 참인 것만 뺌(정배열로 산 신호는 그대로)."""
    base = entry(noon="1045")

    def f(c, b):
        m = base(c, b).copy()
        al = e_align(c, b)
        for k in np.flatnonzero(m):
            if not al[k] and HH[c][k] == "1045" and test(c, k):
                m[k] = False
        return m
    return f


def run3(tag, fn, feat=None, high_first=True, cost=H.COST):
    sigs = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    rk = rank_plus(tiers(sigs), feat, high_first)
    res = M.simulate(data, lambda c, b: sigs[c], exit_rule, size, rank=rk, stale_of=stale90, seeds=16, cost=cost)
    print(f"  {tag:34s} 신호 {sum(int(v.sum()) for v in sigs.values()):5d} " + H.line(res), flush=True)
    return res


best = entry(noon="1045")
print(f"== 15분봉 4회차: 같은 때 순서 · 10:45 사기 거르기 ({len(data)}종목) ==", flush=True)
run3("기준: 10:45 봉 뒤", best)
for name, feat in (("거래량 배수", RV), ("평균값 대비", VW), ("오늘 수익", DR)):
    run3(f"순서 + {name} 높은 것 먼저", best, feat, True)
    run3(f"순서 + {name} 낮은 것 먼저", best, feat, False)
run3("10:45 사기: 평균값 아래면 안 삼", noon_cut(lambda c, k: nan0(VW[c])[k] < 0))
run3("10:45 사기: 오늘 −1% 아래면 안 삼", noon_cut(lambda c, k: nan0(DR[c])[k] < -0.01))
run3("10:45 사기: 오늘 +3% 위면 안 삼", noon_cut(lambda c, k: nan0(DR[c])[k] > 0.03))
run3("10:45 사기: 장중 시장 −0.5% 아래면 안 삼", noon_cut(lambda c, k: nan0(MKT[c])[k] < -0.005))
run3("기준 · 비용 0.5%", best, cost=0.5)
print("끝", flush=True)
