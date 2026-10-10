import sys, random, math
sys.path.insert(0, "/home/user/stock-dash/research")
import importlib.util
spec = importlib.util.spec_from_file_location("t009", "/home/user/stock-dash/research/t009.py")
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
ok = lambda c, m: print(("통과 " if c else "실패 ") + m)
ok(abs(t.side(5000, t.MAIN) - 0.00115) < 1e-12, "편도 비용 5,000원 = 0.115%")
days = [f"2016{m:02d}{d:02d}" for m in range(1, 13) for d in range(1, 29)][:300]
rng = random.Random(1)
px, v = {}, 5000.0
for d in days:
    v *= 1 + rng.gauss(0, 0.01); px[d] = round(v / 5) * 5
dist = {days[150]: 50.0}
tri = t.tri_of(days, px, dist)
for var in t.VARIANTS:
    full = t.signal(var, days, tri)
    cut = days[:200]
    tri_c = t.tri_of(cut, px, {k: x for k, x in dist.items() if k <= cut[-1]})
    part = t.signal(var, cut, tri_c)
    ok(all(full.get(d) == part.get(d) for d in cut), f"{var} 자르기(앞 200일 신호 같음) · 켜진 날 {sum(1 for x in full.values() if x)}")
# 덧대기: A · 인버스 값이 고정이면 들어갈 때 · 나올 때 비용만큼만 줄어야 함
base = {d: 100.0 for d in days}
flat = {d: 5000.0 for d in days}
on = {d: (100 <= i < 110) for i, d in enumerate(days)}
nav, alone = t.overlay(base, days, flat, {}, on, t.MAIN)
nv = dict(nav)
exp_in = 100 - 20 * (t.A_COST + 0.00115)
ok(abs(nv[days[101]] - exp_in) < 1e-9, f"들어간 날 NAV {nv[days[101]]:.6f} = {exp_in:.6f}")
b = 20 * (1 - 0.00115)
exp_out = 100 - 20 * (1 + t.A_COST) + b * (1 - 0.00115) * (1 - t.A_COST)
ok(abs(nv[days[111]] - exp_out) < 1e-9, f"나온 날 NAV {nv[days[111]]:.6f} = {exp_out:.6f}")
ok(abs(nv[days[100]] - 100) < 1e-12, "신호 켜진 그날 종가에는 안 삼(다음 날 종가)")
wins, op = t.windows_fix(base, days, flat, {}, on, t.MAIN)
ok(wins and wins[0][0] == days[101] and wins[0][1] == days[111], f"창 산 날 · 판 날 {wins[0][:2]}")
# 인버스 +10% 하루: 들고 있는 몫만 오름
px2 = dict(flat); 
for d in days[105:]: px2[d] = 5500.0
nav2, _ = t.overlay(base, days, px2, {}, on, t.MAIN)
n2 = dict(nav2)
ok(abs(n2[days[105]] - n2[days[104]] - b * 0.1) < 1e-9, "인버스 10% 오른 날 = 들고 있는 몫 × 10%")
days = [f"{2015 + i // 300}{(i % 300) // 25 + 1:02d}{i % 25 + 1:02d}" for i in range(900)]
px, v = {}, 5000.0
for d in days:
    v *= 1 + rng.gauss(0, 0.01); px[d] = round(v / 5) * 5
tri = t.tri_of(days, px, {})
for var in ("O10", "O20", "O40", "V90"):
    full = t.signal(var, days, tri)
    part = t.signal(var, days[:700], t.tri_of(days[:700], px, {}))
    ok(all(full.get(d) == part.get(d) for d in days[:700]), f"{var} 900일 · 자르기 700 같음 · 켜진 날 {sum(1 for x in full.values() if x)}")
on = t.signal("O20", days, tri)
runs = []; cur = 0
for d in days:
    if on.get(d): cur += 1
    elif cur: runs.append(cur); cur = 0
ok(runs and min(runs) >= 20, f"O20 켜진 덩어리 길이 최소 {min(runs) if runs else None}(≥ 20)")
