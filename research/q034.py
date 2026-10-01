"""15분봉 33회차 — 15분봉에서 아직 안 본 짜임: 계좌 칸 수 · 칸 크기 · 같은 시각 순서를 일봉 규칙처럼 '180일 EMA 닷새 기울기 큰 것 먼저'.
Q_PART=1: 칸 수 8 · 12(칸 크기 그대로) · 정배열 3칸
Q_PART=2: 추세 · 3일 연속 3칸(정배열 2칸) · 순서를 180일선 기울기(전 거래일까지 일봉)로
최종 후보(22회차) 위 · 161종목 · 씨앗 16.
"""
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])


def go4(tag, sz=size, slots=10, rk=None):
    res = M.simulate(data, lambda c, b: SGF[c], exit_rule, sz, rank=rk or RKF, stale_of=stale90, seeds=16, slots=slots)
    print(f"  {tag:36s} " + H.line(res), flush=True)


def size_al3(c, b, k):
    x = mat(c, b, k)
    return 4 if x and (x["추세문"] or x["3일연속"]) else 3


def size_tr3(c, b, k):
    x = mat(c, b, k)
    return 3 if x and (x["추세문"] or x["3일연속"]) else 2


def slope_table(c):
    rows = json.load(open(f"price-data/{c}.json", encoding="utf-8"))["closes"]
    d = [r[0] for r in rows]
    cl = np.array([float(r[1]) for r in rows])
    e = np.full(len(cl), np.nan)
    if len(cl) >= 180:
        a = 2 / 181
        e[179] = cl[:180].mean()
        for i in range(180, len(cl)):
            e[i] = e[i - 1] + a * (cl[i] - e[i - 1])
    sl = np.r_[np.full(5, np.nan), (e[5:] / e[:-5] - 1) * 100]
    return dict(zip(d, sl))


SL = {c: slope_table(c) for c in data}


def rank_slope(c, b, k):
    x = mat(c, b, k)
    v = SL[c].get(x["날"]) if x else None       # 재료 날 = 전 거래일
    return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, -(v if v is not None and not np.isnan(v) else -99))


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 33회차({part}): 칸 수 · 칸 크기 · 순서 ({len(data)}종목) ==", flush=True)
if part == "1":
    go4("칸 수 8", slots=8)
    go4("칸 수 12", slots=12)
    go4("정배열 3칸", sz=size_al3)
else:
    go4("추세 · 3일 연속 3칸", sz=size_tr3)
    go4("순서: 180일선 기울기 큰 것 먼저", rk=rank_slope)
print("끝", flush=True)
