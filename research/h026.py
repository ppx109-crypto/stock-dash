"""1시간봉 26회차(확인 줄) — 추세 초입에만 사기(사용자 목표 ① 오르기 전에 미리 산다 · 빠른 회전).
지금은 재료(A그룹 꼴 + 가르침)가 켜져 있는 동안 어느 날이든 삼(들고 있지 않으면). 켜진 지 며칠째인지로 나눔:
- 켜진 첫날만 · 3일 안 · 5일 안 · 10일 안 · 5일 넘은 뒤에만(늦게 산 것)
재료가 켜진 날 수 = 전 거래일까지 재료가 이어진 날 수(오늘 값 안 씀). 사는 때 · 파는 법은 지금 규칙."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

RUN = {}
def run_len(c):
    """봉마다 '재료가 며칠째 켜져 있나'(그 봉의 재료 = 전 거래일 값 → 이어진 날 수)."""
    if c in RUN: return RUN[c]
    b = data[c]; a = ATT[c]
    out = np.zeros(len(b["t"]), int); cnt = 0; last_day = None; last_ok = False
    for k, t in enumerate(b["t"]):
        d = t[:8]
        if d != last_day:
            now_ok = bool(a[k] and ok(a[k]))
            cnt = cnt + 1 if (now_ok and last_ok) else (1 if now_ok else 0)
            last_ok = now_ok; last_day = d
        out[k] = cnt
    RUN[c] = out
    return out
def only(lo, hi):
    def e(c, b):
        m = e_align_or_noon(c, b).copy()
        r = run_len(c)
        m &= (r >= lo) & (r <= hi)
        return m
    return e
print("== 1시간봉 26회차 (추세 초입에만 사기) ==", flush=True)
for tag, lo, hi in (("지금(아무 날)", 0, 10 ** 6), ("켜진 첫날만", 1, 1), ("3일 안", 1, 3), ("5일 안", 1, 5),
                    ("10일 안", 1, 10), ("20일 안", 1, 20), ("6일째부터(늦게)", 6, 10 ** 6)):
    res = H.simulate(data, only(lo, hi), exit_daily, size, rank=rank)
    print(f"  {tag:18s} " + H.line(res), flush=True)
print("끝", flush=True)
