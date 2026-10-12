"""KMF-0001 합성 시험(성과 셈 없음 · 가짜 분봉)."""
import json
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K  # noqa: E402
import numpy as np  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def bars(day, prices, start=540):
    return [(day, start + i, p, p + 0.1, p - 0.1, p, 10) for i, p in enumerate(prices)]


# 1 다음 분 시가에 체결 · 편도 비용 · 15:30 종가 정리
rows = bars("20260105", [100.0] * 391)
want = [None] * len(rows)
want[10] = 1                                     # 550분 판단 → 551분 시가 100 삼
rows = [r if r[1] != 700 else (r[0], r[1], 101.0, 101.1, 100.9, 101.0, 10) for r in rows]
days, tr = K.simulate(rows, want)
chk("1 다음 분 시가 체결 · 15:30 종가 정리 · 비용 두 번", abs(days["20260105"] - (0.0 - 2 * K.COST)) < 1e-9 and tr[-1][1] == K.FLAT_AT)
# 2 하루 −12p 멈춤 주문: 그 분 안에서 닿으면 그 값 · 뒤엔 다시 안 들기
p = [100.0] * 30 + [95.0, 85.0] + [80.0] * 359
rows = bars("20260106", p)
want = [None] * len(rows); want[5] = 1; want[40] = 1
days, tr = K.simulate(rows, want)
# 멈춤 값 = 100 − 12 + 0.04 + 0.04 = 88.08 · 571분 시가 85가 이미 넘음 → 시가 85에 정리 → −0.04 − 15 − 0.04 = −15.08(갭은 한도를 넘을 수 있음)
chk("2 하루 −12p 멈춤(시가가 넘으면 시가 · 다시 안 듦)", abs(days["20260106"] - (-15.08)) < 1e-9)
rows = bars("20260113", [100.0] * 391)
rows = [r if r[1] != 600 else (r[0], r[1], 99.0, 99.1, 87.0, 90.0, 10) for r in rows]
want = [None] * len(rows); want[5] = 1
days, tr = K.simulate(rows, want)
chk("2c 분 안에서 닿으면 멈춤 값 88.08에 정리 → 정확히 −12p", abs(days["20260113"] - (-12.0)) < 1e-9)
chk("2b 멈춘 날 거래 1번", len(tr) == 1)
# 3 L0 / S0
rows = bars("20260107", [100.0] * 391)
want = [None] * len(rows); want[5] = 1; want[20] = "S0"; want[30] = "L0"
days, tr = K.simulate(rows, want)
chk("3 S0는 산 것을 안 건드리고 L0가 정리", len(tr) == 1 and tr[0][1] == 570)
# 4 15:00 판단 뒤 새로 안 듦 · 뒤집기 신호는 정리만
rows = bars("20260108", [100.0] * 391)
want = [None] * len(rows); want[5] = 1; want[365] = -1
days, tr = K.simulate(rows, want)
chk("4 15:05 뒤집기 신호 → 정리만(새로 팔지 않음)", len(tr) == 1 and tr[0][2] == 1 and tr[0][1] == 905)
# 5 날이 바뀌면 처음부터
rows = bars("20260109", [100.0] * 391) + bars("20260112", [100.0] * 391)
want = [None] * len(rows); want[5] = 1
days, tr = K.simulate(rows, want)
chk("5 다음 날로 안 넘김", days["20260112"] == 0.0 and len(tr) == 1)
# 6 RNA 앞만: 앞부분으로 셈한 값 = 전체로 셈한 값의 앞부분
x = list(100 + np.cumsum(np.sin(np.arange(3000) / 7.0)))
a, b = K.rna(x[:2000], (5, 20, 60, 120)), K.rna(x, (5, 20, 60, 120))
same = all(np.allclose(a[k], b[k][:2000], equal_nan=True) for k in a)
chk("6 RNA는 그 분까지 값만(앞부분 같음)", same)
# 7 신호도 앞만
rows = [("20260105" if i < 1500 else "20260106", 540 + i % 395, v, v + .1, v - .1, v, 1) for i, v in enumerate(x)]
for cfg in K.grid():
    w1, w2 = K.signals(rows[:2000], cfg), K.signals(rows, cfg)[:2000]
    if w1 != w2:
        chk(f"7 신호 앞만 {K.name(cfg)}", False)
chk("7 신호 18칸 모두 그 분까지 값만", True)
chk("8 격자 18칸 · 이름 겹침 없음", len(K.grid()) == 18 and len({K.name(g) for g in K.grid()}) == 18)
chk("9 잠금 통과", bool(K.verify_inputs()))
bad = json.loads(K.LOCK.read_text()); bad["research/kmf.py"] = "0" * 64
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
    json.dump(bad, fh)
try:
    K.verify_inputs(fh.name); chk("10 잠금 다르면 멈춤", False)
except SystemExit:
    chk("10 잠금 다르면 멈춤", True)
d = {"days": 90, "total_p": 50.0, "per_day_p": 0.5, "trades": 40, "months": {"202601": 1, "202602": 1, "202603": 1, "202604": -1, "202605": -1}}
v = {"days": 60, "total_p": 20.0, "per_day_p": 0.3, "worst_day_p": -12.3, "months": {"202606": 1, "202607": 1, "202608": -1}}
chk("11 고르기 잣대 경계", K.eligible(d) and K.val_pass(d, v) and not K.val_pass(d, dict(v, per_day_p=0.24))
    and not K.val_pass(d, dict(v, worst_day_p=-12.6)) and not K.eligible(dict(d, trades=29)))
# 12 계약: 그날 거래량 합 1등(행 수가 아님 · 같으면 코드 앞)
with tempfile.TemporaryDirectory() as td:
    mini, fut = Path(td) / "m.csv", Path(td) / "f.csv"
    mini.write_text("date,minute,open,high,low,close,volume\n20260831,540,1,1,1,1,1\n")
    lines = ["datetime,code,open,high,low,close,volume"]
    for mm in range(3):
        lines.append(f"2026-09-01 09:0{mm}:00,A0569000,2,2,2,2,1")      # 행 3 · 거래량 3
    lines.append("2026-09-01 09:00:00,A056A000,3,3,3,3,100")            # 행 1 · 거래량 100
    lines += ["2026-09-02 09:00:00,A056B000,4,4,4,4,5", "2026-09-02 09:00:00,A056A000,5,5,5,5,5"]
    fut.write_text("\n".join(lines) + "\n")
    om, of, oc = K.MINI, K.FUT, K.CUT
    K.MINI, K.FUT, K.CUT = mini, fut, ""
    got = K.load()
    K.MINI, K.FUT, K.CUT = om, of, oc
chk("12 계약은 거래량 합 1등 · 같으면 코드 앞", [r[5] for r in got if r[0] == "20260901"] == [3.0] and [r[5] for r in got if r[0] == "20260902"] == [5.0])
# 13 새 지표: 가장 나쁜 달 · 원 환산 · 95% 구간
st13 = K.stats({"20260105": -2.0, "20260106": 4.0, "20260202": -3.0}, [], "20260101", "20260531")
chk("13 가장 나쁜 달 · 원 · 구간", st13["worst_month_p"] == -3.0 and st13["won"]["worst_day"] == -150000 and len(st13["per_day_ci95_p"]) == 2)
# 14 마지막 시험: 동의 파일 없음 · 확인 미통과 칸 · 이미 돌림 → 멈춤
with tempfile.TemporaryDirectory() as td:
    ob, oo, ofo, ov = K.BOX, K.FINAL_OK, K.FINAL_OUT, K.verify_inputs
    K.BOX = Path(td); K.FINAL_OK = K.BOX / "final_ok.json"; K.FINAL_OUT = K.BOX / "evidence/final.json"; K.verify_inputs = lambda *a: {}
    (K.BOX / "evidence").mkdir()
    (K.BOX / "evidence/picks.json").write_text(json.dumps({"TR": {"name": "a", "cfg": {}, "val_pass": False}, "MR": None, "ORB": None}))
    stops = []
    for setup in ("no_ok", "not_passed", "done"):
        if setup == "not_passed":
            K.FINAL_OK.write_text(json.dumps({"gpt_pr": 1, "picks": ["a"]}))
        if setup == "done":
            K.FINAL_OUT.write_text("{}")
        try:
            K.final(); stops.append(False)
        except SystemExit:
            stops.append(True)
    K.BOX, K.FINAL_OK, K.FINAL_OUT, K.verify_inputs = ob, oo, ofo, ov
chk("14 마지막 시험 막기(동의 없음 · 미통과 칸 · 두 번째)", all(stops))
# 15 시험 2 막기: 시험 1 먼저 · 자료 · 잠금 없음 · 해시 다름 · 두 번째
with tempfile.TemporaryDirectory() as td:
    keep = (K.BOX, K.FINAL_OUT, K.FINAL2_OUT, K.TEST2_LOCK, K.TEST2_FILE, K.verify_inputs)
    K.BOX = Path(td); K.FINAL_OUT = K.BOX / "f1.json"; K.FINAL2_OUT = K.BOX / "f2.json"
    K.TEST2_LOCK = K.BOX / "t2lock.json"; K.TEST2_FILE = K.BOX / "t2.csv"; K.verify_inputs = lambda *a: {}
    stops = []
    for setup in ("no_test1", "no_lock", "bad_sha", "done"):
        if setup == "no_lock":
            K.FINAL_OUT.write_text(json.dumps({"results": {}}))
        if setup == "bad_sha":
            K.TEST2_FILE.write_text("date,minute,open,high,low,close,volume\n")
            K.TEST2_LOCK.write_text(json.dumps({"sha256": "0" * 64, "gpt_pr": 1}))
        if setup == "done":
            K.FINAL2_OUT.write_text("{}")
        try:
            K.final2(); stops.append(False)
        except SystemExit:
            stops.append(True)
    K.BOX, K.FINAL_OUT, K.FINAL2_OUT, K.TEST2_LOCK, K.TEST2_FILE, K.verify_inputs = keep
chk("15 시험 2 막기(시험 1 먼저 · 잠금 · 해시 · 두 번째)", all(stops))
# 16 시험 2 자료는 10-13부터만 읽고 날 · 분 순서로 붙음 · 그 앞 날은 버림
with tempfile.TemporaryDirectory() as td:
    mini, fut, t2 = Path(td) / "m.csv", Path(td) / "f.csv", Path(td) / "t2.csv"
    mini.write_text("date,minute,open,high,low,close,volume\n20260831,540,1,1,1,1,1\n")
    fut.write_text("datetime,code,open,high,low,close,volume\n2026-09-01 09:00:00,A0569000,2,2,2,2,1\n2026-10-13 09:00:00,A056A000,9,9,9,9,1\n")
    t2.write_text("date,minute,open,high,low,close,volume\n20261014,540,7,7,7,7,1\n20261012,540,8,8,8,8,1\n20261013,541,6,6,6,6,1\n")
    keep = (K.MINI, K.FUT, K.TEST2_FILE, K.CUT)
    K.MINI, K.FUT, K.TEST2_FILE, K.CUT = mini, fut, t2, ""
    got = [(r[0], r[5]) for r in K.load()]
    K.CUT = "20261013"; cut13 = [(r[0], r[5]) for r in K.load()]
    K.MINI, K.FUT, K.TEST2_FILE, K.CUT = keep
chk("16 시험 2 자료 10-13부터 · 순서 · 키움 큰 파일의 10-13 뒤는 안 씀 · 자르면 안 읽음",
    got == [("20260831", 1.0), ("20260901", 2.0), ("20261013", 6.0), ("20261014", 7.0)] and cut13 == got[:2])
print(f"모두 통과 {ok}개")
