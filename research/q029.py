"""15분봉 28회차 — 1시간봉 · 일봉 연구 옮기기 ③.
Q_PART=1: 불타기(1시간봉 18회차: 들고 있는 매매가 처음 +5%에 닿으면 2칸 더 · 한 종목 최대 4칸) · 추세 초입만(1시간봉 26회차: 후보 문이 열린 지 5거래일 안)
Q_PART=2: 정배열 시간 손절(일봉 새 58회차: 산 뒤 5 · 10거래일째 산 값보다 −3% 아래면 팖)
최종 후보(22회차) 위 · 161종목 · 씨앗 16.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
CTX = W["CTX"]

DAYBARS = 26          # 15분봉 하루 칸 수


def pyramid(c, b, p, k):
    if p.get("더함") or p["칸"] >= 4:
        return 0
    before = b["c"][p["i"]:k].max() if k > p["i"] else -1
    if gain(b, p, k) >= 5 and (before / p["price"] - 1) * 100 < 5:
        return ("add", min(2, 4 - p["칸"]))
    return 0


def pyr_first(c, b, p, k):
    r = exit_rule(c, b, p, k)        # 팔 일이 먼저
    return r if r else pyramid(c, b, p, k)


# 후보 문이 열린 지 며칠째(일봉 날 기준, 그날 재료까지)
OPEN_RUN = {}
for c in CTX:
    run, out = 0, {}
    for d in sorted(CTX[c]):
        x = CTX[c][d]
        run = run + 1 if (door(x) is not None and x["가르침"]) else 0
        out[d] = run
    OPEN_RUN[c] = out


def early_only(n=5):
    def f(c, b):
        m = SGF[c].copy()
        for k in np.flatnonzero(m):
            x = mat(c, b, k)
            if x and (OPEN_RUN[c].get(x["날"]) or 0) > n:
                m[k] = False
        return m
    return f


def time_stop(days, loss=3):
    def f(c, b, p, k):
        if kind_of(c, p) != "정배열":
            return 0
        held = k - p["i"]
        return "all" if held >= days * DAYBARS and held < (days + 1) * DAYBARS and gain(b, p, k) <= -loss else 0
    return first(f)


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 28회차({part}): 1시간봉 · 일봉 연구 옮기기 ③ ({len(data)}종목) ==", flush=True)
if part == "1":
    go("불타기(+5% 처음 닿으면 2칸 더)", ex=pyr_first)
    go("추세 초입만(문 열린 지 5거래일 안)", early_only(5))
    go("추세 초입만(10거래일 안)", early_only(10))
else:
    for d in (5, 10):
        go(f"정배열 {d}거래일째 −3% 아래면 팖", ex=time_stop(d))
print("끝", flush=True)
