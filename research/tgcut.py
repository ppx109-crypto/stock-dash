"""세 갈래 공통 G3 — '45일 사이 증권사 목표가(가운데 값, 그날까지 나온 것)가 내렸으면 안 삼'(일봉 새 28회차 · 15분봉 3회차 · 1시간봉 83회차와 같은 셈)."""
import bisect
import sys
from datetime import date, timedelta
sys.path.insert(0, "/home/user/stock-dash")
import study

_TG = {}


def _tl(code):
    if code not in _TG:
        g = study.target_timeline(code)
        _TG[code] = ([d for d, _ in g], [x for _, x in g]) if g else None
    return _TG[code]


def _at(code, day, back=0):
    got = _tl(code)
    if not got:
        return None
    days, vals = got
    if back:
        day = (date(int(day[:4]), int(day[4:6]), int(day[6:8])) - timedelta(days=back)).strftime("%Y%m%d")
    k = bisect.bisect_left(days, day)
    if k == 0:
        return None
    return vals[k - 1] if days[k - 1] >= study._months_before(day, 3) else None


def target_cut(code, day, back=45):
    a, z = _at(code, day), _at(code, day, back)
    return bool(a and z and a["목표가"] < z["목표가"])
