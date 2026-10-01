"""세 갈래 공통 실험 — 후보 문의 수급 조건(97회차 '스승님 수급': 5거래일 합 외국인 + · 투신 + · 개인 −)을 바꾼 판.
teach(code, day, kind): day까지(그날 포함) 수급 줄로 셈 — 1시간봉 · 15분봉 재료의 '날'(= 전 거래일)과 1일봉의 '전날'에 맞춰 부르는 쪽이 날을 줌."""
import bisect
import sys
sys.path.insert(0, "/home/user/stock-dash")
import final_group as FG

KINDS = {
    "기준(5일 · 외+ 투+ 개−)": (5, "base"),
    "3일": (3, "base"),
    "10일": (10, "base"),
    "개인 조건 뺌(5일 · 외+ 투+)": (5, "no_ind"),
    "투신 대신 기관(5일 · 외+ 기+ 개−)": (5, "inst"),
    "외+투 합 +(5일 · 개−)": (5, "sum"),
}
_ROWS = {}


def _rows(code):
    if code not in _ROWS:
        fl = sorted(FG.flow_rows(code), key=lambda x: x["date"])
        _ROWS[code] = ([x["date"] for x in fl], fl)
    return _ROWS[code]


def teach(code, day, kind, before=False):
    """before=True면 day **전날까지**(1일봉 규칙: 그날 종가에 사며 수급은 전날까지)."""
    n, how = KINDS[kind]
    days, fl = _rows(code)
    k = bisect.bisect_left(days, day) if before else bisect.bisect_right(days, day)
    if k < n:
        return False
    last = fl[k - n:k]
    if any(r.get(c) is None for r in last for c in ("외국인", "투신", "개인", "기관")):
        return False
    s = {c: sum(r[c] for r in last) for c in ("외국인", "투신", "개인", "기관")}
    if how == "base":
        return s["외국인"] > 0 and s["투신"] > 0 and s["개인"] < 0
    if how == "no_ind":
        return s["외국인"] > 0 and s["투신"] > 0
    if how == "inst":
        return s["외국인"] > 0 and s["기관"] > 0 and s["개인"] < 0
    if how == "sum":
        return s["외국인"] + s["투신"] > 0 and s["개인"] < 0
    raise ValueError(how)
