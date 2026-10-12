"""KMF-0004 합성 · 성질 시험(손익 셈 없음)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K  # noqa: E402
import kmf4 as K4  # noqa: E402
import numpy as np  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def day(d, prices, start=540):
    return [(d, start + i, p, p + 0.5, p - 0.5, p, 1) for i, p in enumerate(prices)]


raw = day("20260105", list(np.arange(395) * 0.1 + 100))
b = K4.day_start_aligned(raw, 15)
chk("1 15분봉 첫 봉 = 09:00 ~ 09:14(마지막 분 554) · 시가 · 종가 · 고저", b[0][1] == 554 and b[0][2] == raw[0][2] and b[0][5] == raw[14][5]
    and b[0][3] == max(r[3] for r in raw[:15]) and b[0][4] == min(r[4] for r in raw[:15]))
chk("1b 15:29까지만(마지막 봉 마지막 분 929) · 26봉", b[-1][1] == 929 and len(b) == 26)
late = K4.day_start_aligned(day("20260102", [100.0] * 330, start=600), 30)
chk("2 늦게 연 날은 그날 첫 분(10:00)부터 30분씩", late[0][1] == 629 and late[1][1] == 659)
rng = np.random.default_rng(3)
raw3 = []
for k, d in enumerate(("20260105", "20260106", "20260107")):
    raw3 += day(d, list(100 + np.cumsum(rng.normal(0, 0.5, 391))))
fullb = K4.day_start_aligned(raw3, 15)
same = True
for k in rng.integers(20, len(raw3), 50):
    pb = K4.day_start_aligned(raw3[:k], 15)
    if pb[:-1] != fullb[:len(pb) - 1]:
        same = False
chk("3 묶기는 앞만(1분 자료를 어디서 잘라도 다 끝난 봉은 같음)", same)
h_full = K4.h60_slope(fullb, 15)
chk("4 60분 흐름 앞만(앞부분으로 셈 = 전체의 앞부분)", all(np.array_equal(K4.h60_slope(fullb[:k], 15), h_full[:k]) for k in (10, 30, 50, 70)))
# 4b 장 끝 모자란 조각(15:00 ~ 15:29)은 60분 흐름을 바꾸지 않음: 그 조각 값만 크게 바꿔도 다음 날 첫 봉까지 흐름이 같음(GPT #282)
def two_days(last_piece):
    rows = []
    for k, d in enumerate([f"202601{5 + x:02d}" for x in range(12)]):
        p = list(100 + np.arange(390) * 0.01 + k)
        if d == "20260116":
            p[360:] = [last_piece] * 30                    # 그날 15:00 ~ 15:29
        rows += day(d, p)
    return K4.day_start_aligned(rows, 15)
A, Bb = two_days(100.0), two_days(500.0)
ha, hb = K4.h60_slope(A, 15), K4.h60_slope(Bb, 15)
chk("4b 장 끝 30분 조각은 60분 흐름 셈에 안 들어감", np.array_equal(ha, hb) and len(A) == len(Bb))
# 5 역추세금지 · 정배열 성질(실제 개발 자료 · 손익 셈 없음): 산 봉은 기울기 > 0 · 정배열, 판 봉은 기울기 < 0 · 역배열
rows = K._rows_before(K.VAL[0])
good = True
for cfg in K4.grid():
    bb = K4.prep(rows, cfg)
    w = K4.signals(bb, cfg)
    f = K.rna(np.array([r[5] for r in bb]), K4.SPANS, slope_k=4, band=60)
    for i, x in enumerate(w):
        if x == 1 and not (f["slope"][i] > 0 and f["order"][i] == 3):
            good = False
        if x == -1 and not (f["slope"][i] < 0 and f["order"][i] == 0):
            good = False
chk("5 14칸 모두 역추세 들기 0번(사기는 오름 · 정배열 · 팔기는 내림 · 역배열에서만)", good)
chk("6 격자 14칸 · 이름 겹침 없음", len(K4.grid()) == 14 and len({K4.name(c) for c in K4.grid()}) == 14)
chk("7 잠금 통과", bool(K4.verify_inputs()))
print(f"모두 통과 {ok}개")
