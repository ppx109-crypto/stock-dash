"""DIP-DEEP-0042 마지막 시험 셈 부품 합성 시험 — nav · twr · control · boot(실제 자료 · 성과 셈 없음)."""
import sys, types
from pathlib import Path
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
# round 2: 대조 포트폴리오 자기 중복 금지 · 미래 칸 부족 종목 미리 뺌
pool3 = [{"code": x, "date": days[1], "i": 1} for x in ("A", "B", "C")] + [{"code": x, "date": days[2], "i": 2} for x in ("A", "B", "C")]
lanes3 = {"A": {"날": days, "closes": [100.0] * 20}, "B": {"날": days, "closes": [100.0] * 20}, "C": {"날": days[:4], "closes": [100.0] * 4}}
led3 = [{"code": "A", "산 날": days[1], "판 날": days[6], "들고": 5, "자리": 2, "손익": 0, "행": {"i": 1}},
        {"code": "A2", "산 날": days[2], "판 날": days[7], "들고": 5, "자리": 2, "손익": 0, "행": {"i": 2}}]
lanes3["A2"] = {"날": days, "closes": [100.0] * 20}
picks = []
orig = F.random.Random
class Spy(orig):
    def choice(self, seq):
        x = super().choice(seq); picks.append([r["code"] for r in seq]); return x
F.random.Random = Spy
F.control(led3, pool3, lanes3, 0)
F.random.Random = orig
ok(picks and picks[0] == ["B"], "첫 매매: 후보가 든 A는 빼고, 줄이 짧은 C(산 칸 + 5 > 줄 끝)는 미리 뺌 → B만")
ok(len(picks) == 1, "둘째 매매: 대조가 이미 든 B · 후보가 든 A · 짧은 C를 빼니 후보 없음 → 건너뜀(중복 보유 없음)")
# round 2: 부트스트랩 = 빈 달 포함 연속 달력 격자
F.REPS = 300
led4 = [{"판 날": f"2023{m:02d}10", "손익": 1.0} for m in range(1, 13)]
mm, lo, hi, emp = F.boot(led4, "20230102", "20231229")
ok(mm == 1.0 and lo == 1.0 and hi == 1.0 and emp == 0, "부트스트랩: 모두 1%면 구간도 1% · 빈 복제 0")
ok(F.month_grid("20230102", "20230916") == [f"2023{m:02d}" for m in range(1, 10)], "달 격자는 빈 달을 포함해 이어짐")
led5 = [{"판 날": "20230110", "손익": 5.0}]
mm, lo, hi, emp = F.boot(led5, "20230102", "20241231")
ok(lo is None and emp > 0.05 * F.REPS, "매매가 한 달에만 있으면 빈 복제가 많아 구간 없음(조건 5 실패)")
# round 2: 잠금 · 영수증
import os, tempfile, json as _j
tmpd = Path(tempfile.mkdtemp())
F.RECEIPT = tmpd / "h_receipt.json"
r1 = F.take_receipt("키")
ok(r1["status"] == "STARTED" and F.RECEIPT.exists(), "셈 전에 영수증(STARTED)을 원자적으로 만듦")
try:
    F.take_receipt("키"); ok(False, "두 번째는 멈춰야 함")
except SystemExit as e:
    ok("한 번만" in str(e), "영수증이 있으면 다시 셈하지 않고 멈춤")
real_lock = F.LOCK
fake = tmpd / "lock.json"
fake.write_text(_j.dumps({"research/dip_final.py": "0" * 64}))
F.LOCK = fake
try:
    F.lock_key(); ok(False, "잠금 다르면 멈춰야 함")
except SystemExit as e:
    ok("잠금 다름" in str(e), "dip_final.py 해시가 잠금과 다르면 멈춤")
F.LOCK = real_lock
print(f"합계: 실패 {len(fails)}"); sys.exit(1 if fails else 0)
