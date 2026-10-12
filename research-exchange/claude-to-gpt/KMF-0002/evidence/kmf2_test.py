"""KMF-0002 합성 시험(성과 셈 없음 · 가짜 분봉)."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K  # noqa: E402
import kmf2 as K2  # noqa: E402
import numpy as np  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def day(d, prices, start=540):
    return [(d, start + i, p, p + 0.1, p - 0.1, p, 10) for i, p in enumerate(prices)]


cfg = {"bot": "ORB1", "or": 30, "max_entries": 1, "stop": "day"}
# 1 범위(첫 30분 고가 100.1)를 넘은 첫 분에 한 번만 삼 · 그 뒤 None(장 끝까지 들고 감)
p = [100.0] * 30 + [100.0] * 10 + [101.0] + [99.0] * 20 + [102.0] * 330
w = K2.signals(day("20260105", p), cfg)
chk("1 범위 위 첫 분 삼 · 한 번만", w[40] == 1 and sum(1 for x in w if x is not None) == 1)
days, tr = K.simulate(day("20260105", p), w)
chk("1b 장 끝(15:30) 종가 정리", len(tr) == 1 and tr[0][1] == K.FLAT_AT)
# 2 range 멈춤: 반대쪽(저가 99.9) 아래로 내려가면 정리 · 하루 1번이면 다시 안 듦
w = K2.signals(day("20260106", p), dict(cfg, stop="range"))
chk("2 range 멈춤 정리 · 다시 안 듦", w[40] == 1 and w[41] == 0 and sum(1 for x in w if x is not None) == 2)
# 3 하루 2번: 정리 뒤 반대 돌파에 다시 듦
p3 = [100.0] * 30 + [101.0] + [99.0] * 5 + [98.0] + [101.5] * 354
w = K2.signals(day("20260107", p3), dict(cfg, stop="range", max_entries=2))
chk("3 두 번째 들기(아래 돌파 팖)", w[30] == 1 and w[31] == 0 and w[32] == -1)
# 4 늦게 연 날(10:00 시작): 범위는 10:00 ~ 10:29
w = K2.signals(day("20260102", [100.0] * 30 + [101.0] * 300, start=600), cfg)
chk("4 늦게 연 날 범위 그날 첫 분부터", w[30] == 1 and all(x is None for x in w[:30]))
# 5 15:00 판단 뒤 새로 안 듦
w = K2.signals(day("20260108", [100.0] * 380 + [101.0] * 11), cfg)
chk("5 15:00 뒤 새 들기 없음", all(x is None for x in w))
# 6 앞만: 앞부분으로 셈한 신호 = 전체 신호의 앞부분(18칸 모두)
rng = np.random.default_rng(1)
rows = []
for k, d in enumerate(("20260105", "20260106", "20260107")):
    rows += day(d, list(100 + np.cumsum(rng.normal(0, 0.5, 391))))
for g in K2.grid():
    a, b = K2.signals(rows[:600], g), K2.signals(rows, g)[:600]
    if a != b:
        chk(f"6 앞만 {K2.name(g)}", False)
chk("6 신호 12칸 모두 그 분까지 값만", True)
chk("7 격자 12칸 · 이름 겹침 없음", len(K2.grid()) == 12 and len({K2.name(g) for g in K2.grid()}) == 12)
chk("8 잠금 통과", bool(K2.verify_inputs()))
# 9 시험 2: 완전한 거래일이 20일 모자라면 셈(simulate) 전에 멈춤 · 반쯤 빈 날은 세지 않음
import tempfile, hashlib  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    keep = (K2.BOX, K2.FINAL_OUT, K2.FINAL2_OUT, K2.TEST2_LOCK, K.TEST2_FILE, K2.verify_inputs, K.simulate, K.load)
    K2.BOX = Path(td); K2.FINAL_OUT = K2.BOX / "f1.json"; K2.FINAL2_OUT = K2.BOX / "f2.json"; K2.TEST2_LOCK = K2.BOX / "l.json"
    K.TEST2_FILE = K2.BOX / "t2.csv"; K.TEST2_FILE.write_text("x"); K2.verify_inputs = lambda *a: {}
    K2.FINAL_OUT.write_text(json.dumps({"cfg": K2.grid()[0], "pass1": True}))
    K2.TEST2_LOCK.write_text(json.dumps({"sha256": hashlib.sha256(b"x").hexdigest(), "gpt_pr": 1}))
    fake = []
    for k in range(25):
        fake += day(f"202610{13 + k:02d}" if 13 + k <= 31 else f"202611{k - 18:02d}", [100.0] * (391 if k < 19 else 200))
    K.load = lambda: fake                                   # 완전한 날 19 + 반쯤 빈 날 6
    touched = []
    K.simulate = lambda *a, **kw: touched.append(1) or ({}, [])
    try:
        K2.final2(); stopped = False
    except SystemExit as e:
        stopped = "19거래일" in str(e)
    K2.BOX, K2.FINAL_OUT, K2.FINAL2_OUT, K2.TEST2_LOCK, K.TEST2_FILE, K2.verify_inputs, K.simulate, K.load = keep
chk("9 시험 2: 완전한 19일 → 셈 전에 멈춤(simulate 안 부름) · 반쯤 빈 날 안 셈", stopped and not touched and K2.full_days(fake) == 19)
chk("10 잠금에 뿌리 경로 없음", "root" not in K2.lock_body())
print(f"모두 통과 {ok}개")
