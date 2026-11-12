"""정직 캐시(HONEST_CACHE.md 판 2 · 손익 없음): 고정 나무 가격판 하나로 1일봉 후보 캐시를 처음부터 만듦.
- 종목 하나씩 lab.build(horizons=(0,)) · 행은 upto(자르는 날)까지 가격만으로.
- 달 문턱 T[m]: 그달 첫 거래일(정직 표에서 그달 가장 이른 행 날) 앞 행의 변동성 40% 자리(int(k × 0.4)) · k < 1000이면 없음(추세 문 닫힘).
- 시총 순위: 그날 행끼리(caps.known_by × 종가) 내림차순 · 안정 정렬. inside = 순위 ≤ rule.TOP.
- shape · BR: 같은 가격판(upto까지) lanes에서.
- 판 3(SHARES_NEXT.md): shares="next"면 주식수를 접수일 < 날(다음 거래일부터)로 씀 · filings_upto로 공시를 자를 수 있음 · CAPS_ADJ=0만.
모듈로 씀(build_honest · rows_diff_strict · gates · month_edges_asof). 실행은 run_honest.py."""
import bisect
import math
import os
import pickle
import sys
import time

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import numpy as np  # noqa: E402
import caps  # noqa: E402
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
import final_study as F  # noqa: E402

KEEP_FROM = "20160101"      # 이 날부터 행 전체를 남김(SINCE 2017-02-01 앞 여유)
MONTH_FROM = "201601"
MIN_K = 1000
ALLOWED_SKIP = {"ahead", "i"}


def month_edges_asof(vols, months, first_day, q=rule.CALM, min_k=MIN_K):
    """vols: [(날, 변동성)] · first_day[m] = 그달 첫 거래일. T[m] = first_day[m] 앞 행 q 자리 · k < min_k면 None."""
    got = sorted((d, v) for d, v in vols if v is not None and not (isinstance(v, float) and math.isnan(v)))
    days = [d for d, _ in got]
    arr = np.array([v for _, v in got], dtype=float)
    out = {}
    for m in months:
        if m not in first_day:
            continue
        k = bisect.bisect_left(days, first_day[m])
        out[m] = float(np.partition(arr[:k], int(k * q))[int(k * q)]) if k >= min_k else None
    return out


def num_same(x, y, rel=1e-9):
    """수치 같음(GPT #457 4차 ①): 비유한 값을 허용오차 계산 전에 따로 봄.
    NaN과 NaN만 같음 · +inf와 +inf · −inf와 −inf만 같음 · 유한 대 비유한은 다름 · 유한끼리는 상대 1e−9."""
    xf, yf = math.isfinite(x), math.isfinite(y)
    if not xf or not yf:
        if math.isnan(x) or math.isnan(y):
            return math.isnan(x) and math.isnan(y)
        return x == y          # 같은 부호 inf만 참 · 유한 대 inf는 거짓
    return abs(x - y) <= rel * max(1.0, abs(x), abs(y))


def rows_diff_strict(A, B, upto=None):
    """B 규칙: 칸 이름 집합이 다르면(허용 제외 ahead · i) 실패로 셈. 한쪽만 있는 행 · 칸 값 · 타입 다름 · 칸 이름 다름.
    타입 정책: bool을 뺀 int · float는 수치 호환(1 == 1.0)으로 보고 num_same으로 비교 · 그 밖은 타입이 같아야 함."""
    a = {k: v for k, v in A.items() if upto is None or k[1] <= upto}
    b = {k: v for k, v in B.items() if upto is None or k[1] <= upto}
    bad, names, types = {}, 0, 0
    for k in set(a) & set(b):
        ka, kb = set(a[k]) - ALLOWED_SKIP, set(b[k]) - ALLOWED_SKIP
        if ka != kb:
            names += 1
        for col in ka & kb:
            x, y = a[k][col], b[k][col]
            if type(x) is not type(y) and not (isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool)):
                types += 1
                continue
            if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
                same = num_same(float(x), float(y))
            else:
                same = x == y
            if not same:
                bad[col] = bad.get(col, 0) + 1
    res = {"A만": len(set(a) - set(b)), "B만": len(set(b) - set(a)), "칸 다름": bad, "칸 이름 다른 행": names, "타입 다른 칸": types}
    res["같음"] = res["A만"] == res["B만"] == res["칸 이름 다른 행"] == res["타입 다른 칸"] == 0 and not bad
    return res


def make_known(shares="same", filings_upto=None, filings_strict=False):
    """주식수 함수(SHARES_NEXT.md 1절). same = caps.known_by와 같음(접수일 ≤ 날) · next = 접수일 < 날.
    filings_upto: 이 날까지 접수된 공시만 남김(filings_strict면 접수일 < 그날만)."""
    assert shares in ("same", "next")
    memo = {}

    def line(code):
        got = memo.get(code)
        if got is None:
            got = caps.timeline(code)
            if filings_upto is not None:
                got = tuple(x for x in got if (x[0] < filings_upto if filings_strict else x[0] <= filings_upto))
            memo[code] = got
        return got

    def known(code, day):
        found = None
        for when, count in line(code):
            if (when >= day) if shares == "next" else (when > day):
                break
            found = count
        return found
    return known


RANK_FREE = ("시총순위", "시가총액")


def build_honest(prices, upto, tmpdir, log=None, codes=None, shares="same", filings_upto=None, filings_strict=False):
    """upto까지 가격으로 정직 캐시. 돌려줌: dict(inside={(종목, 날): 행} · T · shape · BR · first_day · rank · 실측)."""
    if caps.ADJ:
        raise SystemExit("CAPS_ADJ가 켜져 있음 — 정직 캐시는 원 주식수(CAPS_ADJ=0)만 씀(SHARES_NEXT.md · 멈춤)")
    known = make_known(shares, filings_upto, filings_strict)
    t0 = time.time()
    P = {c: dict(b, rows=[x for x in b["rows"] if x[0] <= upto]) for c, b in prices.items() if codes is None or c in codes}
    P = {c: b for c, b in P.items() if b["rows"]}
    os.makedirs(tmpdir, exist_ok=True)
    vols, sizes, nrow = [], [], {}
    for c in sorted(P):
        rows = lab.build({c: P[c]}, horizons=(0,))
        keep = []
        for r in rows:
            r.pop("ahead", None)
            v = r.get("변동성")
            vols.append((r["date"], v))
            if r["date"] >= KEEP_FROM:
                keep.append(r)
                cnt = known(r["code"], r["date"])
                if cnt is not None and r.get("price"):
                    sizes.append((r["date"], c, cnt * r["price"]))
        nrow[c] = len(rows)
        with open(os.path.join(tmpdir, f"{c}.pkl"), "wb") as fh:
            pickle.dump(keep, fh, protocol=pickle.HIGHEST_PROTOCOL)
    t1 = time.time()
    by_day = {}
    for d, c, s in sizes:          # 종목 순서대로 들어감 → 안정 정렬
        by_day.setdefault(d, []).append((c, s))
    rank = {}
    for d, here in by_day.items():
        here.sort(key=lambda one: -one[1])
        for place, (c, s) in enumerate(here, 1):
            rank[(c, d)] = (place, s)
    inside = {}
    import hashlib
    pop = hashlib.sha256()          # 행 모집단 지문: 순위 · 시총 칸을 뺀 남긴 행 전체(같은 모집단 확인용)
    for c in sorted(P):
        with open(os.path.join(tmpdir, f"{c}.pkl"), "rb") as fh:
            for r in pickle.load(fh):
                pop.update(repr(sorted((k, v) for k, v in r.items() if k not in RANK_FREE)).encode())
                got = rank.get((c, r["date"]))
                if got is not None:
                    r[caps.RANK], r[caps.SIZE] = got
                if caps.inside(r, rule.TOP):
                    inside[(c, r["date"])] = r
    first_day = {}
    for d, _ in vols:
        m = d[:6]
        if d < first_day.get(m, "99999999"):
            first_day[m] = d
    months = sorted(m for m in first_day if m >= MONTH_FROM)
    T = month_edges_asof(vols, months, first_day)
    lanes = lab.lanes(P)
    shape = F.shapes(lanes, {k[0] for k in inside})
    BR = F.breadth_by_day(list(inside.values()), shape)
    t2 = time.time()
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except Exception:
        peak = None
    return {"inside": inside, "T": T, "shape": shape, "BR": BR, "first_day": first_day, "P": P, "rank": rank,
            "실측": {"빌드 초": round(t1 - t0, 1), "나머지 초": round(t2 - t1, 1), "최대 메모리 MB": peak, "전체 행": len(vols),
                   "inside 행": len(inside), "종목": len(P), "순위 붙은 행": len(rank), "행 모집단 지문": pop.hexdigest(),
                   "주식수": shares, "공시 자름": [filings_upto, filings_strict], "CAPS_ADJ": os.getenv("CAPS_ADJ", "0")}, "종목별 행 수": nrow}


def trend_leg_with(T):
    def f(row):
        t = T.get(row["date"][:6])
        if t is None or (row.get("변동성") or 99) > t:
            return False
        return (row.get("추세 기울기") or -99) >= rule.SLOPE and (row.get("60일 전 대비") or -99) >= rule.SIXTY
    return f


def gates(r, trend_leg, shape, BR):
    """한 행의 문 · 거절 이유(holds · aligned · teacher · target_cut · BASE_HOLD · 갈래)."""
    old = (rule.trend_leg, nrl.shape, nrl.BR)
    rule.trend_leg, nrl.shape, nrl.BR = trend_leg, shape, BR
    try:
        g = {"holds": bool(rule.holds(r)), "aligned": bool(nrl.aligned(r)), "teacher": bool(nrl.teacher(r)), "target_cut": bool(nrl.target_cut(r))}
        g["BASE_HOLD"] = bool(nrl.BASE_HOLD(r))
        g["갈래"] = nrl.tier(r) if g["BASE_HOLD"] else None
        return g
    finally:
        rule.trend_leg, nrl.shape, nrl.BR = old


def keyed_diff(a, b, upto=None, key_upto=lambda k, u: k <= u):
    """사전 둘의 키 집합을 양쪽으로 먼저 보고(GPT #457 4차 ②) 값을 비교. 값은 수치면 num_same · None은 None끼리만 같음."""
    ka = {k for k in a if upto is None or key_upto(k, upto)}
    kb = {k for k in b if upto is None or key_upto(k, upto)}
    diff = []
    for k in ka & kb:
        x, y = a[k], b[k]
        if x is None or y is None:
            ok = x is None and y is None
        elif isinstance(x, (int, float)) and isinstance(y, (int, float)):
            ok = num_same(float(x), float(y))
        else:
            ok = x == y
        if not ok:
            diff.append(k)
    return {"A만": sorted(ka - kb)[:20], "B만": sorted(kb - ka)[:20], "A만 수": len(ka - kb), "B만 수": len(kb - ka), "값 다름 수": len(diff), "값 다름 예": sorted(diff)[:10],
            "같음": not (ka - kb) and not (kb - ka) and not diff}


def shape_diff(sa, sb, lens):
    """shape 사전 둘: 종목 집합 양쪽 · 종목마다 길이 lens[종목](자른 판 가격 길이)까지 배열 길이 · 값(NaN끼리 같음)."""
    import numpy as _np
    ca, cb = set(sa), set(sb)
    bad = []
    for c in ca & cb:
        n = lens.get(c)
        for key in ("정배열", "간격", "50>200"):
            x, y = _np.asarray(sa[c][key], dtype=float), _np.asarray(sb[c][key], dtype=float)
            if n is None or len(x) < n or len(y) < n:
                bad.append((c, key, "길이"))
                break
            x, y = x[:n], y[:n]
            same = _np.array_equal(_np.isnan(x), _np.isnan(y)) and _np.array_equal(_np.isinf(x), _np.isinf(y)) and \
                _np.allclose(_np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), _np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0), rtol=1e-9, atol=0) and \
                _np.array_equal(_np.sign(x[_np.isinf(x)]), _np.sign(y[_np.isinf(y)]))
            if not same:
                bad.append((c, key, "값"))
                break
    return {"A만 종목": len(ca - cb), "B만 종목": len(cb - ca), "다른 종목": len(bad), "예": bad[:10], "같음": not (ca - cb) and not (cb - ca) and not bad}
