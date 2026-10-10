"""D1-SIMPLE-0041 합성 시험 — 새 부품(지수이동평균 정배열 · 깨지면 팖)이 그날 종가까지만 쓰는지. 실제 수익 셈 없음."""
import importlib.util, random, sys
from pathlib import Path
R = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(R))
spec = importlib.util.spec_from_file_location("t011", R / "research/t011.py")
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
fails = []
def ok(c, m):
    print(("통과 " if c else "실패 ") + m)
    if not c: fails.append(m)
rng = random.Random(5); c, v = [], 10000.0
for i in range(900):
    v *= 1 + rng.gauss(0.0006, 0.02); c.append(v)
full = t.aligned_list(c)
for cut in (300, 500, 777):
    ok(t.aligned_list(c[:cut]) == full[:cut], f"정배열 자르기 {cut}칸: 앞부분 한 칸도 같음")
c2 = c[:600] + [x * 0.3 for x in c[600:]]
ok(t.aligned_list(c2)[:600] == full[:600], "600칸 뒤 값을 70% 깎아도 앞 600칸 정배열 같음")
ok(not any(full[:t.WARM]), "앞 250칸은 신호 없음")
ok(sum(full) > 0, f"켜진 칸이 있음({sum(full)})")
up = [100 * 1.01 ** i for i in range(400)]
a = t.aligned_list(up)
ok(all(a[t.WARM:]), "꾸준히 오르면 250칸 뒤 늘 정배열")
ema = {"X": a}
lane = {"code": "X", "closes": up}
go = t.exit_rule(ema)
ok(go(lane, 260, up[260], 5, up[265]) is False, "정배열이면 안 팖")
ema2 = {"X": a[:300] + [False] * 100}
ok(t.exit_rule(ema2)(lane, 290, up[290], 10, up[300]) is True, "정배열 깨진 칸에서 팖")
down = up[:300] + [up[299] * 0.85] * 100
ok(t.exit_rule({"X": [True] * 400}, -10.0)({"code": "X", "closes": down}, 299, up[299], 1, up[299]) is True, "S2: −15%면 손절")
ok(t.exit_rule({"X": [True] * 400})({"code": "X", "closes": down}, 299, up[299], 1, up[299]) is False, "S1: 손절 없음")
print(f"합계: 실패 {len(fails)}"); sys.exit(1 if fails else 0)
