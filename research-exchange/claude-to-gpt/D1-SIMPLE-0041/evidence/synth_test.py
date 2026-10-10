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
# round 2: 판정 코드(엔진 출력 둘째 자리 값 · ≥ 0.5 같으면 통과)
B = {"앞": {"연수익": 13.86, "행운뺌": 12.65}, "뒤": {"연수익": 58.37, "행운뺌": 18.30}}
S = {"앞": {"연수익": 6.93, "행운뺌": 6.33}, "뒤": {"연수익": 29.19, "행운뺌": 9.15}}
c, l = t.label(B, S); ok(l == "CORE_RETAINED" and c["앞_연수익"]["pass"], "딱 절반(6.93 ÷ 13.86 = 0.5)은 통과 · 넷 모두면 CORE_RETAINED")
S2 = {"앞": {"연수익": 6.92, "행운뺌": 6.33}, "뒤": {"연수익": 29.19, "행운뺌": 9.15}}
c, l = t.label(B, S2); ok(l == "CORE_WEAK" and not c["앞_연수익"]["pass"], "6.92(절반 아래)면 CORE_WEAK")
c, l = t.label({"앞": {"연수익": -1.0, "행운뺌": 1}, "뒤": {"연수익": 1, "행운뺌": 1}}, S); ok(l == "CORE_WEAK", "B가 0 이하면 그 칸 실패")
c, l = t.label(B, {"앞": None, "뒤": S["뒤"]}); ok(l == "CORE_WEAK", "S1 결과 없음(60건 미만)이면 실패")
# round 2: 자료 해시가 다르면 멈춤
import types
t.CACHE_SHA = "0" * 64
try:
    t.lock_check(); ok(False, "해시 다르면 멈춰야 함")
except SystemExit as e:
    ok("해시 다름" in str(e), "캐시 해시가 다르면 셈 없이 멈춤")
print(f"합계: 실패 {len(fails)}"); sys.exit(1 if fails else 0)
