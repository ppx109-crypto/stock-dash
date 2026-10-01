"""1시간봉 101회차 — 15분봉 연구(36회차)에서 거꾸로 옮김: '그날 이미 +2% 위면 안 삼' · '장중 시장 흐름(같은 시각 종목들 오늘 수익 평균) −1% 아래면 안 삼'
을 1시간봉 최고 규칙(90 · 94회차)에 얹음. 15분봉 1년 자료에서는 두 반 모두 크게 나았음 → 1시간봉 연구의 긴 자료(앞 2023-10 ~ 2025-03 · 뒤 2025-04 ~ 2026-09)로 확인.
재료는 그 봉이 닫힌 때까지(m15feat.day_ret · market — 시간 단위와 상관없이 그날 첫 봉 시가 기준). 씨앗 16.
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("research/h094.py", encoding="utf-8").read().split('print("== 1시간봉 94회차')[0])
import m15feat as F

DR = {c: np.nan_to_num(F.day_ret(b), nan=0.0) for c, b in data.items()}
MK = F.market(data)
MKT = {c: np.nan_to_num(np.array([MK.get(t, np.nan) for t in b["t"]], float), nan=0.0) for c, b in data.items()}


def entry_f(noon="11", up=None, mkt=None):
    def f(c, b):
        good = np.ones(len(b["t"]), bool)
        if up is not None:
            good &= ~(DR[c] > up)
        if mkt is not None:
            good &= ~(MKT[c] < mkt)
        al = e_align(c, b) & good
        nn = ctx_now(c, b) & hour_is(b, noon) & good
        days = [t[:8] for t in b["t"]]
        seen, m = set(), np.zeros(len(b["t"]), bool)
        for k in np.flatnonzero(al | nn):
            if days[k] not in seen:
                m[k] = True
                seen.add(days[k])
        return m
    return f


def run(tag, fn):
    global sigs, KEYS
    sigs = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
    rk = rk_of(tiers(20, 5, 3))
    res = H.simulate(data, lambda c, b: sigs[c], EX, size, rank=rk, stale_of=stale90, seeds=16)
    print(f"  {tag:36s} " + H.line(res), flush=True)


print(f"== 1시간봉 101회차: 15분봉 거르기 거꾸로 옮기기 ({len(data)}종목) ==", flush=True)
run("최고 규칙(94회차) 그대로", entry_f())
run("+ 그날 +2% 위면 안 삼", entry_f(up=0.02))
run("+ 장중 시장 −1% 아래면 안 삼", entry_f(mkt=-0.01))
run("+ 둘 다", entry_f(up=0.02, mkt=-0.01))
run("+ 둘 다 · 정오 대신 10시 봉 뒤(11:00)", entry_f(noon="10", up=0.02, mkt=-0.01))
print("끝", flush=True)
