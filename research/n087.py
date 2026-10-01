"""일봉 새 87회차(세 갈래 공통 G1 · G2 · 1일봉) — 정배열 문 숫자: 간격 범위(19 ~ 53%) · 시장 폭 문턱(50%). 기준 = 새 82회차 · 씨앗 8 · 두 반.
Q_PART=1: 간격 15 ~ 53 · 19 ~ 45 · 19 ~ 60 · 25 ~ 53 / Q_PART=2: 시장 폭 45 · 55 · 60%."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule


def aligned2(r, lo=19, hi=53, bmin=50):
    f = nrl.F.form_of(nrl.shape, r)
    return bool(f.get("정배열") and f.get("간격") is not None and lo <= f["간격"] < hi and nrl.BR.get(r["date"], 0) >= bmin)


def hold(**kw):
    return lambda r: (rule.holds(r) or aligned2(r, **kw)) and nrl.teacher(r) and not nrl.target_cut(r)


part = os.environ.get("Q_PART", "1")
print(f"== 일봉 새 87회차({part}): 정배열 문 숫자 ==", flush=True)
T.once("기준(간격 19 ~ 53 · 폭 50)", holds=hold())
if part == "1":
    for lo, hi in ((15, 53), (19, 45), (19, 60), (25, 53)):
        T.once(f"간격 {lo} ~ {hi}", holds=hold(lo=lo, hi=hi))
else:
    for b in (45, 55, 60):
        T.once(f"시장 폭 {b}%", holds=hold(bmin=b))
print("끝", flush=True)
