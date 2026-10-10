"""BRK-FLOW-0044 마지막 시험 셈 부품 합성 시험(DIP 판을 옮김) — nav · twr · control · boot(실제 자료 · 성과 셈 없음)."""
import sys, types
from pathlib import Path
sys.path.insert(0, "/home/user/stock-dash/research")
import brk_final as F
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
ok(abs(v0["annual"] - (-0.25 * 2 / 10 / 11)) < 1e-12 and v0 == {"annual": v0["annual"], "targets": 1, "picked": 1, "skipped": 0},
   "후보가 든 A는 빼고 B를 고름 · 비용 · 자리 · 11해로 나눔 · 대상 1 · 고름 1 · 건너뜀 0")
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
got3 = F.control(led3, pool3, lanes3, 0)
F.random.Random = orig
ok(got3["targets"] == 2 and got3["picked"] == 1 and got3["skipped"] == 1, "round 3: 대상 2 · 고름 1 · 건너뜀 1을 결과에 남김")
ok(picks and picks[0] == ["B"], "첫 매매: 후보가 든 A는 빼고, 줄이 짧은 C(산 칸 + 5 > 줄 끝)는 미리 뺌 → B만")
ok(len(picks) == 1, "둘째 매매: 대조가 이미 든 B · 후보가 든 A · 짧은 C를 빼니 후보 없음 → 건너뜀(중복 보유 없음)")
# round 2: 부트스트랩 = 빈 달 포함 연속 달력 격자
F.REPS = 300
led4 = [{"판 날": f"2023{m:02d}10", "손익": 1.0} for m in range(1, 13)]
mm, lo, hi, emp = F.boot(led4, "20230102", "20231229")
ok(mm == 1.0 and lo == 1.0 and hi == 1.0 and emp == 0, "부트스트랩: 모두 1%면 구간도 1% · 빈 복제 0")
ok(F.month_grid("20230102", "20230916") == [f"2023{m:02d}" for m in range(1, 10)], "달 격자는 빈 달을 포함해 이어짐")
# round 3: 45달이면 이은 블록을 45달까지만(48달 아님)
g45 = F.month_grid("20060102", "20161229")
led45 = [{"판 날": m + "10", "손익": float(k)} for k, m in enumerate(g45)]
class Zero(orig):
    def randrange(self, *a, **k): return 0
F.random.Random = Zero
mm, lo, hi, emp = F.boot(led45, "20060102", "20161229")
F.random.Random = orig
# 132달 = 6달 블록 22개(딱 나눠짐): 시작 달 0 고정이면 0 ~ 5달 값 평균 2.5
ok(len(g45) == 132 and abs(lo - 2.5) < 1e-12 and abs(hi - 2.5) < 1e-12, "H 132달 격자 · 블록 22개 · 원래 길이까지만")
led5 = [{"판 날": "20230110", "손익": 5.0}]
mm, lo, hi, emp = F.boot(led5, "20230102", "20241231")
ok(lo is None and emp > 0.05 * F.REPS, "매매가 한 달에만 있으면 빈 복제가 많아 구간 없음(조건 5 실패)")
# round 2: 잠금 · 영수증
import os, tempfile, json as _j, importlib
tmpd = Path(tempfile.mkdtemp())
# round 3: 영수증 경로는 환경 값으로 못 바꿈
os.environ["DIP_H_RECEIPT"] = str(tmpd / "우회.json")
F2 = importlib.reload(F)
ok(F2.RECEIPT == F2.BOX / "h_receipt.json" and "DIP_H_RECEIPT" not in open(F2.__file__).read().split("RECEIPT =")[1].split("\n")[0],
   "환경 값 DIP_H_RECEIPT를 줘도 영수증 경로는 고정")
F = F2
F.REPS = 300
# round 3: 잘못된 스냅샷은 영수증을 만들지 않음(사전검사가 먼저)
F.RECEIPT = tmpd / "h_receipt_bad.json"
try:
    F.prepare_h(str(tmpd / "없음.pkl")); ok(False, "없는 스냅샷이면 멈춰야 함")
except SystemExit as e:
    ok("없음" in str(e) and not F.RECEIPT.exists(), "H 스냅샷이 없으면 영수증 없이 멈춤")
bad = tmpd / "bad.pkl"; bad.write_bytes(b"not a pickle")
try:
    F.prepare_h(str(bad)); ok(False, "해시 다르면 멈춰야 함")
except SystemExit as e:
    ok("해시 다름" in str(e) and not F.RECEIPT.exists(), "H 스냅샷 해시가 다르면 영수증 없이 멈춤")
F.RECEIPT = tmpd / "h_receipt.json"
r1 = F.take_receipt("키")
ok(r1["status"] == "STARTED" and F.RECEIPT.exists(), "셈 전에 영수증(STARTED)을 원자적으로 만듦")
try:
    F.take_receipt("키"); ok(False, "두 번째는 멈춰야 함")
except SystemExit as e:
    ok("한 번만" in str(e), "영수증이 있으면 다시 셈하지 않고 멈춤")
real_lock = F.LOCK
fake = tmpd / "lock.json"
fake.write_text(_j.dumps({"research/brk_final.py": "0" * 64}))
F.LOCK = fake
try:
    F.lock_key(); ok(False, "잠금 다르면 멈춰야 함")
except SystemExit as e:
    ok("잠금 다름" in str(e), "brk_final.py 해시가 잠금과 다르면 멈춤")
F.LOCK = real_lock
# 잠근 규칙: 다음 날 팔기 · 신호 하루 밀기
lane = {"closes": [100, 101, 106, 99, 98] + [100] * 20}
ok(F.exits(lane, 0, 100, 2, 106) is False and F.exits(lane, 0, 100, 3, 106) is True, "팔기: 앞 칸(+6%)으로 판단해 다음 바 종가에 팖")
ok(F.exits({"closes": [100] * 15}, 0, 100, 10, 100) is False and F.exits({"closes": [100] * 15}, 0, 100, 11, 100) is True, "기간 10: 앞 칸까지 10 바 뒤 다음 바에 팖")
class Dm(F.Data):
    def __init__(self): pass
dm = Dm()
dm.LANES = {"X": {"closes": [100.0] * 60 + [101.0, 102.0], "날": [f"d{k:03d}" for k in range(62)]}}
dm.ROWMAP = {("X", 60): {"code": "X", "i": 60, "date": "d060"}}
dm.FLOW = {"X": (["d050"] * 0, {}, [0])}
dm.flow_sum = lambda r, n, col: 5.0
dm.ret = lambda r, n: 0.0
dm.ix_ret = lambda d, n: 0.0
ok(dm.holds({"code": "X", "i": 61, "date": "d061"}) is True, "어제(60칸) 고가 돌파 + 수급이면 오늘(61칸) 삼")
ok(dm.holds({"code": "X", "i": 60, "date": "d060"}) is False, "앞 칸(59) 줄이 대상 밖이면 안 삼")
dm.flow_sum = lambda r, n, col: -1.0 if col == "투신" else 5.0
ok(dm.holds({"code": "X", "i": 61, "date": "d061"}) is False, "투신 순매도면 안 삼")
print(f"합계: 실패 {len(fails)}"); sys.exit(1 if fails else 0)
