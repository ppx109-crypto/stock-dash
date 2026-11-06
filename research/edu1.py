"""EDU-0001 — 교육자료(PlanX 12강) 아이디어 A단계 시험(사전등록 research-exchange/claude-to-gpt/EDU-0001/PREREG.md).

T1 이익의 질(4강) · T3 퀀트 보드 세 칸(3강 접힌 칸) · T2 큰 수주(6 · 9강 공급계약 '매출액 대비 %').
- 자료 판: EDU_ROOT(고정 main 펼침 · 기본 scratchpad/edu_tree) · 공급계약 EDU_CONTRACT(작업 갈래 contract-data).
- 재료는 접수일 < 판단일인 보고서만 · 사서 = 판단 다음 거래일 종가(T2는 t0+1 종가) · 2026-10-01 뒤 자료는 안 읽음.
- EDU_MODE=run(기본) · smoke(재료 개수만 · 수익 안 셈) · cut(2021-06-30 자르기 대조 · 수익 안 셈).
python3 research/edu1.py
"""
import bisect
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
ROOT = Path(os.getenv("EDU_ROOT", str(SP / "edu_tree")))
CONTRACT = Path(os.getenv("EDU_CONTRACT", "/home/user/stock-dash/contract-data"))
OUT = Path(os.getenv("EDU_OUT", "/home/user/stock-dash/research/edu1"))
MODE = os.getenv("EDU_MODE", "run")
DATA_END = "20260930"            # 이 날 뒤 자료는 처음부터 안 읽음
CUT = os.getenv("EDU_CUT", "")   # 자르기 대조용(이 날 뒤 자료 안 읽음)
FIRST, LAST_SIGNAL = "20170201", "20260630"
PERIODS = (("학습", "20170101", "20210101"), ("검증", "20210101", "20230101"), ("시험", "20230101", "20991231"))
KIND = {"1분기": 1, "반기": 2, "3분기": 3, "사업": 4}
COST = 0.005                     # T2 왕복 비용(고정 · 근사 계약)


def keep(day):
    day = str(day)
    return day <= DATA_END and (not CUT or day <= CUT)


def num(x):
    if x is None:
        return None
    try:
        v = float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def growth(a, b):
    """a가 b보다 몇 % 늘었나 · b ≤ 0이면 None(etools와 같음)."""
    if a is None or b is None or b <= 0:
        return None
    return (a - b) / b * 100


def ssum(vals):
    return None if not vals or any(v is None for v in vals) else sum(vals)


# ───────────── 분기 실적(quarter-data) · 4분기 = 사업 − 1 ~ 3분기 ─────────────
FIELDS = (("s", "매출"), ("o", "영업이익"), ("n", "순이익"))


def quarter_book(body):
    """[(접수일, (해, 분기), 값)] 접수일 순. 값: s · o · n(석 달) · s0 · o0 · n0(작년 같은 석 달) · eq(자본) · at(자산)."""
    raw = {}
    for key, v in ((body or {}).get("rows") or {}).items():
        if not v or "-" not in key or not str(v.get("접수번호", ""))[:8].isdigit():
            continue
        day = str(v["접수번호"])[:8]
        if not keep(day):
            continue
        y, kind = key.split("-", 1)
        if kind not in KIND:
            continue
        one = {"날": day, "eq": num(v.get("자본")), "at": num(v.get("자산"))}
        for short, name in FIELDS:
            one[short] = num(v.get(name))
            one[short + "0"] = num(v.get(name + "_작년"))
        raw[(int(y), KIND[kind])] = one
    out = []
    for (y, k), v in raw.items():
        if k == 4:
            parts = [raw.get((y, j)) for j in (1, 2, 3)]
            q4 = dict(v)
            for short, _ in FIELDS:
                for f in (short, short + "0"):
                    vals = [p.get(f) for p in parts] if all(parts) else []
                    q4[f] = (v[f] - sum(vals)) if v[f] is not None and len(vals) == 3 and None not in vals else None
            v = q4
        out.append((v["날"], (y, k), v))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def known(book, day):
    """접수일 < day 인 보고서만 {(해, 분기): 값} · 가장 늦은 (해, 분기)."""
    days = [d for d, _, _ in book]
    n = bisect.bisect_left(days, day)
    if not n:
        return None, None
    seen = {}
    for _, q, v in book[:n]:
        seen[q] = v
    return seen, max(seen)


def ttm(seen, last, f):
    y, k = last
    q4 = [(y if j <= k else y - 1, j) for j in range(1, 5)]
    return ssum([seen.get(q, {}).get(f) for q in q4])


def fund_feats(book, day, mcap):
    """T3 재료(그날 앞 접수만)."""
    seen, last = known(book, day)
    if not seen:
        return {}
    s, s0, o, o0, n = (ttm(seen, last, f) for f in ("s", "s0", "o", "o0", "n"))
    eq = seen[last].get("eq")
    f = {"g_s": growth(s, s0), "g_o": growth(o, o0)}
    f["margin"] = o / s if o is not None and s is not None and s > 0 else None
    f["roe"] = n / eq if n is not None and eq is not None and eq > 0 else None
    f["ey"] = o / mcap if o is not None and mcap is not None and mcap > 0 else None
    return f


# ───────────── 현금흐름(cash-data) · e004와 같은 식 ─────────────
def cash_book(body):
    out = []
    for key, v in ((body or {}).get("rows") or {}).items():
        if not v or "-" not in key or not str(v.get("접수번호", ""))[:8].isdigit():
            continue
        day = str(v["접수번호"])[:8]
        if not keep(day):
            continue
        y, kind = key.split("-", 1)
        if kind in KIND:
            out.append((day, (int(y), KIND[kind]), v))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def cash_feats(book, day):
    seen, last = known(book, day)
    if not seen:
        return {}
    v = seen[last]
    prev = seen.get((last[0] - 1, last[1]))
    g = lambda a, b: (a - b) / abs(b) * 100 if a is not None and b is not None and b != 0 else None
    ni, cfo, op, at = num(v.get("순이익_누적")), num(v.get("영업현금")), num(v.get("영업이익_누적")), num(v.get("자산"))
    f = {}
    f["발생액"] = (ni - cfo) / at * 100 if ni is not None and cfo is not None and at is not None and at > 0 else None
    f["현금전환"] = cfo / op if cfo is not None and op is not None and op > 0 else None
    f["영업현금증가"] = g(cfo, num(v.get("영업현금_작년")))
    sales_g = g(num(v.get("매출_누적")), num(v.get("매출_작년누적")))
    inv_g = g(num(v.get("재고")), num(prev.get("재고"))) if prev else None
    ar_g = g(num(v.get("매출채권")), num(prev.get("매출채권"))) if prev else None
    f["재고-매출"] = inv_g - sales_g if inv_g is not None and sales_g is not None else None
    f["채권-매출"] = ar_g - sales_g if ar_g is not None and sales_g is not None else None
    capex = num(v.get("설비투자"))
    f["설비투자"] = abs(capex) / at * 100 if capex is not None and at is not None and at > 0 else None
    k = last[1]
    f["영업현금/자산"] = cfo * 4 / k / at if cfo is not None and at is not None and at > 0 else None
    return f


# ───────────── 순위 · 무리 · 통계(그날 종목끼리만) ─────────────
def pct_rank(vals, good_high=True):
    """{종목: 값} → {종목: 백분위(0, 1]} · 결측은 빠짐 · 같은 값은 종목 코드 순(고정)."""
    got = [(v if good_high else -v, c) for c, v in vals.items() if v is not None]
    got.sort()
    n = len(got)
    return {c: (i + 1) / n for i, (_, c) in enumerate(got)} if n else {}


def fifths(score):
    """{종목: 점수} → {종목: 1 ~ 5}(5가 가장 높음)."""
    got = sorted((v, c) for c, v in score.items() if v is not None)
    n = len(got)
    return {c: int(5 * i / n) + 1 for i, (_, c) in enumerate(got)}


def nw_t(xs, lag):
    x = np.asarray([v for v in xs if v is not None and math.isfinite(v)], float)
    n = len(x)
    if n < 3:
        return None
    e = x - x.mean()
    var = (e @ e) / n
    for L in range(1, lag + 1):
        if L >= n:
            break
        w = 1 - L / (lag + 1)
        var += 2 * w * (e[L:] @ e[:-L]) / n
    if var <= 0:
        return None
    return float(x.mean() / math.sqrt(var / n))


def cluster_t(groups):
    """묶음마다 평균 → 묶음 사이 t."""
    m = np.asarray([np.mean(v) for v in groups.values() if v], float)
    if len(m) < 3 or m.std(ddof=1) == 0:
        return None
    return float(m.mean() / (m.std(ddof=1) / math.sqrt(len(m))))


# ───────────── 자료 읽기 ─────────────
def load_closes():
    import pandas as pd
    close = {}
    for p in sorted((ROOT / "price-data").glob("*.json")):
        if not p.stem.isdigit():
            continue
        b = json.loads(p.read_text(encoding="utf-8"))
        rows = {str(d): float(x) for d, x in (b.get("closes") or []) if x and keep(d)}
        if rows:
            close[p.stem] = rows
    C = pd.DataFrame(close).sort_index()
    return C[C.index >= "20160101"]


def universe(C, top):
    sys.path[:0] = [str(ROOT), str(ROOT / "research")]
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        import caps
        caps.ADJ = True
        import z001
        z001.TOP = top
        inside, size = z001.universe(C)
    finally:
        os.chdir(cwd)
    return inside, size


def books():
    qb, cb = {}, {}
    for p in sorted((ROOT / "quarter-data").glob("*.json")):
        qb[p.stem] = quarter_book(json.loads(p.read_text(encoding="utf-8")))
    for p in sorted((ROOT / "cash-data").glob("*.json")):
        cb[p.stem] = cash_book(json.loads(p.read_text(encoding="utf-8")))
    return qb, cb


def month_firsts(days):
    out, seen = [], set()
    for d in days:
        if FIRST <= d <= LAST_SIGNAL and d[:6] not in seen:
            seen.add(d[:6])
            out.append(d)
    return out


T1_KEYS = (("발생액", False), ("현금전환", True), ("영업현금증가", True), ("재고-매출", False), ("채권-매출", False), ("설비투자", False))


def day_scores(day, codes, qb, cb, size_row):
    """그날 대상 종목의 T1 · T3 점수와 재료 순위(그날 종목끼리만)."""
    cf = {c: cash_feats(cb.get(c, []), day) for c in codes}
    ff = {c: fund_feats(qb.get(c, []), day, size_row.get(c)) for c in codes}
    for c in codes:
        ff[c]["ocf_a"] = cf[c].get("영업현금/자산")
    r1 = {k: pct_rank({c: cf[c].get(k) for c in codes}, hi) for k, hi in T1_KEYS}
    t1 = {}
    for c in codes:
        got = [r1[k][c] for k, _ in T1_KEYS if c in r1[k]]
        if len(got) >= 4:
            t1[c] = float(np.mean(got))
    r3 = {k: pct_rank({c: ff[c].get(k) for c in codes}) for k in ("g_s", "g_o", "margin", "roe", "ocf_a", "ey")}
    parts = {"성장성": ("g_s", "g_o"), "수익성": ("margin", "roe", "ocf_a"), "가치": ("ey",)}
    t3, t3p = {}, {p: {} for p in parts}
    for c in codes:
        got = {}
        for p, ks in parts.items():
            vs = [r3[k][c] for k in ks if c in r3[k]]
            if vs:
                got[p] = float(np.mean(vs))
                t3p[p][c] = got[p]
        if len(got) == 3:
            t3[c] = float(np.mean(list(got.values())))
    return {"T1": t1, "T3": t3, "T1재료": {k: r1[k] for k, _ in T1_KEYS}, "T3칸": t3p}


def period_of(day):
    for name, a, b in PERIODS:
        if a <= day < b:
            return name
    return None


# ───────────── T1 · T3 ─────────────
def cross(C, inside100, size, qb, cb, smoke=False):
    days = list(C.index)
    idx = {d: i for i, d in enumerate(days)}
    arr = C.to_numpy(float)
    cols = list(C.columns)
    ci = {c: j for j, c in enumerate(cols)}
    sig = month_firsts(days)
    if smoke:
        sig = sig[:2] + sig[-2:]
    rows = []
    for d in sig:
        codes = [c for c in cols if bool(inside100.at[d, c])]
        size_row = {c: float(size.at[d, c]) for c in codes if size.at[d, c] == size.at[d, c]}
        sc = day_scores(d, codes, qb, cb, size_row)
        one = {"날": d, "대상": len(codes), "T1 점수": len(sc["T1"]), "T3 점수": len(sc["T3"])}
        if smoke:
            rows.append(one)
            continue
        i = idx[d]
        fw = {}
        for h in (20, 60):
            if i + 1 + h >= len(days) or days[i + 1 + h] > DATA_END:
                continue
            got = {}
            for c in codes:
                a, b = arr[i + 1, ci[c]], arr[i + 1 + h, ci[c]]
                if a == a and b == b and a > 0:
                    got[c] = b / a - 1
            if len(got) < 40:
                continue
            m = float(np.mean(list(got.values())))
            fw[h] = {c: v - m for c, v in got.items()}
        for name in ("T1", "T3"):
            q = fifths(sc[name])
            if len(q) < 40:
                continue
            for h, ex in fw.items():
                g = {j: [ex[c] for c, k in q.items() if k == j and c in ex] for j in range(1, 6)}
                if any(len(v) == 0 for v in g.values()):
                    continue
                gm = {j: float(np.mean(v)) for j, v in g.items()}
                one[f"{name}_h{h}"] = {"무리": gm, "Q5-Q1": gm[5] - gm[1], "Q1-전체": gm[1], "Q5-전체": gm[5]}
        for label, ranks in list(sc["T1재료"].items()) + list(sc["T3칸"].items()):
            q = fifths(ranks)
            if 60 not in fw or len(q) < 40:
                continue
            ex = fw[60]
            g1 = [ex[c] for c, k in q.items() if k == 1 and c in ex]
            g5 = [ex[c] for c, k in q.items() if k == 5 and c in ex]
            if g1 and g5:
                one.setdefault("진단_h60", {})[label] = float(np.mean(g5) - np.mean(g1))
        rows.append(one)
    return rows


def judge_cross(rows, name):
    out = {}
    for h, lag in ((60, 2), (20, 0)):
        key = f"{name}_h{h}"
        per = {}
        for p, a, b in PERIODS:
            rs = [r[key] for r in rows if key in r and a <= r["날"] < b]
            per[p] = {"달": len(rs), "Q5-Q1": float(np.mean([x["Q5-Q1"] for x in rs])) if rs else None,
                      "Q1-전체": float(np.mean([x["Q1-전체"] for x in rs])) if rs else None,
                      "Q5-전체": float(np.mean([x["Q5-전체"] for x in rs])) if rs else None,
                      "NW t(Q5-Q1)": nw_t([x["Q5-Q1"] for x in rs], lag)}
        allr = [r[key] for r in rows if key in r]
        per["전체"] = {"달": len(allr), "Q5-Q1": float(np.mean([x["Q5-Q1"] for x in allr])) if allr else None,
                     "Q1-전체": float(np.mean([x["Q1-전체"] for x in allr])) if allr else None,
                     "Q5-전체": float(np.mean([x["Q5-전체"] for x in allr])) if allr else None,
                     "NW t(Q5-Q1)": nw_t([x["Q5-Q1"] for x in allr], lag)}
        out[f"h{h}"] = per
    p60 = out["h60"]
    neg = lambda v: v is not None and v < 0
    pos = lambda v: v is not None and v > 0
    gate = {
        "(a) Q1-전체 < 0 세 기간": all(neg(p60[p]["Q1-전체"]) for p, _, _ in PERIODS),
        "(b) Q5-Q1 > 0 세 기간": all(pos(p60[p]["Q5-Q1"]) for p, _, _ in PERIODS),
        "(c) 전체 NW t ≥ 2.0": p60["전체"]["NW t(Q5-Q1)"] is not None and p60["전체"]["NW t(Q5-Q1)"] >= 2.0,
        "(d) 전체 Q5-Q1 ≥ +1.0%p": p60["전체"]["Q5-Q1"] is not None and p60["전체"]["Q5-Q1"] >= 0.01,
    }
    out["통과"] = gate
    out["판정"] = "A 통과" if all(gate.values()) else "나아짐 없음(닫음)"
    diag = {}
    for r in rows:
        for k, v in (r.get("진단_h60") or {}).items():
            diag.setdefault(k, {}).setdefault(period_of(r["날"]), []).append(v)
    if name == "T1":
        keys = [k for k, _ in T1_KEYS]
    else:
        keys = ["성장성", "수익성", "가치"]
    out["진단(재료 · 칸 Q5-Q1 h60 · 고르지 않음)"] = {k: {p: float(np.mean(v)) for p, v in diag.get(k, {}).items()} for k in keys}
    return out


# ───────────── T2 큰 수주 ─────────────
def contract_events(folder):
    """[(종목, 접수일, 매출액대비%)] · 원본 · 제목에 공급계약 · 해지 · 정정 뺌."""
    out = []
    for p in sorted(Path(folder).glob("*.json")):
        if p.stem.startswith("_") or not p.stem.isdigit():
            continue
        b = json.loads(p.read_text(encoding="utf-8"))
        for r in b.get("filings") or []:
            day = str(r.get("rcept_dt") or "")
            nm = str(r.get("report_nm") or "")
            if not day.isdigit() or not keep(day) or r.get("kind") != "원본":
                continue
            if "공급계약" not in nm or "해지" in nm or "정정" in nm:
                continue
            ratio = num((r.get("fields_k2") or {}).get("매출액대비%"))
            if ratio is None:
                continue
            out.append((p.stem, day, ratio))
    out.sort(key=lambda t: (t[1], t[0]))
    return out


GROUPS = (("큰 수주(≥20%)", lambda x: x >= 20), ("공급계약 전체", lambda x: True), ("<10%", lambda x: x < 10),
          ("10~20%", lambda x: 10 <= x < 20), ("≥50%", lambda x: x >= 50))


def events_table(C, inside200, evs, h=20):
    days = list(C.index)
    arr = C.to_numpy(float)
    cols = list(C.columns)
    ci = {c: j for j, c in enumerate(cols)}
    ins = inside200.to_numpy(bool)
    picked = {g: [] for g, _ in GROUPS}
    last_kept = {}
    for code, rday, ratio in evs:
        if code not in ci:
            continue
        i0 = bisect.bisect_left(days, rday)
        if i0 >= len(days) or i0 + 1 + h >= len(days) or days[i0 + 1 + h] > DATA_END:
            continue
        if not ins[i0, ci[code]]:
            continue
        a, b = arr[i0 + 1, ci[code]], arr[i0 + 1 + h, ci[code]]
        if not (a == a and b == b and a > 0):
            continue
        uni = ins[i0]
        ua, ub = arr[i0 + 1, uni], arr[i0 + 1 + h, uni]
        ok = (ua == ua) & (ub == ub) & (ua > 0)
        if ok.sum() < 40:
            continue
        m = float(np.mean(ub[ok] / ua[ok] - 1))
        ex = b / a - 1 - m - COST
        for g, test in GROUPS:
            if not test(ratio):
                continue
            k = (g, code)
            if k in last_kept and i0 - last_kept[k] < 20:
                continue
            last_kept[k] = i0
            picked[g].append({"종목": code, "t0": days[i0], "비율": ratio, "초과(비용 뒤)": ex})
    return picked


def judge_events(picked):
    out = {}
    for g, _ in GROUPS:
        ev = picked[g]
        per = {}
        for p, a, b in PERIODS + (("전체", "0", "9"),):
            sel = [e for e in ev if a <= e["t0"] < b]
            xs = [e["초과(비용 뒤)"] for e in sel]
            if not xs:
                per[p] = {"사건": 0}
                continue
            by_m, by_s = {}, {}
            for e in sel:
                by_m.setdefault(e["t0"][:6], []).append(e["초과(비용 뒤)"])
                by_s.setdefault(e["종목"], []).append(e["초과(비용 뒤)"])
            tm, ts = cluster_t(by_m), cluster_t(by_s)
            tot = sum(xs)
            share = max(sum(v) for v in by_s.values()) / tot if tot > 0 else None
            per[p] = {"사건": len(xs), "종목": len(by_s), "평균": float(np.mean(xs)), "가운데": float(np.median(xs)),
                      "이긴 몫": float(np.mean(np.array(xs) > 0)), "달 t": tm, "종목 t": ts,
                      "작은 t": min(t for t in (tm, ts) if t is not None) if (tm is not None or ts is not None) else None,
                      "한 종목 몫": share}
        out[g] = per
    big, allc = out["큰 수주(≥20%)"], out["공급계약 전체"]
    pos = lambda v: v is not None and v > 0
    gate = {
        "(a) 비용 뒤 평균 > 0 세 기간": all(pos(big[p].get("평균")) for p, _, _ in PERIODS),
        "(b) 전체 작은 t ≥ 2.0": big["전체"].get("작은 t") is not None and big["전체"]["작은 t"] >= 2.0,
        "(c) 기간마다 사건 ≥ 30": all(big[p].get("사건", 0) >= 30 for p, _, _ in PERIODS),
        "(d) 한 종목 몫 < 25%": big["전체"].get("한 종목 몫") is not None and big["전체"]["한 종목 몫"] < 0.25,
        "(e) 큰 수주 > 공급계약 전체 세 기간": all(big[p].get("평균") is not None and allc[p].get("평균") is not None
                                          and big[p]["평균"] > allc[p]["평균"] for p, _, _ in PERIODS),
    }
    return {"무리": out, "통과": gate, "판정": "A 통과" if all(gate.values()) else "나아짐 없음(닫음)"}


# ───────────── 실행 ─────────────
def build():
    C = load_closes()
    inside100, size = universe(C, 100)
    inside200, _ = universe(C, 200)
    qb, cb = books()
    return C, inside100, inside200, size, qb, cb


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    C, inside100, inside200, size, qb, cb = build()
    if MODE == "smoke":
        rows = cross(C, inside100, size, qb, cb, smoke=True)
        evs = contract_events(CONTRACT)
        print("smoke 재료 개수:", json.dumps(rows, ensure_ascii=False))
        print("smoke 공급계약 사건(원본 · % 있음):", len(evs), "· 첫", evs[:1], "· 끝 날", evs[-1][1] if evs else None)
        return
    rows = cross(C, inside100, size, qb, cb)
    evs = contract_events(CONTRACT)
    picked = events_table(C, inside200, evs)
    res = {"과제": "EDU-0001 A단계", "자료 끝": DATA_END, "판단 달": len(rows),
           "T1 이익의 질": judge_cross(rows, "T1"), "T3 퀀트 보드": judge_cross(rows, "T3"), "T2 큰 수주": judge_events(picked)}
    (OUT / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "rows.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    (OUT / "events.json").write_text(json.dumps(picked, ensure_ascii=False), encoding="utf-8")
    for k in ("T1 이익의 질", "T3 퀀트 보드", "T2 큰 수주"):
        print(k, res[k]["판정"], json.dumps(res[k]["통과"], ensure_ascii=False))


def cut_check(cut="20210630"):
    """자르기 대조: cut 뒤 자료를 처음부터 안 읽은 판과 다 읽은 판의 재료 · 무리가 cut까지 같은지(수익 안 셈)."""
    global CUT
    full = build()
    ea = [e for e in contract_events(CONTRACT) if e[1] <= cut]   # 다 읽은 판(자르기 전)에서 cut까지
    CUT = cut
    part = build()
    C, i100, _, size, qb, cb = full
    Cp, i100p, _, sizep, qbp, cbp = part
    bad, n = 0, 0
    for d in month_firsts(list(Cp.index)):
        if d > cut:
            continue
        codes = [c for c in C.columns if bool(i100.at[d, c])]
        codesp = [c for c in Cp.columns if bool(i100p.at[d, c])]
        sa = day_scores(d, codes, qb, cb, {c: float(size.at[d, c]) for c in codes if size.at[d, c] == size.at[d, c]})
        sb = day_scores(d, codesp, qbp, cbp, {c: float(sizep.at[d, c]) for c in codesp if sizep.at[d, c] == sizep.at[d, c]})
        n += 1
        if codes != codesp or fifths(sa["T1"]) != fifths(sb["T1"]) or fifths(sa["T3"]) != fifths(sb["T3"]):
            bad += 1
    eb = contract_events(CONTRACT)                               # 처음부터 cut 뒤를 안 읽은 판
    print(f"자르기 {cut}: 판단 달 {n} · 다른 달 {bad} · 사건 같음 {ea == eb}")
    if bad or ea != eb:
        sys.exit(1)
    print("자르기 PASS")


if __name__ == "__main__":
    if MODE == "cut":
        cut_check()
    else:
        main()
