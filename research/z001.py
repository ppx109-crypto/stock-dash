"""Z1 — 요즘 오르는 종목의 특이점(한투 · DART)과 그것이 과거에도 통했나(사용자 2026-10-07
"요즘 수익이 나는 것들은 어떤 것이며 어떠한 한투자료와 다트자료의 특이점이 있으며 그런 특이점이 과거에서도 적용되는지
면밀히 미래참조 다각도로 차단하며 검토해줘").

방법(횡단면 재료 연구 · 엔진 규칙이 아님):
- 판단일 t(5거래일마다): 재료는 날짜가 t 이하인 줄만 씀. 수급 · 공매도 · 신용 · 대차 · 프로그램 · 체결 · 의견 · 공시 · 실적은 모두
  장 끝난 뒤(또는 시각 모름) 나올 수 있으므로 'GAP=1': t까지 나온 것을 보고 **t+1 종가에 사서** t+1+H 종가에 판다고 잼.
  (t+1 장중엔 t까지 자료가 다 나와 있음 → 15:15 문제 없음 · 공시가 t+1 아침에 나왔어도 쓰지 않음)
- 대상: 그날의 시가총액(그날까지 접수된 주식수 × 그날 종가 · caps) 200등 안. 잴 값 = 그날 대상 가운데 가운데값을 뺀 초과 수익(시장 오르내림 뺌).
- 잣대: 날마다 순위 상관(IC) · 위 1/5 − 아래 1/5 초과 수익. 기간: 2017~19 · 2020~22 · 2023~25 · 2026(1~9월 · 요즘).
- 골라 시험: 2017~2022에서만 고름(두 반 모두 같은 쪽 · t ≥ 2) → 2023~25 · 2026에서 시험(고를 때 안 봄).
- 미래 참조 막기(다각도):
  ① 자르기 시험(Z_CUT): 모든 자료를 자른 날 뒤를 처음부터 안 읽고 다시 셈 → 자른 날 앞 재료가 한 칸도 달라지면 불합격.
  ② 더럽히기 시험(Z_POISON): 자른 날 뒤 값을 엉터리로 바꿔도 앞 재료가 같아야 함.
  ③ 엿보기 대조: 일부러 하루 미래(t+1 외국인 수급)를 쓴 재료를 같이 셈 → 얼마나 부풀려지는지 보여 줌(진짜 재료는 이것과 달라야).
  ④ 같은 날 공시(t+1)는 안 씀 · 실적은 접수번호 앞 8자리(접수일) 기준 · 의견은 보고서 날 기준.
  ⑤ 순위 · 가운데값은 그날 횡단면만(앞날과 섞지 않음) · 문턱 없음(순위만) · 고르기는 앞 기간만.
- 남는 한계: 대상 500종목은 2026-09 시가총액으로 고른 '살아남은' 종목(상폐 없음) → 성적이 좋게 나오는 쪽. 순위 자체는 그때 값.
python research/z001.py            → 결과 표(scratchpad/z001.json · 화면)
Z_CUT=20220615 python research/z001.py check   → 자르기 · 더럽히기 시험
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
import caps  # noqa: E402

H = int(os.getenv("Z_H", "20"))            # 들고 있는 거래일
GAP = 1                                     # 판단 t → t+1 종가에 삼
STEP = 5                                    # 판단일 간격
TOP = int(os.getenv("Z_TOP", "200"))
START = "20170301"
CUT = os.getenv("Z_CUT", "")
POISON = os.getenv("Z_POISON", "")
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
EVENT_KINDS = ("공급계약", "자사주취득", "자사주처분", "유상증자", "전환사채", "잠정실적", "기업설명회", "대량보유", "임원소유",
               "최대주주지분변동", "조회공시", "무상증자", "주식소각", "시설투자", "배당", "주식매수선택권", "소송")


def _keep(d):
    """자르기: 자른 날 뒤 줄은 처음부터 안 읽음."""
    return not CUT or str(d) <= CUT


def _poison(d, v):
    """더럽히기: 자른 날 뒤 값은 엉터리(부호 뒤집고 크게)."""
    if POISON and str(d) > POISON and isinstance(v, (int, float)) and v == v:
        return -v * 7.3 + 11
    return v


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ───────────────────────── 읽기 ─────────────────────────

def load():
    codes = sorted(p.stem for p in Path("price-data").glob("*.json") if p.stem.isdigit())
    close, name = {}, {}
    for c in codes:
        b = _json(f"price-data/{c}.json") or {}
        rows = {str(d): _poison(d, float(x)) for d, x in (b.get("closes") or []) if x and _keep(d)}
        if rows:                      # '자료가 길게 있는 종목만'은 뒷날을 보고 고르는 셈이라 걸지 않음(자르기 시험)
            close[c], name[c] = rows, b.get("name") or c
    C = pd.DataFrame(close).sort_index()
    C = C[C.index >= "20160101"]
    days = list(C.index)
    codes = list(C.columns)

    def frame(folder, pick):
        out = {}
        for c in codes:
            b = _json(f"{folder}/{c}.json")
            if not b:
                continue
            got = pick(b)
            if got:
                out[c] = {d: _poison(d, v) for d, v in got.items() if _keep(d)}
        return pd.DataFrame(out).reindex(index=days, columns=codes)

    def cols(b, name_):
        cs = b.get("cols") or b.get("칸") or []
        rows = b.get("rows") or b.get("날") or []
        if name_ not in cs:
            return None
        i = cs.index(name_)
        return {str(r[0]): float(r[i]) for r in rows if r[i] is not None}

    def dicts(b, key):
        return {str(r["date"]): float(r[key]) for r in (b.get("rows") or []) if r.get(key) is not None}

    F = {}
    F["vol"] = frame("volume-data", lambda b: cols(b, "거래량"))
    F["value"] = frame("volume-data", lambda b: cols(b, "거래대금"))
    for who in ("외국인", "기관", "투신", "연기금", "사모", "개인"):
        F[who] = frame("investor-data", lambda b, w=who: cols(b, w))
    F["프로그램"] = frame("program-data", lambda b: dicts(b, "순매수량"))
    F["공매도비중"] = frame("short-data", lambda b: cols(b, "공매도비중"))
    F["신용잔고율"] = frame("credit-data", lambda b: cols(b, "잔고율"))
    F["대차잔고"] = frame("loan-data", lambda b: dicts(b, "잔고주수"))
    F["매수체결"] = frame("side-data", lambda b: dicts(b, "매수체결량"))
    F["매도체결"] = frame("side-data", lambda b: dicts(b, "매도체결량"))

    # 의견: (보고서 날, 목표가) · 공시: (접수일, 종류) · 실적: (접수일, 영업이익 · 작년 · 매출 · 작년)
    ops, evs, qs = {}, {}, {}
    for c in codes:
        b = _json(f"opinion-data/{c}.json")
        if b is None:                 # 파일 없음 = 모름(빈칸) · 파일은 있는데 줄이 없음 = 0건
            ops[c] = None
            b = {}
        else:
            ops[c] = []
        ops[c] = None if ops[c] is None else sorted((str(r["date"]), _poison(r["date"], float(r["target"]))) for r in (b.get("rows") or [])
                        if r.get("target") and _keep(r["date"]))
        b = _json(f"event-data/{c}.json") or {}
        evs[c] = sorted((str(r["date"]), r.get("kind")) for r in (b.get("rows") or []) if r.get("date") and _keep(r["date"]))
        b = _json(f"quarter-data/{c}.json") or {}
        got = []
        for k, v in (b.get("rows") or {}).items():
            if not v or not str(v.get("접수번호", ""))[:8].isdigit():
                continue
            d = str(v["접수번호"])[:8]
            if not _keep(d):
                continue
            num = lambda x: float(str(x).replace(",", "")) if x not in (None, "", "-") else None
            got.append((d, num(v.get("영업이익")), num(v.get("영업이익_작년")), num(v.get("매출")), num(v.get("매출_작년"))))
        qs[c] = sorted(got, key=lambda r: r[0])
    return C, F, ops, evs, qs, name


# ───────────────────────── 재료(그날까지 자료만) ─────────────────────────

def features(C, F, ops, evs, qs):
    """{재료 이름: DataFrame[날 × 종목]} — 모든 값은 그 줄 날짜 이하 자료로만 셈(뒤로 굴리는 rolling · shift(+k)만)."""
    X = {}
    r1 = C.pct_change(fill_method=None)
    X["수익5"] = C / C.shift(5) - 1
    X["수익20"] = C / C.shift(20) - 1
    X["수익60"] = C / C.shift(60) - 1
    X["수익250_20"] = C.shift(20) / C.shift(250) - 1
    X["52주고점비"] = C / C.rolling(250, min_periods=200).max()
    X["변동성20"] = r1.rolling(20, min_periods=15).std()
    X["정배열50_200"] = (C.rolling(50).mean() > C.rolling(200).mean()).astype(float).where(C.rolling(200).count() >= 200)
    X["거래대금증가"] = F["value"].rolling(20, min_periods=15).mean() / F["value"].rolling(120, min_periods=80).mean()
    vol20 = F["vol"].rolling(20, min_periods=15).sum()
    vol60 = F["vol"].rolling(60, min_periods=45).sum()
    for who in ("외국인", "기관", "투신", "연기금", "사모", "개인"):
        X[f"{who}20"] = F[who].rolling(20, min_periods=15).sum() / vol20
        X[f"{who}60"] = F[who].rolling(60, min_periods=45).sum() / vol60
    X["외국인전환"] = X["외국인20"] - X["외국인60"]
    X["프로그램20"] = F["프로그램"].rolling(20, min_periods=15).sum() / vol20
    X["공매도20"] = F["공매도비중"].rolling(20, min_periods=15).mean()
    X["공매도변화"] = X["공매도20"] - F["공매도비중"].rolling(60, min_periods=45).mean()
    X["신용잔고율"] = F["신용잔고율"]
    X["신용변화20"] = F["신용잔고율"] - F["신용잔고율"].shift(20)
    X["대차변화20"] = F["대차잔고"] / F["대차잔고"].shift(20) - 1
    tot = (F["매수체결"] + F["매도체결"]).rolling(20, min_periods=15).sum()
    X["매수체결비"] = F["매수체결"].rolling(20, min_periods=15).sum() / tot - 0.5
    # 엿보기 대조(일부러 하루 미래) — 진짜 재료와 견주기용 · 고르기 · 시험에서는 뺌
    # (산 뒤 5일(t+2 ~ t+6) 외국인 수급 = 들고 있는 동안의 미래 → 이걸 쓰면 성적이 얼마나 부풀려지는지 보임)
    X["엿보기_외국인내일"] = F["외국인"].rolling(5).sum().shift(-(GAP + 5)) / F["vol"].rolling(5).sum().shift(-(GAP + 5))

    days = list(C.index)
    di = {d: i for i, d in enumerate(days)}
    n, m = len(days), len(C.columns)

    def per_code(fn):
        a = np.full((n, m), np.nan)
        for j, c in enumerate(C.columns):
            fn(j, c, a)
        return pd.DataFrame(a, index=days, columns=C.columns)

    dnum = np.array([int(d) for d in days])
    cal = pd.to_datetime(pd.Series(days))
    ordinal = cal.map(pd.Timestamp.toordinal).to_numpy()

    def window_count(dates, back_days):
        """그날 이하 · back_days(달력 날) 안의 건수 — 날마다."""
        if not dates:
            return np.zeros(n)
        o = np.array(sorted(pd.Timestamp(d).toordinal() for d in dates))
        hi = np.searchsorted(o, ordinal, side="right")            # 그날 이하
        lo = np.searchsorted(o, ordinal - back_days, side="right")
        return hi - lo

    def ev(kind):
        def fn(j, c, a):
            a[:, j] = window_count([d for d, k in evs[c] if k == kind], 60)
        return fn
    for kind in EVENT_KINDS:
        X[f"공시60_{kind}"] = per_code(ev(kind))

    def op_fn(which):
        def fn(j, c, a):
            rows = qs[c]
            if not rows:
                return
            ds = np.array([int(r[0]) for r in rows])
            k = np.searchsorted(ds, dnum, side="right") - 1          # 그날 이하에 접수된 가장 최근
            for t in range(n):
                if k[t] < 0:
                    continue
                r = rows[k[t]]
                now, prev = (r[1], r[2]) if which == "op" else (r[3], r[4])
                if now is not None and prev not in (None, 0):
                    a[t, j] = max(-3.0, min(3.0, (now - prev) / abs(prev)))
        return fn
    X["영업이익증가"] = per_code(op_fn("op"))
    X["매출증가"] = per_code(op_fn("sales"))

    def opinion(kind):
        def fn(j, c, a):
            rows = ops[c]
            if rows is None:
                return
            if not rows:
                if kind == "n60":
                    a[:, j] = 0
                return
            o = np.array([pd.Timestamp(d).toordinal() for d, _ in rows])
            tg = np.array([t for _, t in rows])
            cs = np.concatenate([[0], np.cumsum(tg)])
            hi = np.searchsorted(o, ordinal, side="right")
            if kind == "n60":
                lo = np.searchsorted(o, ordinal - 60, side="right")
                a[:, j] = hi - lo
                return
            lo90 = np.searchsorted(o, ordinal - 90, side="right")
            mean90 = np.where(hi > lo90, (cs[hi] - cs[lo90]) / np.maximum(hi - lo90, 1), np.nan)
            if kind == "upside":
                a[:, j] = mean90 / C.iloc[:, j].to_numpy() - 1
            else:   # 목표가 올림: 최근 30일 평균 / 31~120일 전 평균
                lo30 = np.searchsorted(o, ordinal - 30, side="right")
                lo120 = np.searchsorted(o, ordinal - 120, side="right")
                m30 = np.where(hi > lo30, (cs[hi] - cs[lo30]) / np.maximum(hi - lo30, 1), np.nan)
                mold = np.where(lo30 > lo120, (cs[lo30] - cs[lo120]) / np.maximum(lo30 - lo120, 1), np.nan)
                a[:, j] = m30 / mold - 1
        return fn
    X["의견수60"] = per_code(opinion("n60"))
    X["목표가여력"] = per_code(opinion("upside"))
    X["목표가올림"] = per_code(opinion("rev"))
    # 그날 값(종가)이 없는 종목(아직 상장 전 등)은 재료도 비움 — 공시 '0건'이 상장 전 날에 찍히지 않게(자르기 시험에서 찾음)
    return {k: (v if k.startswith("엿보기") else v.where(C.notna())) for k, v in X.items()}


def universe(C):
    """그날 시가총액 TOP 안(그날까지 접수된 주식수 × 그날 종가)."""
    inside = pd.DataFrame(False, index=C.index, columns=C.columns)
    size = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for c in C.columns:
        tl = caps.timeline(c)
        if not tl:
            continue
        ds = np.array([int(d) for d, _ in tl])
        cnt = np.array([n for _, n in tl], dtype=float)
        k = np.searchsorted(ds, np.array([int(d) for d in C.index]), side="right") - 1
        sh = np.where(k >= 0, cnt[np.maximum(k, 0)], np.nan)
        size[c] = sh * C[c].to_numpy()
    rank = size.rank(axis=1, ascending=False)
    inside = rank <= TOP
    return inside, size


# ───────────────────────── 잣대 ─────────────────────────

def forward(C):
    """t에 판단 → t+GAP 종가에 사서 t+GAP+H 종가에 팜."""
    return C.shift(-(GAP + H)) / C.shift(-GAP) - 1


def period(d):
    y = int(d[:4])
    return "2017~19" if y <= 2019 else "2020~22" if y <= 2022 else "2023~25" if y <= 2025 else "2026"


def evaluate(X, C, inside):
    fwd = forward(C)
    days = [d for i, d in enumerate(C.index) if d >= START and i % STEP == 0 and i + GAP + H < len(C.index)]
    res = {}
    for name_, F in X.items():
        ics, spreads = {}, {}
        for d in days:
            ok = inside.loc[d] & F.loc[d].notna() & fwd.loc[d].notna()
            if ok.sum() < 40:
                continue
            f, r = F.loc[d][ok], fwd.loc[d][ok]
            r = r - r.median()
            if f.nunique() < 2:
                continue
            ic = f.rank().corr(r.rank())
            if f.nunique() <= 5:      # 0/1 · 건수 재료: 있음(가장 작은 값보다 큼) − 없음
                hi, lo = f > f.min(), f == f.min()
                sp = r[hi].mean() - r[lo].mean() if hi.sum() >= 3 else np.nan
            else:
                q = f.rank(pct=True)
                sp = r[q > 0.8].mean() - r[q <= 0.2].mean()
            ics.setdefault(period(d), []).append(ic)
            spreads.setdefault(period(d), []).append(sp)
            if d >= "20260601":
                ics.setdefault("요즘(6~9월)", []).append(ic)
                spreads.setdefault("요즘(6~9월)", []).append(sp)
        out = {}
        for p in ics:
            a = np.array(ics[p], dtype=float)
            a = a[~np.isnan(a)]
            s = np.array(spreads[p], dtype=float)
            s = s[~np.isnan(s)]
            if len(a) < 3 or len(s) == 0:
                continue
            # 20일 들고 5일마다 재므로 겹침 4배 → t는 √(n/4)
            t = a.mean() / (a.std(ddof=1) + 1e-12) * math.sqrt(len(a) / (H / STEP))
            out[p] = {"IC": round(float(a.mean()), 4), "t": round(float(t), 2), "위-아래(%)": round(float(s.mean()) * 100, 2),
                      "날수": int(len(a))}
        res[name_] = out
    return res


def recent_winners(C, X, inside, name, look=60):
    """요즘(마지막 look거래일) 많이 오른 대상 종목 20 + 그 출발점(look일 전)의 재료 백분위."""
    t0 = C.index[-1 - look]
    t1 = C.index[-1]
    ok = inside.loc[t0]
    ret = (C.loc[t1] / C.loc[t0] - 1)[ok].dropna().sort_values(ascending=False)
    top = list(ret.index[:20])
    prof = {}
    for f, F in X.items():
        if f.startswith("엿보기"):
            continue
        row = F.loc[t0][ok]
        if row.notna().sum() < 40:
            continue
        pct = row.rank(pct=True)
        v = pct.reindex(top).dropna()
        if len(v) >= 8:
            prof[f] = round(float(v.mean()), 3)
    return {"출발": t0, "끝": t1, "오른 종목": [(c, name[c], round(float(ret[c]) * 100, 1)) for c in top],
            "출발점 백분위 평균(0.5 = 보통)": dict(sorted(prof.items(), key=lambda kv: -abs(kv[1] - 0.5)))}


def pick_and_test(res):
    """2017~2022만 보고 고름: 두 반 같은 쪽 · 둘 다 |t| ≥ 2 → 2023~25 · 2026 · 요즘 성적."""
    chosen = []
    for f, out in res.items():
        if f.startswith("엿보기"):
            continue
        a, b = out.get("2017~19"), out.get("2020~22")
        if a and b and np.sign(a["IC"]) == np.sign(b["IC"]) and min(abs(a["t"]), abs(b["t"])) >= 2:
            chosen.append({"재료": f, "쪽": "+" if a["IC"] > 0 else "−", **{p: out.get(p) for p in ("2017~19", "2020~22", "2023~25", "2026", "요즘(6~9월)")}})
    return chosen


def combined(X, C, inside, chosen, train_end="20221231"):
    """고른 재료를 쪽(부호)대로 순위 평균 → 하나의 점수. 고르기 · 부호는 2022까지만 · 시험은 뒤."""
    if not chosen:
        return {}
    fwd = forward(C)
    score = None
    for ch in chosen:
        r = X[ch["재료"]].where(inside).rank(axis=1, pct=True)
        r = r if ch["쪽"] == "+" else 1 - r
        score = r.fillna(0.5) if score is None else score + r.fillna(0.5)     # 값이 없는 재료는 보통(0.5)으로
    days = [d for i, d in enumerate(C.index) if d >= START and i % STEP == 0 and i + GAP + H < len(C.index)]
    out = {}
    for d in days:
        ok = inside.loc[d] & score.loc[d].notna() & fwd.loc[d].notna()
        if ok.sum() < 40:
            continue
        s, r = score.loc[d][ok], fwd.loc[d][ok]
        r = r - r.median()
        q = s.rank(pct=True)
        for p in {period(d), "요즘(6~9월)" if d >= "20260601" else None} - {None}:
            out.setdefault(p, []).append((s.rank().corr(r.rank()), r[q > 0.8].mean() - r[q <= 0.2].mean(), r[q > 0.9].mean()))
    return {p: {"IC": round(float(np.nanmean([x[0] for x in v])), 4), "위-아래(%)": round(float(np.nanmean([x[1] for x in v])) * 100, 2),
                "위 10%(초과 %)": round(float(np.nanmean([x[2] for x in v])) * 100, 2), "날수": len(v)} for p, v in out.items()}


def main():
    C, F, ops, evs, qs, name = load()
    X = features(C, F, ops, evs, qs)
    inside, _ = universe(C)
    res = evaluate(X, C, inside)
    chosen = pick_and_test(res)
    combo = combined(X, C, inside, chosen)
    win = recent_winners(C, X, inside, name)
    out = {"설정": {"H": H, "GAP": GAP, "STEP": STEP, "TOP": TOP, "마지막 날": C.index[-1]}, "재료별": res, "고른 재료(2017~22로만)": chosen,
           "합친 점수": combo, "요즘 오른 종목": win}
    SP.mkdir(parents=True, exist_ok=True)
    (SP / f"z001_H{H}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    show(out)


def show(out):
    print("설정", out["설정"])
    print("\n[재료별 IC · t · 위-아래 %]  (2017~19 | 2020~22 | 2023~25 | 2026 | 요즘)")
    for f, o in sorted(out["재료별"].items(), key=lambda kv: -abs((kv[1].get("2026") or {}).get("IC", 0))):
        cells = []
        for p in ("2017~19", "2020~22", "2023~25", "2026", "요즘(6~9월)"):
            x = o.get(p)
            cells.append(f"{x['IC']:+.3f}({x['t']:+.1f}) {x['위-아래(%)']:+.1f}%" if x else "-")
        print(f"{f:14s} | " + " | ".join(cells))
    print("\n[2017~22로만 고른 재료]")
    for ch in out["고른 재료(2017~22로만)"]:
        print(ch["재료"], ch["쪽"], {p: (ch[p] or {}).get("IC") for p in ("2023~25", "2026", "요즘(6~9월)")})
    print("\n[합친 점수]", out["합친 점수"])
    w = out["요즘 오른 종목"]
    print("\n[요즘 오른 종목]", w["출발"], "→", w["끝"], w["오른 종목"])
    print("출발점 백분위:", list(w["출발점 백분위 평균(0.5 = 보통)"].items())[:20])


def check():
    """자르기 · 더럽히기 시험: 자른 날 앞(자른 날 − H − 2일까지) 재료가 온 자료와 같아야."""
    global CUT, POISON
    cut = os.getenv("Z_CUT") or "20220615"
    CUT, POISON = "", ""
    C0, F0, o0, e0, q0, _ = load()
    X0 = features(C0, F0, o0, e0, q0)
    ok = True
    for mode in ("cut", "poison"):
        CUT, POISON = (cut, "") if mode == "cut" else ("", cut)
        C1, F1, o1, e1, q1, _ = load()
        X1 = features(C1, F1, o1, e1, q1)
        bad = []
        for f in X0:
            if f.startswith("엿보기"):
                continue
            a = X0[f].loc[X0[f].index <= cut]
            b = X1[f].reindex(index=a.index, columns=a.columns)
            if not np.allclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float), equal_nan=True, atol=1e-12):
                diff = ~np.isclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float), equal_nan=True, atol=1e-12)
                bad.append(f"{f}(처음 다른 날 {a.index[np.argwhere(diff)[0][0]]})")
        # 엿보기 대조는 반드시 걸려야 함(검사 눈이 살아 있나)
        a = X0["엿보기_외국인내일"].loc[X0["엿보기_외국인내일"].index <= cut]
        b = X1["엿보기_외국인내일"].reindex(index=a.index, columns=a.columns)
        caught = not np.allclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float), equal_nan=True)
        print(f"[{mode} {cut}] 진짜 재료 {len(X0) - 1}개: {'합격' if not bad else '불합격 — ' + ', '.join(bad)} · 엿보기 대조 {'걸림(검사 눈 살아 있음)' if caught else '안 걸림(검사 눈 고장)'}")
        ok &= (not bad) and caught
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(check() if sys.argv[1:2] == ["check"] else main())
