"""일봉 새 69회차 — 장이 무너질 때 정배열 매매를 먼저 정리(파는 쪽의 시장 신호, 사는 쪽 시장 판단(42 · 52 · 53)과 다름).

그날 종가로 판단 · 그날 종가에 팜(규칙의 다른 팔기와 같음). 시장 폭(100위 안 50일선 > 200일선 몫)은 그날 종가까지로 만듦(dguard 6겹),
코스피 지수는 한투 지수 일봉(그날 종가). 바뀐 매매의 손익을 직접 봄.
실행: NRL_CACHE=... python3 research/n069.py
"""
import bisect
import json
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import lab
import ntools as T
import nrl

T_DAYS = sorted(nrl.BR)
rows = json.load(open("/home/user/stock-dash/market-data/index_KOSPI.json", encoding="utf-8"))["rows"]
KD = [r["date"] for r in rows]
KC = [r["종가"] for r in rows]


def kospi_ret(day, n):
    k = bisect.bisect_right(KD, day) - 1
    return KC[k] / KC[k - n] - 1 if k >= n else None


def broken_plus(extra):
    def go(lane, start, price, step, peak, row=None):
        if nrl.broken(lane, start, price, step, peak, row):
            return True
        return extra(lane["날"][start + step], (lane["closes"][start + step] / price - 1) * 100)
    return go


def exits(extra):
    return lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": broken_plus(extra)})


print("== 일봉 새 69회차: 장이 무너질 때 정배열 먼저 정리 ==", flush=True)
base = T.once("지금 규칙(기준)")
for lv in (40, 35, 30):
    got = T.once(f"시장 폭 {lv}% 아래로 떨어지면 정배열 팜", exit_at=exits(lambda d, g, lv=lv: nrl.BR.get(d, 100) < lv))
    T.diff_check(base, got)
for drop in (10, 15):
    got = T.once(f"시장 폭 20일 새 {drop}%p 넘게 줄면 팜", exit_at=exits(
        lambda d, g, drop=drop: (lambda k: k >= 20 and nrl.BR.get(T_DAYS[k], 0) - nrl.BR.get(T_DAYS[k - 20], 0) <= -drop)(
            bisect.bisect_right(T_DAYS, d) - 1)))
    T.diff_check(base, got)
for n, lv in ((5, -5), (10, -7), (20, -10)):
    got = T.once(f"코스피 {n}일 {lv}% 아래면 정배열 팜", exit_at=exits(lambda d, g, n=n, lv=lv: (kospi_ret(d, n) or 0) * 100 <= lv))
    T.diff_check(base, got)
got = T.once("코스피 10일 −7% 아래이고 손실 중일 때만", exit_at=exits(lambda d, g: (kospi_ret(d, 10) or 0) * 100 <= -7 and g < 0))
T.diff_check(base, got)
print("끝", flush=True)
