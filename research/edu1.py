"""EDU-0001 — 교육자료(PlanX 12강) 아이디어 A단계 시험(사전등록 research-exchange/claude-to-gpt/EDU-0001/PREREG.md · 판 2).

T1 이익의 질(4강) · T3 퀀트 보드 세 칸(3강 접힌 칸) · T2 큰 수주(6 · 9강 공급계약 '매출액 대비 %').
판 2(GPT #485 고칠 것 4 + 대리 검토 높음 5 · 중간 · 낮음 반영 · 셈 전):
- 시가총액 = 그날 원주가(loan-data) × 그날 **앞** 접수 주식 수(단위 실수는 앞 줄과만 견줌) · caps 모듈 안 씀(뒤 자료 · 어림 배수 없음).
- 4분기 = 사업 − 1 ~ 3분기는 판단일마다 그날 보이는 판으로만 · 사업보고서 기간이 12월 끝이 아니면 4분기 안 만듦.
- 같은 값은 평균 순위 · T1 ③ = 앞해 같은 보고서의 영업현금 대비 · 누적 비율은 ×4/분기 수로 연환산.
- (a) 기준 = 그날 점수 있는 종목 평균(대상 평균은 진단) · (c) t = Hansen-Hodrick(같은 무게) 지연 2.
- T2: t0 2017-02-01 ~ 2026-06-30만 · 자회사 · 첨부 공시 뺌 · 기준 평균에서 사건 종목 뺌 · 비용 0.25 · 0.5 · 1.0%p(판정 1.0) ·
  t = 사건 평균의 CR1 묶음 t(분기 · 종목 중 작은 것) · 한 종목 몫 = 절댓값 기준.
- EDU_MODE=run(기본) · smoke(개수만) · guard(10개 날 × 자르기 · 더럽히기 → 그날까지 모든 칸 대조 + 엿보기 돌연변이가 FAIL로 잡히는지).
python3 research/edu1.py
"""
import bisect
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
ROOT = Path(os.getenv("EDU_ROOT", str(SP / "edu_tree")))
CONTRACT = Path(os.getenv("EDU_CONTRACT", "/home/user/stock-dash/contract-data"))
OUT = Path(os.getenv("EDU_OUT", "/home/user/stock-dash/research/edu1"))
MODE = os.getenv("EDU_MODE", "run")
PIN_MAIN = "70473e52d3691ff14f9adc787f74aa873453e06a"
PIN_CONTRACT_TREE = "112b7fa36f6e2dab5b17490c42772da90bfc72a9"
DATA_END = "20260930"            # 이 날 뒤 자료는 처음부터 안 읽음
CUT = ""                         # 자르기 대조용(이 날 뒤 자료 안 읽음)
POISON = ""                      # 더럽히기 대조용(이 날 뒤 값은 엉터리)
LEAK = os.getenv("EDU_LEAK") == "1"   # 검사 도구 자기 시험 전용: 일부러 45일 엿보기(본 셈에서는 쓰면 안 됨)
CHECK_DAYS = tuple(os.getenv("EDU_CHECK_DAYS", "20181231,20190628,20191230,20200630,20201230,20210630,20220630,20230630,20240628,20250630").split(","))
FIRST, LAST_SIGNAL = "20170201", "20260630"
PERIODS = (("학습", "20170101", "20210101"), ("검증", "20210101", "20230101"), ("시험", "20230101", "20991231"))
KIND = {"1분기": 1, "반기": 2, "3분기": 3, "사업": 4}
COSTS = (0.0025, 0.005, 0.01)    # T2 왕복 비용 범위(근사 계약) · 판정은 가장 비싼 쪽
GATE_COST = 0.01
H_T2 = 20


def keep(day):
    day = str(day)
    return day <= DATA_END and (not CUT or day <= CUT)


def dirty(day):
    return bool(POISON) and str(day) > POISON


def num(x):
    if x is None:
        return None
    try:
        v = float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def poison_num(day, v):
    return (-v * 7.3 + 11) if dirty(day) and v is not None else v


def peek(day):
    """판단일 기준 '보이는 끝' — 본 셈은 day 그대로(접수일 < day). LEAK이면 45일 뒤까지 엿봄(자기 시험 전용)."""
    if not LEAK:
        return day
    return (datetime.strptime(day, "%Y%m%d") + timedelta(days=45)).strftime("%Y%m%d")


def growth(a, b):
    """a가 b보다 몇 % 늘었나 · b ≤ 0이면 None(etools와 같음)."""
    if a is None or b is None or b <= 0:
        return None
    return (a - b) / b * 100


def ssum(vals):
    return None if not vals or any(v is None for v in vals) else sum(vals)


# ───────────── 분기 실적(quarter-data) ─────────────
# 자료에는 (해, 분기)마다 마지막 판 하나만 · 그 판의 접수일 전에는 그 기간을 '모름'으로 둠(정정한 회사가 그 사이 빠지는 한계).
FIELDS = (("s", "매출"), ("o", "영업이익"), ("n", "순이익"))


def end_month(text):
    t = str(text or "")
    return int(t[5:7]) if len(t) >= 7 and t[5:7].isdigit() else None


def quarter_book(body):
    """[(접수일, (해, 분기), 값)] 접수일 순 · 값: s · o · n(석 달, 사업은 한 해) · s0 · o0 · n0 · eq · at · 월(기간 끝 달)."""
    out = []
    for key, v in ((body or {}).get("rows") or {}).items():
        if not v or "-" not in key or not str(v.get("접수번호", ""))[:8].isdigit():
            continue
        day = str(v["접수번호"])[:8]
        if not keep(day):
            continue
        y, kind = key.split("-", 1)
        if kind not in KIND:
            continue
        one = {"날": day, "eq": poison_num(day, num(v.get("자본"))), "at": poison_num(day, num(v.get("자산"))), "월": end_month(v.get("기간"))}
        for short, name in FIELDS:
            one[short] = poison_num(day, num(v.get(name)))
            one[short + "0"] = poison_num(day, num(v.get(name + "_작년")))
        out.append((day, (int(y), KIND[kind]), one))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def known(book, day):
    """접수일 < day 인 판만 {(해, 분기): 석 달 값} · 4분기는 그날 보이는 1 ~ 3분기로(사업 기간이 12월 끝일 때만) · 가장 늦은 (해, 분기)."""
    days = [d for d, _, _ in book]
    n = bisect.bisect_left(days, peek(day))
    if not n:
        return None, None
    raw = {}
    for _, q, v in book[:n]:
        raw[q] = v
    seen = {}
    for (y, k), v in raw.items():
        if k < 4:
            seen[(y, k)] = v
            continue
        parts = [raw.get((y, j)) for j in (1, 2, 3)]
        q4 = dict(v)
        for short, _ in FIELDS:
            for f in (short, short + "0"):
                ok = v.get("월") == 12 and all(parts) and v[f] is not None and all(p.get(f) is not None for p in parts)
                q4[f] = v[f] - sum(p[f] for p in parts) if ok else None
        seen[(y, 4)] = q4
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


# ───────────── 현금흐름(cash-data) ─────────────
CASH_NUM = ("순이익_누적", "영업현금", "영업이익_누적", "자산", "매출_누적", "매출_작년누적", "재고", "매출채권", "설비투자")


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
            out.append((day, (int(y), KIND[kind]), {k: poison_num(day, num(v.get(k))) for k in CASH_NUM}))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def cash_known(book, day):
    days = [d for d, _, _ in book]
    n = bisect.bisect_left(days, peek(day))
    if not n:
        return None, None
    seen = {}
    for _, q, v in book[:n]:
        seen[q] = v
    return seen, max(seen)


def cash_feats(book, day):
    """가장 최근 보고서(누적) · 앞해 같은 보고서와 견줌 · 누적 비율은 ×4/분기 수로 연환산."""
    seen, last = cash_known(book, day)
    if not seen:
        return {}
    v = seen[last]
    prev = seen.get((last[0] - 1, last[1]))
    ann = 4 / last[1]
    g = lambda a, b: (a - b) / abs(b) * 100 if a is not None and b is not None and b != 0 else None
    ni, cfo, op, at = v["순이익_누적"], v["영업현금"], v["영업이익_누적"], v["자산"]
    f = {}
    f["발생액"] = (ni - cfo) / at * 100 * ann if ni is not None and cfo is not None and at is not None and at > 0 else None
    f["현금전환"] = cfo / op if cfo is not None and op is not None and op > 0 else None
    f["영업현금증가"] = g(cfo, prev["영업현금"]) if prev else None
    sales_g = g(v["매출_누적"], v["매출_작년누적"])
    inv_g = g(v["재고"], prev["재고"]) if prev else None
    ar_g = g(v["매출채권"], prev["매출채권"]) if prev else None
    f["재고-매출"] = inv_g - sales_g if inv_g is not None and sales_g is not None else None
    f["채권-매출"] = ar_g - sales_g if ar_g is not None and sales_g is not None else None
    capex = v["설비투자"]
    f["설비투자"] = abs(capex) / at * 100 * ann if capex is not None and at is not None and at > 0 else None
    f["영업현금/자산"] = cfo * ann / at if cfo is not None and at is not None and at > 0 else None
    return f


# ───────────── 순위 · 무리 · 통계(그날 종목끼리만 · 같은 값은 평균 순위) ─────────────
def mid_ranks(vals, good_high=True):
    """{종목: 값} → {종목: 평균 순위(1 ~ n · 같은 값은 같은 평균)} · 결측 빠짐 · 종목 이름과 무관."""
    got = sorted(((v if good_high else -v), c) for c, v in vals.items() if v is not None)
    out, i, n = {}, 0, len(got)
    while i < n:
        j = i
        while j + 1 < n and got[j + 1][0] == got[i][0]:
            j += 1
        r = (i + 1 + j + 1) / 2
        for k in range(i, j + 1):
            out[got[k][1]] = r
        i = j + 1
    return out


def pct_rank(vals, good_high=True):
    r = mid_ranks(vals, good_high)
    n = len(r)
    return {c: v / n for c, v in r.items()} if n else {}


def fifths(score):
    """{종목: 점수} → {종목: 1 ~ 5}(5가 가장 높음) · 평균 순위로 나눔 → 같은 점수는 같은 무리."""
    r = mid_ranks(score)
    n = len(r)
    return {c: min(5, int(5 * (v - 0.5) / n) + 1) for c, v in r.items()} if n else {}


def hh_t(xs, lag):
    """Hansen-Hodrick t(지연 lag까지 같은 무게) · 분산 ≤ 0이거나 3개 미만이면 None."""
    x = np.asarray([v for v in xs if v is not None and math.isfinite(v)], float)
    n = len(x)
    if n < 3:
        return None
    e = x - x.mean()
    var = (e @ e) / n
    for L in range(1, lag + 1):
        if L < n:
            var += 2 * (e[L:] @ e[:-L]) / n
    if var <= 0:
        return None
    return float(x.mean() / math.sqrt(var / n))


def cr1_t(xs, keys):
    """사건 평균(사건마다 같은 무게)의 한 갈래 묶음 견고 t(CR1: G/(G−1) 보정)."""
    x = np.asarray(xs, float)
    n = len(x)
    groups = {}
    for v, k in zip(x - x.mean(), keys):
        groups[k] = groups.get(k, 0.0) + v
    G = len(groups)
    if n < 3 or G < 3:
        return None
    var = G / (G - 1) * sum(s * s for s in groups.values()) / (n * n)
    if var <= 0:
        return None
    return float(x.mean() / math.sqrt(var))


# ───────────── 자료 읽기(시가총액은 뒤 자료 없이) ─────────────
def pin_check():
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    repo = CONTRACT.parent
    tree = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD:contract-data"], capture_output=True, text=True).stdout.strip()
    clean = subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--", "contract-data"]).returncode == 0
    ok = head == PIN_MAIN and tree == PIN_CONTRACT_TREE and clean
    return {"자료 나무": head, "공급계약 나무": tree, "공급계약 고친 것 없음": clean, "고정과 같음": ok}


def load_closes():
    import pandas as pd
    close = {}
    for p in sorted((ROOT / "price-data").glob("*.json")):
        if not p.stem.isdigit():
            continue
        b = json.loads(p.read_text(encoding="utf-8"))
        rows = {str(d): poison_num(d, float(x)) for d, x in (b.get("closes") or []) if x and keep(d)}
        if rows:
            close[p.stem] = rows
    C = pd.DataFrame(close).sort_index()
    return C[C.index >= "20160101"]


def load_raw_closes():
    """원주가(수정 안 한 종가) — loan-data(caps._raw_closes와 같은 원천)."""
    out = {}
    for p in sorted((ROOT / "loan-data").glob("*.json")):
        b = json.loads(p.read_text(encoding="utf-8"))
        out[p.stem] = {str(r["date"]): (float(r["종가"]) * 7.3 + 11 if dirty(r["date"]) else float(r["종가"]))
                       for r in b.get("rows") or [] if r.get("종가") and keep(r["date"])}
    return out


def shares_line(body):
    """(접수일, 주식 수) 날짜순 · 단위 실수(≈1000배)는 **앞 줄과만** 견줘 고침(뒤 줄 · 전체 가운데값 안 씀)."""
    rows = sorted((str(d), int(c)) for d, c in ((body or {}).get("날") or []) if d and c and keep(d))
    out = []
    for day, count in rows:
        if dirty(day):
            count = count * 7 + 11
        if out:
            x = count / out[-1][1]
            if x >= 300:
                count = count / 1000
            elif x <= 1 / 300:
                count = count * 1000
        out.append((day, count))
    return out


def load_shares():
    out = {}
    for p in sorted((ROOT / "share-data").glob("*.json")):
        out[p.stem] = shares_line(json.loads(p.read_text(encoding="utf-8")))
    return out


def shares_before(line, day):
    """접수일 < day 인 가장 최근 주식 수(접수 다음 거래일부터)."""
    k = bisect.bisect_left([d for d, _ in line], peek(day))
    return line[k - 1][1] if k else None


class Caps:
    """그날 시가총액 = 그날 원주가 × 그날 앞 접수 주식 수 · 순위는 시가총액을 아는 종목끼리."""

    def __init__(self, raw, shares):
        self.raw, self.shares, self.memo = raw, shares, {}

    def size(self, day):
        if day not in self.memo:
            got = {}
            for c, line in self.shares.items():
                px = self.raw.get(c, {}).get(day)
                n = shares_before(line, day)
                if px is not None and n is not None and px > 0:
                    got[c] = px * n
            self.memo[day] = got
        return self.memo[day]

    def top(self, day, k):
        s = self.size(day)
        return set(sorted(s, key=lambda c: (-s[c], c))[:k])


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
    """그날 대상 종목의 T1 · T3 점수와 재료(그날 종목끼리만)."""
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
    return {"T1": t1, "T3": t3, "T1재료": {k: r1[k] for k, _ in T1_KEYS}, "T3칸": t3p, "현금": cf, "실적": ff}


def period_of(day):
    for name, a, b in PERIODS:
        if a <= day < b:
            return name
    return None


def fwd_raw(C, day, codes, h):
    """day 다음 거래일 종가에 사서 h거래일 뒤 종가 · 끝이 DATA_END 넘으면 None · {종목: 수익}."""
    days = list(C.index)
    i = days.index(day)
    if i + 1 + h >= len(days) or days[i + 1 + h] > DATA_END:
        return None
    a, b = C.iloc[i + 1], C.iloc[i + 1 + h]
    got = {}
    for c in codes:
        x, y = a.get(c), b.get(c)
        if x is not None and y is not None and x == x and y == y and x > 0:
            got[c] = float(y / x - 1)
    return got if len(got) >= 40 else None


def group_stats(q, r, universe_mean):
    """무리마다 평균 − 그날 점수 있는 종목 평균(기준) · 대상 평균 기준은 진단."""
    have = {c: r[c] for c in q if c in r}
    if len(have) < 40:
        return None
    m = float(np.mean(list(have.values())))
    g = {j: [have[c] for c, k in q.items() if k == j and c in have] for j in range(1, 6)}
    if any(len(v) == 0 for v in g.values()):
        return None
    gm = {j: float(np.mean(v)) for j, v in g.items()}
    return {"무리": gm, "Q5-Q1": gm[5] - gm[1], "Q1-기준": gm[1] - m, "Q5-기준": gm[5] - m, "Q1-대상(진단)": gm[1] - universe_mean}


# ───────────── T1 · T3 ─────────────
def cross(C, caps, qb, cb, smoke=False):
    sig = month_firsts(list(C.index))
    if smoke:
        sig = sig[:2] + sig[-2:]
    rows = []
    for d in sig:
        codes = sorted(caps.top(d, 100))
        sc = day_scores(d, codes, qb, cb, caps.size(d))
        one = {"날": d, "대상": len(codes), "T1 점수": len(sc["T1"]), "T3 점수": len(sc["T3"])}
        if smoke:
            rows.append(one)
            continue
        fw = {h: fwd_raw(C, d, codes, h) for h in (20, 60)}
        fw = {h: v for h, v in fw.items() if v is not None}
        for name in ("T1", "T3"):
            q = fifths(sc[name])
            if len(q) < 40:
                continue
            for h, r in fw.items():
                st = group_stats(q, r, float(np.mean(list(r.values()))))
                if st:
                    one[f"{name}_h{h}"] = st
        for label, ranks in list(sc["T1재료"].items()) + list(sc["T3칸"].items()):
            q = fifths(ranks)
            if 60 not in fw or len(q) < 40:
                continue
            st = group_stats(q, fw[60], 0.0)
            if st:
                one.setdefault("진단_h60", {})[label] = st["Q5-Q1"]
        rows.append(one)
    return rows


def judge_cross(rows, name):
    out = {}
    for h, lag in ((60, 2), (20, 0)):
        key = f"{name}_h{h}"
        per = {}
        for p, a, b in PERIODS + (("전체", "0", "9"),):
            rs = [r[key] for r in rows if key in r and a <= r["날"] < b]
            mean = lambda f: float(np.mean([x[f] for x in rs])) if rs else None
            per[p] = {"달": len(rs), "Q5-Q1": mean("Q5-Q1"), "Q1-기준": mean("Q1-기준"), "Q5-기준": mean("Q5-기준"),
                      "Q1-대상(진단)": mean("Q1-대상(진단)"), "HH t(Q5-Q1)": hh_t([x["Q5-Q1"] for x in rs], lag)}
        out[f"h{h}"] = per
    p60 = out["h60"]
    neg = lambda v: v is not None and v < 0
    pos = lambda v: v is not None and v > 0
    gate = {
        "(a) Q1-기준 < 0 세 기간": all(neg(p60[p]["Q1-기준"]) for p, _, _ in PERIODS),
        "(b) Q5-Q1 > 0 세 기간": all(pos(p60[p]["Q5-Q1"]) for p, _, _ in PERIODS),
        "(c) 전체 HH t(지연 2) ≥ 2.0": p60["전체"]["HH t(Q5-Q1)"] is not None and p60["전체"]["HH t(Q5-Q1)"] >= 2.0,
        "(d) 전체 Q5-Q1 ≥ +1.0%p": p60["전체"]["Q5-Q1"] is not None and p60["전체"]["Q5-Q1"] >= 0.01,
    }
    out["통과"] = gate
    out["판정"] = "A 통과" if all(gate.values()) else "나아짐 없음(닫음)"
    diag = {}
    for r in rows:
        for k, v in (r.get("진단_h60") or {}).items():
            diag.setdefault(k, {}).setdefault(period_of(r["날"]), []).append(v)
    keys = [k for k, _ in T1_KEYS] if name == "T1" else ["성장성", "수익성", "가치"]
    out["진단(재료 · 칸 Q5-Q1 h60 · 고르지 않음 · 현금전환 · 가치 단독과 견줌)"] = {
        k: {p: float(np.mean(v)) for p, v in diag.get(k, {}).items()} for k in keys}
    return out


# ───────────── T2 큰 수주 ─────────────
def contract_events(folder):
    """[(종목, 접수일, 매출액대비%, 접수번호)] · 원본 · 제목에 공급계약 · 해지 · 정정 · 자회사 · 첨부 뺌."""
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
            if "공급계약" not in nm or any(w in nm for w in ("해지", "정정", "자회사", "첨부")):
                continue
            ratio = poison_num(day, num((r.get("fields_k2") or {}).get("매출액대비%")))
            if ratio is None:
                continue
            out.append((p.stem, day, ratio, str(r.get("rcept_no") or "")))
    out.sort(key=lambda t: (t[1], t[0], t[3]))
    return out


GROUPS = (("큰 수주(≥20%)", lambda x: x >= 20), ("공급계약 전체", lambda x: True), ("<10%", lambda x: x < 10),
          ("10~20%", lambda x: 10 <= x < 20), ("≥50%", lambda x: x >= 50))


def last_valid(col, lo, hi):
    """col[lo..hi] 안에서 hi부터 거꾸로 첫 값 있는 칸(나감 날 값이 비면 창 안 마지막 값)."""
    for k in range(hi, lo - 1, -1):
        v = col[k]
        if v == v:
            return v
    return None


def events_table(C, member, evs, h=H_T2):
    """member(t0) = 그날 대상 200위. 들어감 = t0+1 종가 · 나감 = t0+1+h 종가(비면 창 안 마지막 값) · 기준 = 대상(사건 종목 뺌) 평균."""
    days = list(C.index)
    arr = C.to_numpy(float)
    col = {c: j for j, c in enumerate(C.columns)}
    picked = {g: [] for g, _ in GROUPS}
    last_kept = {}
    for code, rday, ratio, no in evs:
        if code not in col or rday < days[0]:
            continue
        i0 = bisect.bisect_left(days, rday)
        if i0 >= len(days) or not (FIRST <= days[i0] <= LAST_SIGNAL):
            continue
        if i0 + 1 + h >= len(days) or days[i0 + 1 + h] > DATA_END:
            continue
        uni = member(days[i0])
        if code not in uni:
            continue
        a = arr[i0 + 1, col[code]]
        b = last_valid(arr[:, col[code]], i0 + 2, i0 + 1 + h)
        if not (a == a and a > 0) or b is None:
            continue
        rs = []
        for c in sorted(uni):
            if c == code or c not in col:
                continue
            x = arr[i0 + 1, col[c]]
            y = last_valid(arr[:, col[c]], i0 + 2, i0 + 1 + h)
            if x == x and x > 0 and y is not None:
                rs.append(y / x - 1)
        if len(rs) < 40:
            continue
        m = float(np.mean(rs))
        ex0 = float(b / a - 1 - m)
        for g, test in GROUPS:
            if not test(ratio):
                continue
            k = (g, code)
            if k in last_kept and i0 - last_kept[k] < 20:
                continue
            last_kept[k] = i0
            picked[g].append({"종목": code, "접수번호": no, "접수일": rday, "t0": days[i0], "들어감": days[i0 + 1],
                              "나감": days[i0 + 1 + h], "비율": ratio, "기준 평균": m, "초과(비용 전)": ex0})
    return picked


def qkey(day):
    return f"{day[:4]}Q{(int(day[4:6]) - 1) // 3 + 1}"


def event_stats(sel, cost):
    xs = [e["초과(비용 전)"] - cost for e in sel]
    if not xs:
        return {"사건": 0}
    tq = cr1_t(xs, [qkey(e["t0"]) for e in sel])
    ts = cr1_t(xs, [e["종목"] for e in sel])
    by_s, by_m = {}, {}
    for e, x in zip(sel, xs):
        by_s[e["종목"]] = by_s.get(e["종목"], 0.0) + x
        by_m[e["t0"][:6]] = by_m.get(e["t0"][:6], 0.0) + x
    ab, abm = sum(abs(v) for v in by_s.values()), sum(abs(v) for v in by_m.values())
    return {"사건": len(xs), "종목": len(by_s), "평균": float(np.mean(xs)), "가운데": float(np.median(xs)),
            "이긴 몫": float(np.mean(np.array(xs) > 0)), "분기 t(CR1)": tq, "종목 t(CR1)": ts,
            "작은 t": min(tq, ts) if tq is not None and ts is not None else None,
            "한 종목 몫(절댓값)": max(abs(v) for v in by_s.values()) / ab if ab > 0 else None,
            "한 달 몫(절댓값 · 진단)": max(abs(v) for v in by_m.values()) / abm if abm > 0 else None}


def judge_events(picked):
    out = {}
    for g, _ in GROUPS:
        out[g] = {}
        for cost in COSTS:
            per = {}
            for p, a, b in PERIODS + (("전체", "0", "9"),):
                per[p] = event_stats([e for e in picked[g] if a <= e["t0"] < b], cost)
            out[g][f"비용 {cost * 100:.2f}%p"] = per
    big = out["큰 수주(≥20%)"][f"비용 {GATE_COST * 100:.2f}%p"]
    allc = out["공급계약 전체"][f"비용 {GATE_COST * 100:.2f}%p"]
    pos = lambda v: v is not None and v > 0
    gate = {
        "(a) 비용 1.0%p 뒤 평균 > 0 세 기간": all(pos(big[p].get("평균")) for p, _, _ in PERIODS),
        "(b) 전체 작은 t ≥ 2.0(비용 1.0%p)": big["전체"].get("작은 t") is not None and big["전체"]["작은 t"] >= 2.0,
        "(c) 기간마다 사건 ≥ 30": all(big[p].get("사건", 0) >= 30 for p, _, _ in PERIODS),
        "(d) 한 종목 몫(절댓값) < 25%": big["전체"].get("한 종목 몫(절댓값)") is not None and big["전체"]["한 종목 몫(절댓값)"] < 0.25,
        "(e) 큰 수주 > 공급계약 전체 세 기간": all(big[p].get("평균") is not None and allc[p].get("평균") is not None
                                          and big[p]["평균"] > allc[p]["평균"] for p, _, _ in PERIODS),
    }
    return {"무리": out, "통과": gate, "판정": "A 통과" if all(gate.values()) else "나아짐 없음(닫음)"}


# ───────────── 실행 ─────────────
def build():
    C = load_closes()
    caps = Caps(load_raw_closes(), load_shares())
    qb, cb = books()
    return C, caps, qb, cb


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pins = pin_check()
    if not pins["고정과 같음"] and MODE == "run":
        print("자료 판이 사전등록과 다름 — 멈춤", pins)
        sys.exit(2)
    C, caps, qb, cb = build()
    if MODE == "smoke":
        rows = cross(C, caps, qb, cb, smoke=True)
        evs = contract_events(CONTRACT)
        print("smoke 판:", json.dumps(pins, ensure_ascii=False))
        print("smoke 재료 개수:", json.dumps(rows, ensure_ascii=False))
        print("smoke 공급계약 사건(원본 · % 있음 · 자회사 · 첨부 뺌):", len(evs))
        return
    rows = cross(C, caps, qb, cb)
    evs = contract_events(CONTRACT)
    picked = events_table(C, lambda d: caps.top(d, 200), evs)
    res = {"과제": "EDU-0001 A단계(판 2)", "자료 판": pins, "자료 끝": DATA_END, "판단 달": len(rows),
           "T1 이익의 질": judge_cross(rows, "T1"), "T3 퀀트 보드": judge_cross(rows, "T3"), "T2 큰 수주": judge_events(picked)}
    (OUT / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "rows.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    (OUT / "events.json").write_text(json.dumps(picked, ensure_ascii=False), encoding="utf-8")
    for k in ("T1 이익의 질", "T3 퀀트 보드", "T2 큰 수주"):
        print(k, res[k]["판정"], json.dumps(res[k]["통과"], ensure_ascii=False))


def snapshot(day_list, cut):
    """그날까지 모든 칸: 대상 100 · 200 · 시가총액 · 재료 · 점수 · 무리 · 끝이 cut 안인 앞날 수익 · 사건(나감 ≤ cut)."""
    C, caps, qb, cb = build()
    days = list(C.index)
    snap = {}
    for d in day_list:
        codes = sorted(caps.top(d, 100))
        sc = day_scores(d, codes, qb, cb, caps.size(d))
        i = days.index(d)
        fw = {h: fwd_raw(C, d, codes, h) for h in (20, 60) if i + 1 + h < len(days) and days[i + 1 + h] <= cut}
        snap[d] = json.dumps({"100": codes, "200": sorted(caps.top(d, 200)), "시총": caps.size(d), "현금": sc["현금"], "실적": sc["실적"],
                              "T1": sc["T1"], "T3": sc["T3"], "무리1": fifths(sc["T1"]), "무리3": fifths(sc["T3"]), "앞날": fw},
                             sort_keys=True, ensure_ascii=False, default=str)
    evs = [e for e in contract_events(CONTRACT) if e[1] <= cut]
    pk = events_table(C, lambda d: caps.top(d, 200), evs)
    return snap, json.dumps({g: [e for e in v if e["나감"] <= cut] for g, v in pk.items()}, sort_keys=True, ensure_ascii=False)


def guard_one(kind, cut, full=None):
    """kind = cut(뒤 자료를 처음부터 안 읽음) | poison(뒤 값을 엉터리로) → 그날까지 모든 칸이 다 읽은 판과 바이트 같으면 True."""
    global CUT, POISON
    C, _, _, _ = build()
    day_list = [d for d in month_firsts(list(C.index)) if d <= cut]
    full = full or snapshot(day_list, cut)
    if kind == "cut":
        CUT = cut
    else:
        POISON = cut
    try:
        part = snapshot(day_list, cut)
    finally:
        CUT = POISON = ""
    bad = [d for d in day_list if full[0][d] != part[0][d]]
    same_ev = full[1] == part[1]
    return (not bad and same_ev), {"판단 달": len(day_list), "다른 달": len(bad), "첫 다른 달": bad[:3], "사건 같음": same_ev}, full


def guard():
    report, ok_all = {}, True
    for cut in CHECK_DAYS:
        full = None
        for kind in ("cut", "poison"):
            ok, info, full = guard_one(kind, cut, full)
            report[f"{kind} {cut}"] = {"PASS": ok, **info}
            ok_all &= ok
            print(kind, cut, "PASS" if ok else "FAIL", info, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "guard.json").write_text(json.dumps({"모두 PASS": ok_all, "엿보기 돌연변이": LEAK, **report}, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    if not ok_all:
        sys.exit(1)


if __name__ == "__main__":
    if MODE == "guard":
        guard()
    else:
        main()
