"""E(실적 다시 보기) 도구 — DART 분기 실적(quarter-data)으로 여러 갈래 비교를 만듭니다.

quarter-data의 1분기 · 반기 · 3분기 값은 **그 석 달치**이고, '_작년'은 작년 같은 석 달입니다(같은 보고서 안이라 기준이 맞음).
사업보고서는 한 해 전체 → 4분기 = 사업 − (1+2+3분기). 날짜는 접수번호 앞 8자리(정정이면 늦은 날) — 신호 날 **앞** 접수만 씀.

비교(매출 s · 영업이익 o):
  q   : 이번 분기 vs 작년 같은 분기
  ytd : 올해 누적(1분기~이번 분기) vs 작년 같은 누적 (4분기면 = 한 해)
  yr  : 가장 최근 한 해(사업보고서) vs 그 앞해
  q2  : 이번 분기 vs 재작년 같은 분기          (작년 보고서의 '_작년')
  ytd2: 올해 누적 vs 재작년 같은 누적
  yr2 : 가장 최근 한 해 vs 재재작년(두 해 전)
  ttm : 최근 네 분기 합 vs 그 앞 네 분기 합
  run : 영업이익이 작년 같은 분기보다 늘어난 분기가 몇 번 이어졌나
"""
import bisect
import json
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
KIND = {"1분기": 1, "반기": 2, "3분기": 3, "사업": 4}


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def series(code):
    """{(해, 분기): {"날": 접수일, "s": 석 달 매출, "s0": 작년 같은 석 달, "o", "o0"}} — 4분기는 빼서 만듦."""
    try:
        body = json.loads((ROOT / "quarter-data" / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    raw = {}
    for key, v in (body.get("rows") or {}).items():
        if not v or "-" not in key or not str(v.get("접수번호", ""))[:8].isdigit():
            continue
        y, kind = key.split("-", 1)
        if kind not in KIND:
            continue
        raw[(int(y), KIND[kind])] = {"날": str(v["접수번호"])[:8], "s": _num(v.get("매출")), "s0": _num(v.get("매출_작년")),
                                     "o": _num(v.get("영업이익")), "o0": _num(v.get("영업이익_작년"))}
    out = {}
    for (y, k), v in raw.items():
        if k < 4:
            out[(y, k)] = v
            continue
        parts = [raw.get((y, j)) for j in (1, 2, 3)]
        q4 = {"날": v["날"], "연s": v["s"], "연s0": v["s0"], "연o": v["o"], "연o0": v["o0"]}
        for f in ("s", "s0", "o", "o0"):
            vals = [p.get(f) for p in parts if p] if all(parts) else []
            q4[f] = (v[f] - sum(vals)) if v[f] is not None and len(vals) == 3 and None not in vals else None
        out[(y, 4)] = q4
    return out


def growth(a, b):
    """a가 b보다 몇 % 늘었나. b가 0 이하면 None(뜻 없음)."""
    if a is None or b is None or b <= 0:
        return None
    return (a - b) / b * 100


def turn(a, b):
    """영업이익 바뀜 갈래: 흑전 · 적전 · 적지 · 늘음 · 줄음."""
    if a is None or b is None:
        return None
    if b <= 0 < a:
        return "흑전"
    if a <= 0 < b:
        return "적전"
    if a <= 0 and b <= 0:
        return "적지"
    return "늘음" if a > b else "줄음"


def _sum(vals):
    return None if not vals or None in vals else sum(vals)


class Book:
    def __init__(self):
        self.cache = {}

    def _get(self, code):
        if code not in self.cache:
            s = series(code)
            keys = sorted(s, key=lambda k: s[k]["날"])
            self.cache[code] = (s, keys, [s[k]["날"] for k in keys])
        return self.cache[code]

    def known(self, code, day):
        """day 앞에 접수된 보고서만 담은 표와 가장 최근 (해, 분기)."""
        s, keys, days = self._get(code)
        n = bisect.bisect_left(days, day)
        if not n:
            return None, None
        seen = {k: s[k] for k in keys[:n]}
        last = max(seen)                          # 해 · 분기로 가장 늦은 것(늦게 낸 앞 분기 정정은 무시)
        return seen, last

    def feats(self, code, day):
        seen, last = self.known(code, day)
        if not seen:
            return None
        y, k = last
        cur = seen[last]
        f = {"해분기": f"{y}Q{k}", "접수": cur["날"]}
        prev = seen.get((y - 1, k))               # 작년 보고서(그 안의 '_작년' = 재작년)
        for x in ("s", "o"):
            f[f"q_{x}"] = growth(cur.get(x), cur.get(x + "0"))
            f[f"q2_{x}"] = growth(cur.get(x), prev.get(x + "0")) if prev else None
            this = [seen.get((y, j), {}).get(x) for j in range(1, k + 1)]
            last_y = [seen.get((y, j), {}).get(x + "0") for j in range(1, k + 1)]
            two_y = [seen.get((y - 1, j), {}).get(x + "0") for j in range(1, k + 1)]
            f[f"ytd_{x}"] = growth(_sum(this), _sum(last_y))
            f[f"ytd2_{x}"] = growth(_sum(this), _sum(two_y))
            # 최근 네 분기 vs 그 앞 네 분기(각 보고서의 '_작년'으로 앞 네 분기를 채움)
            q4 = [(y if j <= k else y - 1, j) for j in range(1, 5)]
            f[f"ttm_{x}"] = growth(_sum([seen.get(q, {}).get(x) for q in q4]), _sum([seen.get(q, {}).get(x + "0") for q in q4]))
        ann = [q for q in seen if q[1] == 4]
        if ann:
            a = seen[max(ann)]
            b = seen.get((max(ann)[0] - 1, 4))
            for x in ("s", "o"):
                f[f"yr_{x}"] = growth(a.get("연" + x), a.get("연" + x + "0"))
                f[f"yr2_{x}"] = growth(a.get("연" + x), b.get("연" + x + "0")) if b else None
            f["yr_turn"] = turn(a.get("연o"), a.get("연o0"))
        f["q_turn"] = turn(cur.get("o"), cur.get("o0"))
        f["ytd_turn"] = turn(_sum([seen.get((y, j), {}).get("o") for j in range(1, k + 1)]),
                             _sum([seen.get((y, j), {}).get("o0") for j in range(1, k + 1)]))
        run, q = 0, last
        while q in seen and seen[q].get("o") is not None and seen[q].get("o0") is not None and seen[q]["o"] > seen[q]["o0"]:
            run += 1
            q = (q[0] - 1, 4) if q[1] == 1 else (q[0], q[1] - 1)
        f["run"] = run
        # 영업이익률 바뀜(이번 분기 vs 작년 같은 분기, %p)
        if cur.get("s") and cur.get("s0") and cur.get("o") is not None and cur.get("o0") is not None:
            f["margin_d"] = cur["o"] / cur["s"] * 100 - cur["o0"] / cur["s0"] * 100
        return f
