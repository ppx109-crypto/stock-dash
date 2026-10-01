"""닮은 종목 거르기(1일봉 rule.KIN · lab.unlike)를 1시간봉 · 15분봉 엔진(hlab._one_run)에 실험으로만 끼움.
운영 코드(hlab.py · hourly_a.py)는 건드리지 않고, 이 모듈을 부른 실험 안에서만 hlab._one_run을 바꿔 씀.
닮음 = 사려는 종목(산 날 전 거래일까지 60일)과 들고 있는 종목(그 종목을 산 날 전 거래일까지 60일)의 일봉 수익률 상관.
1일봉 규칙도 들고 있는 줄은 그 줄이 산 날의 창을 씀(lab.kinship). 뒷날 값은 쓰지 않음.
쓰는 법: import kinpatch; kinpatch.set_edge(0.6) — None이면 끔. set_edge(0.6, align=True)는 두 종목 모두 같은 날 창(날짜 맞춤).
주의(2026-10-02 찾음): lab.kinship은 들고 있는 줄의 창을 그 줄이 산 날에 두어, 산 날이 열흘만 달라도 닮음이 0 근처로 떨어짐
(삼성전자 · SK하이닉스 같은 날 0.91 · 열흘 어긋남 0.03) → 1일봉 규칙의 거르기는 사실상 같은 날 함께 사는 것끼리만 걸림.
set_daycap(n): 하루에 새로 사는 종목 수 한도(G10)."""
import bisect
import inspect
import json

import numpy as np

import hlab as H

HOME = "/home/user/stock-dash"
EDGE = [None]
ALIGN = [False]   # 참이면 들고 있는 종목도 '오늘 사려는 날' 창으로(날짜 맞춤)
BACK = 60
_D, _C = {}, {}


def _daily(c):
    if c not in _D:
        try:
            rows = json.load(open(f"{HOME}/price-data/{c[:6]}.json", encoding="utf-8"))["closes"]
            days = [str(d) for d, _ in rows]
            v = np.array([x for _, x in rows], float)
            r = np.zeros(len(v))
            r[1:] = np.where(v[:-1] > 0, v[1:] / np.where(v[:-1] > 0, v[:-1], 1) - 1, 0.0)
            _D[c] = (days, r)
        except (OSError, ValueError, KeyError, TypeError):
            _D[c] = None
    return _D[c]


def _win(c, day):
    d = _daily(c)
    if not d:
        return None
    k = bisect.bisect_left(d[0], day)          # day 앞(전 거래일)까지
    if k < BACK + 1:
        return None
    return d[1][k - BACK:k]


def kin(c, day, hc, hday):
    key = (c, day, hc, hday)
    if key not in _C:
        a, b = _win(c, day), _win(hc, hday)
        if a is None or b is None or a.std() == 0 or b.std() == 0:
            _C[key] = 0.0
        else:
            _C[key] = float(np.corrcoef(a, b)[0, 1])
    return _C[key]


def ok(c, day, held):
    e = EDGE[0]
    if e is None:
        return True
    return all(kin(c, day, hc, hday) < e for hc, hday in held if hc != c)


def set_edge(e, align=False):
    EDGE[0] = e
    ALIGN[0] = align


SKIPPED = [0]


def _hooked(c, T, pos):
    good = ok(c, T[:8], [(q["code"], T[:8] if ALIGN[0] else q["day"]) for q in pos.values()])
    if not good:
        SKIPPED[0] += 1
    return good


DAYCAP = [None]   # 하루(같은 날짜)에 새로 사는 종목 수 한도 · None이면 없음(1일봉 lab.run per_day와 같은 뜻)
_DAY = {}


def set_daycap(n):
    DAYCAP[0] = n


def _day_ok(T):
    return DAYCAP[0] is None or _DAY.get(T[:8], 0) < DAYCAP[0]


def _day_count(T):
    _DAY[T[:8]] = _DAY.get(T[:8], 0) + 1


def _day_reset():
    _DAY.clear()


_src = inspect.getsource(H._one_run)
_mark = '            _audit(asked, ("사기", c), k)\n'
assert _src.count(_mark) == 1
_src = _src.replace(_mark, _mark + '            if not _KIN_OK(c, T, pos) or not _DAY_OK(T):\n                continue\n')
_m2 = '"now": k, "day": T[:8], "code": c, "양보": give}\n            bought_slots[0] += take\n'
assert _src.count(_m2) == 1
_src = _src.replace(_m2, _m2 + '            _DAY_COUNT(T)\n')
_m3 = '    rng = np.random.default_rng(seed)\n'
assert _src.count(_m3) == 1
_src = _src.replace(_m3, _m3 + '    _DAY_RESET()\n')
H.__dict__.update(_KIN_OK=_hooked, _DAY_OK=_day_ok, _DAY_COUNT=_day_count, _DAY_RESET=_day_reset)
exec(compile(_src, H.__file__, "exec"), H.__dict__)
