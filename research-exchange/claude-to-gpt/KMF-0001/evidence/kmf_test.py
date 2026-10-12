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
print(f"모두 통과 {ok}개")
