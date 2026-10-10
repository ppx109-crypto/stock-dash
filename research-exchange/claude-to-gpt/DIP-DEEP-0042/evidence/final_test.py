"""DIP-DEEP-0042 마지막 시험 셈 부품 합성 시험 — nav · twr · control · boot(실제 자료 · 성과 셈 없음)."""
import sys, types
sys.path.insert(0, "/home/user/stock-dash/research")
import dip_final as F
fails = []
def ok(c, m):
    print(("통과 " if c else "실패 ") + m)
    if not c: fails.append(m)
days = [f"202301{d:02d}" for d in range(2, 22)]
lanes = {"A": {"날": days, "closes": [100.0] * 20}, "B": {"날": days, "closes": [100.0] * 10 + [110.0] * 10}}
led = [{"code": "A", "산 날": days[1], "판 날": days[5], "들고": 4, "자리": 2, "손익": -0.25, "행": {"i": 1}},
       {"code": "B", "산 날": days[8], "판 날": days[12], "들고": 4, "자리": 2, "손익": 9.75, "행": {"i": 8}}]
nv = dict(F.nav(led, lanes, days))
c = F.COST / 200
exp1 = 1 - 0.2 * (1 - (1 - c) ** 2)
ok(abs(nv[days[5]] - exp1) < 1e-12, "값이 그대로면 NAV는 비용(편도 0.125% × 2)만큼만 줄어듦")
exp2 = exp1 - 0.2 * exp1 + 0.2 * exp1 * (1 - c) * 1.1 * (1 - c)
ok(abs(nv[days[12]] - exp2) < 1e-12, "10% 오른 매매는 (자리 ÷ 10) × NAV × 10%만큼 오름(비용 포함)")
ok(abs(nv[days[9]] - exp1 * (1 - 0.2 * c)) < 1e-12 and abs(nv[days[10]] - (exp1 - 0.2 * exp1 + 0.2 * exp1 * (1 - c) * 1.1)) < 1e-12, "들고 있는 동안 날마다 종가로 평가(9칸 100원 · 10칸 110원)")
tw = F.twr([("시작", 1.0), ("20230102", 1.01), ("20230103", 1.0201)])
ok(abs(tw["years"]["2023"] - 0.0201) < 1e-12, "해 수익 = Π(1 + r) − 1(1% 두 날 = 2.01%)")
tw2 = F.twr([("시작", 1.0), ("20230102", 0.9), ("20230201", 0.9)])
ok(abs(tw2["worst_day"][1] + 0.1) < 1e-12 and abs(tw2["worst_month"][1] + 0.1) < 1e-12, "가장 나쁜 하루 · 달 TWR")
pool = [{"code": x, "date": days[1], "i": 1} for x in ("A", "B")]
lanes2 = {"A": {"날": days, "closes": [100.0] * 20}, "B": {"날": days, "closes": [100.0] * 20}}
led2 = [{"code": "A", "산 날": days[1], "판 날": days[5], "들고": 4, "자리": 2, "손익": 0, "행": {"i": 1}}]
v0, v1 = F.control(led2, pool, lanes2, 0), F.control(led2, pool, lanes2, 0)
ok(v0 == v1, "같은 seed면 같은 대조 값")
ok(abs(v0 - (-0.25 * 2 / 10 / 4)) < 1e-12, "후보가 든 A는 빼고 B를 고름 · 비용 · 자리 · 4해로 나눔")
F.REPS = 300
led3 = [{"판 날": f"2023{m:02d}10", "손익": 1.0} for m in range(1, 13)]
mm, lo, hi = F.boot(led3)
ok(mm == 1.0 and lo == 1.0 and hi == 1.0, "부트스트랩: 모두 1%면 구간도 1%")
print(f"합계: 실패 {len(fails)}"); sys.exit(1 if fails else 0)
