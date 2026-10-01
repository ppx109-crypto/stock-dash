"""1시간봉 121회차(K · 사용자 2026-10-02) — 1시간봉 최고 규칙(94회차)을 같은 종목 · 같은 1년으로 한투와 야후에 각각.
한투 = hourly-kis(15시 봉은 14시에 합침 · research/kis1h.py) · 야후 = hourly-data. 종목은 둘 다 있는 것만.
기간: 앞 2025-09-17 ~ 2026-03-31 · 뒤 2026-04-01 ~ 2026-09-29 · 1년 통째. 씨앗 16 · 비용 0.30%(+ 1년은 0.5%도). Q_SRC=kis · yahoo."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import hlab as H
import kis1h

src = os.environ.get("Q_SRC", "kis")
COMMON = sorted(set(kis1h.load()) & set(H.load()))
if src == "kis":
    H.load = lambda codes=None: kis1h.load(codes or COMMON)
else:
    _orig = H.load
    H.load = lambda codes=None: _orig(codes or COMMON)
exec(open("/home/user/stock-dash/research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
SG = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
sigs = SG
KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(SG[c])]
rk = rk_of(tiers(20, 5, 3))
P = kis1h.PERIODS + (("1년", ("2025091700", "2026093000")),)
print(f"== 1시간봉 121회차: 94회차 규칙 · {'한투' if src == 'kis' else '야후'} · {len(data)}종목 · 같은 1년 ==", flush=True)
for cost in (H.COST, 0.5):
    res = H.simulate(data, lambda c, b: SG[c], EX, size, periods=P if cost == H.COST else P[2:], rank=rk, stale_of=stale90, seeds=16, cost=cost)
    for name, r in res.items():
        if r:
            print(f"  비용 {cost:.2f}% · {name}: 매매 {r['매매']} · 연 {r['연']}%(흔들림 {r['폭']}) · 골 {r['골']}% · 승률 {r['승률']} · "
                  f"단순 {r['단순']} · 행운뺌 {r['행운뺌']} · 큰2건뺌 {r['큰2건뺌']} · 회전 {r['회전']}배", flush=True)
print("끝", flush=True)
