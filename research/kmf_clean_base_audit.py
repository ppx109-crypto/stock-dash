"""CLEAN-0001 독립 감사(잠금 6cf246c4의 kmf_clean_base 결과를 다시 셈 · 기존 research/*.py는 고치지 않음).
1. 세 입력 CSV를 kmf_nb.load()와 같은 방식으로 직접 읽고(kmf_hdd_fc · kmf_clean_base 안 씀) 달력 근월물 규칙으로 계약을 고른 뒤
   분이 빠진 15분봉(09:00~15:14)이 있는 날을 직접 찾아 meta.excluded_days와 견줌. kiwoom-data 선물 구간 날마다 '그날 거래량 1위 계약'과
   '달력 근월물'이 다른 날 수를 세고 날별 계약 표를 남김.
2. 다섯 판(R0 매일 · S3 매일 · R0 조용한 날만 · S3 안 조용한 날만 · H)의 날별 손익을 다시 셈.
   정직하게 적음: 체결(execute) · 15분봉 · EMA/ATR · R0/T2 신호 함수는 잠근 kmf_nb.py 원문을 그대로 씀.
   다만 원문의 'ROWS = load();' 한 줄만 '감사가 직접 만든 줄'로 바꿔 넣음(근월물 · 뺀 날 처리는 감사 쪽 코드).
   조용함(Z) · S3 기울기 거르기 · 판 조합 · 평가 날짜는 감사가 따로 짬. 또 kmf_hdd_fc 엔진의 줄과 감사 줄이 한 줄도 안 다른지 따로 견줌.
3. 합 · MDD · 최악 · 연속손실 · 회복최장 · 나쁜달 · 앞반 · 뒤반 · −15 넘은 날 · 거래한 날 · 달별을 감사 식으로 다시 셈 → out.json과 견줌.
4. 뺀 날마다 원래(거르지 않은) 엔진의 H 손익(kmf_hdd_pre_daily.json 'H(대조)')과 그 합 · 전체 합.
python3 research/kmf_clean_base_audit.py → research/kmf_clean_base_audit.out(JSON)"""
import csv, json, sys, types, hashlib, collections, statistics as st
from datetime import date, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE))
MINI = ROOT / "kiwoom-data/mini_1min_2026_01_08.csv"; FUT = ROOT / "kiwoom-data/kospi200_futures_1min.csv"; F1M = ROOT / "futures-1m/mini_kospi200_futures_1min.csv"
FIRST, LAST, F1M_FROM, DEV_END = 540, 934, "20261013", "20261014"
NB_SHA = "b34f3549fe9a93b951e104148605404737f0bab30faf2d6960296d59957b55de"
MCH = "123456789ABC"

def cal_front(d):
    """둘째 목요일(만기일) 당일부터 다음 달 월물."""
    day = date(int(d[:4]), int(d[4:6]), int(d[6:])); y, m = day.year, day.month
    while True:
        first = date(y, m, 1); off = (3 - first.weekday()) % 7; thu2 = first + timedelta(days=off + 7)
        if day < thu2: return f"A05{y % 10}{MCH[m - 1]}000"
        m += 1
        if m == 13: y, m = y + 1, 1

def mins(s): return int(s[11:13]) * 60 + int(s[14:16])

# ---------- 1. 독립 읽기 ----------
def read_all():
    rows = []
    with open(MINI, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            m = int(r["minute"])
            if FIRST <= m <= LAST: rows.append((r["date"], m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"]))))
    last_mini = max(r[0] for r in rows); fut = collections.defaultdict(list)
    with open(FUT, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            d = r["datetime"][:10].replace("-", "")
            if d <= last_mini or d >= F1M_FROM or not r["code"].startswith("A056"): continue
            m = mins(r["datetime"])
            if FIRST <= m <= LAST: fut[d].append((r["code"], m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"]))))
    table, skipped = [], []
    for d in sorted(fut):
        vol = collections.Counter(); n = collections.Counter()
        for x in fut[d]: vol[x[0]] += x[6]; n[x[0]] += 1
        top = sorted(vol.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]; cal = cal_front(d)
        table.append({"날": d, "달력 근월물": cal, "거래량 1위": top, "같음": cal == top, "근월물 거래량": vol.get(cal, 0), "1위 거래량": vol[top],
                      "근월물 분 수": n.get(cal, 0), "그날 계약들": dict(sorted(vol.items()))})
        if cal not in vol: skipped.append(d); continue
        rows += [(d,) + x[1:] for x in sorted((x for x in fut[d] if x[0] == cal), key=lambda x: x[1])]
    with open(F1M, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            d = r["datetime"][:10].replace("-", "")
            if not (F1M_FROM <= d < DEV_END): continue
            m = mins(r["datetime"])
            if FIRST <= m <= LAST: rows.append((d, m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"]))))
    return sorted(rows, key=lambda r: (r[0], r[1])), table, skipped, last_mini

ALL, CTAB, SKIP, LAST_MINI = read_all()
def short_days(rows, distinct):
    g = collections.defaultdict(lambda: collections.defaultdict(set if distinct else list))
    for r in rows:
        if 540 <= r[1] <= 914: g[r[0]][(r[1] - 540) // 15].append(r[1]) if not distinct else g[r[0]][(r[1] - 540) // 15].add(r[1])
    bad = {}
    for d in g:
        miss = {540 + (k + 1) * 15: 15 - len(g[d].get(k, ())) for k in range(25) if len(g[d].get(k, ())) < 15}
        if miss: bad[d] = miss
    return bad
BAD = short_days(ALL, distinct=False); BAD_DISTINCT = short_days(ALL, distinct=True)
EXCL = sorted(BAD)
CLEAN = [r for r in ALL if r[0] not in BAD]

OUT = json.loads((HERE / "kmf_clean_base_out.json").read_text()); DAILY = json.loads((HERE / "kmf_clean_base_daily.json").read_text())
meta = OUT["meta"]
res = {"1 뺀 날": {"감사 뺀 날": EXCL, "meta.excluded_days": meta["excluded_days"], "같음": EXCL == meta["excluded_days"],
                  "분 중복 빼고 센 경우도 같음": sorted(BAD_DISTINCT) == EXCL, "뺀 날별 빠진 분(봉 끝 분: 빠진 분 수)": {d: BAD[d] for d in EXCL},
                  "근월물이 없어 통째로 빠진 날": SKIP, "감사 줄 수(거른 뒤)": len(CLEAN), "meta.rows_read": meta["rows_read"],
                  "감사 엔진 날 수": len({r[0] for r in CLEAN}), "meta.engine_days": meta["engine_days"]},
       "1 계약": {"kiwoom 선물 구간 날 수": len(CTAB), "거래량 1위 ≠ 달력 근월물 날 수": sum(1 for t in CTAB if not t["같음"]), "날별 표": CTAB}}

# kmf_hdd_fc 엔진 줄과 견줌(대조용 · 위 결과는 이것 없이 나옴)
import kmf_hdd_fc as FC
K_FC, _P = FC.load_engine()
fc_rows = list(K_FC.ROWS)
res["1 대조: kmf_hdd_fc 엔진 줄과 감사 줄"] = {"줄 수(엔진 · 감사)": [len(fc_rows), len(CLEAN)], "다른 줄 수": sum(1 for a, b in zip(fc_rows, CLEAN) if a != b) + abs(len(fc_rows) - len(CLEAN)),
                                       "엔진 뺀 날 = 감사 뺀 날": sorted(FC.SHORT["detail"]) == EXCL}
for k in [k for k in sys.modules if k in ("kmf_nb", "kmf_hdd_pre", "kmf_hdd_base", "kmf_rlk4", "kmf_rl4")]: del sys.modules[k]

# ---------- 2. 엔진 원문에 감사 줄만 넣어 다시 셈 ----------
src = (HERE / "kmf_nb.py").read_text(encoding="utf-8"); assert hashlib.sha256(src.encode()).hexdigest() == NB_SHA
OLD = "ROWS = load(); BY"; assert src.count(OLD) == 1
K = types.ModuleType("kmf_nb_audit"); K.__file__ = str(HERE / "kmf_nb.py"); K.AUDIT_ROWS = CLEAN
exec(compile(src.replace(OLD, "ROWS = list(AUDIT_ROWS); BY"), K.__file__, "exec"), K.__dict__)
assert K.CUT == ""
DAYS_ALL = sorted({r[0] for r in CLEAN})
# 감사 쪽 조용함: 그날 뺀 앞 20일 하루 폭(%) 가운데 값 → 앞 값들(10개 이상)과만 견준 순위 ≤ 0.6
BY = collections.defaultdict(dict)
for r in CLEAN: BY[r[0]][r[1]] = r
rng = {}
for d in DAYS_ALL:
    x = BY[d]; rng[d] = (max(v[3] for v in x.values()) - min(v[4] for v in x.values())) / x[max(x)][5] * 100
med = {d: st.median([rng[q] for q in DAYS_ALL[i - 20:i]]) for i, d in enumerate(DAYS_ALL) if i >= 20}
Zq, hist = {}, []
for d in DAYS_ALL:
    if d not in med: continue
    if len(hist) >= 10: Zq[d] = sum(1 for h in hist if h <= med[d]) / len(hist) <= 0.6
    hist.append(med[d])
EVAL = [d for d in DAYS_ALL if d in Zq]
JIDX = {(b[0], b[1]): j for j, b in enumerate(K.B15)}
def s3(d):
    out = []
    for s in K.sig_t(d, "T2", s=1.5):
        j = JIDX[(d, s[0])]; a = K.E10[j][1]
        if (abs(K.E20[j][0] - K.E20[j - 4][0]) / a if a else 99.0) <= 0.5: out.append(s)
    return out
PL = {"R0 매일": lambda d: K.sig_r0(d), "S3 매일": s3, "R0 조용한 날만": lambda d: K.sig_r0(d) if Zq[d] else [],
      "S3 안 조용한 날만": lambda d: [] if Zq[d] else s3(d), "H(조용 R0 · 아님 S3)": lambda d: K.sig_r0(d) if Zq[d] else s3(d)}
PNL = {k: {d: K.execute(d, f(d)) for d in EVAL} for k, f in PL.items()}
mm = {}
for k in PL:
    dk = DAILY[k]
    mm[k] = {"날짜 목록 같음": sorted(dk) == EVAL, "다른 칸(>1e-4)": sum(1 for d in EVAL if d not in dk or abs(round(PNL[k][d], 4) - dk[d]) > 1e-4) + sum(1 for d in dk if d not in PNL[k]),
             "가장 큰 차이": round(max(abs(PNL[k][d] - dk.get(d, 1e9)) for d in EVAL), 6)}
res["2 날별 손익"] = {"평가 날(감사 · meta)": [len(EVAL), meta["days"]], "첫 · 끝(감사)": [EVAL[0], EVAL[-1]], "첫 · 끝(meta)": [meta["first"], meta["last"]],
                    "조용한 날(감사 · meta)": [sum(Zq[d] for d in EVAL), meta["quiet_days"]], "판별": mm, "다른 칸 모두": sum(v["다른 칸(>1e-4)"] for v in mm.values())}

# ---------- 3. 성적 다시 셈 ----------
def stat(p, days):
    v = [p[d] for d in days]; eq = pk = mdd = 0.0; run = best = 0; uw = muw = 0; mon = collections.defaultdict(float)
    for d, x in zip(days, v):
        eq += x; mon[d[:6]] += x
        if eq >= pk: pk = eq; uw = 0
        else: uw += 1; muw = max(muw, uw)
        mdd = min(mdd, eq - pk)
        if x < 0: run += 1; best = max(best, run)
        elif x > 0: run = 0
    h = len(days) // 2
    return {"합": round(sum(v), 1), "MDD": round(mdd, 1), "최악": round(min(v), 1), "연속손실": best, "회복최장": muw, "나쁜달": round(min(mon.values()), 1),
            "앞반": round(sum(v[:h]), 1), "뒤반": round(sum(v[h:]), 1), "−15 넘은 날": sum(1 for x in v if x < -15.0), "거래한 날": sum(1 for x in v if x != 0),
            "달별": {m: round(x, 1) for m, x in sorted(mon.items())}}
s_mm, s_tab = {}, {}
for k in PL:
    mine = stat(PNL[k], EVAL); fromdaily = stat(DAILY[k], sorted(DAILY[k])); theirs = OUT["rows"][k]
    diff = [f for f in mine if mine[f] != theirs.get(f)]; diff2 = [f for f in fromdaily if fromdaily[f] != theirs.get(f)]
    s_mm[k] = {"감사 손익으로 셈 · 다른 칸": diff, "daily.json으로 셈 · 다른 칸": diff2}; s_tab[k] = {f: mine[f] for f in mine if f != "달별"}
res["3 성적"] = {"판별 다른 칸": s_mm, "다른 칸 모두": sum(len(v["감사 손익으로 셈 · 다른 칸"]) + len(v["daily.json으로 셈 · 다른 칸"]) for v in s_mm.values()), "감사 성적": s_tab}

# ---------- 4. 뺀 날의 원래 H 손익 ----------
H0 = json.loads((HERE / "kmf_hdd_pre_daily.json").read_text())["H(대조)"]
per = {d: (round(H0[d], 2) if d in H0 else "원래 평가 날 아님") for d in EXCL}
ex_sum = sum(H0[d] for d in EXCL if d in H0); tot = sum(H0.values())
res["4 뺀 날 원래 H"] = {"날별": per, "뺀 날 합": round(ex_sum, 2), "원래 H 전체 합": round(tot, 2), "원래 평가 날 수": len(H0),
                      "뺀 날 비중": round(ex_sum / tot, 3), "뺀 날 빼고 원래 H 합": round(tot - ex_sum, 2), "깨끗한 자료 H 합(out)": OUT["rows"]["H(조용 R0 · 아님 S3)"]["합"]}
res["입력 해시"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (MINI, FUT, F1M)}
res["입력 해시 = meta"] = res["입력 해시"] == meta["data_sha256"]
(HERE / "kmf_clean_base_audit.out").write_text(json.dumps(res, ensure_ascii=False, indent=1))
summary = {"뺀 날 같음": res["1 뺀 날"]["같음"], "계약 다른 날": res["1 계약"]["거래량 1위 ≠ 달력 근월물 날 수"], "엔진 줄 다른 줄": res["1 대조: kmf_hdd_fc 엔진 줄과 감사 줄"]["다른 줄 수"],
           "날별 손익 다른 칸": res["2 날별 손익"]["다른 칸 모두"], "성적 다른 칸": res["3 성적"]["다른 칸 모두"], "뺀 날 원래 H 합": res["4 뺀 날 원래 H"]["뺀 날 합"], "원래 H 합": res["4 뺀 날 원래 H"]["원래 H 전체 합"]}
print(json.dumps(summary, ensure_ascii=False))
