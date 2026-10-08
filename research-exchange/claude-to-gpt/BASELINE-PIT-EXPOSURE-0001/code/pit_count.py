"""BASELINE-PIT-EXPOSURE-0001 · PR #78 고친 후보의 Train 신호 · 목표 · 체결이 기대는 입력의 시점 증거 계수(성과 재실행 없음).
python3 -E -P pit_count.py <b2> <b3> <저장소(git)> <옛 nrl-cache.pkl> <PR68 control_trades.json> <PR74 signals_old.json>
                          <PR76 fixed_local_only.json> <PR78 m15_fixed_local_only.json> <출력 폴더>

- 읽기만: 고정 스냅샷 b2/b3(00b98ab1)의 자료 파일 · git 판 이력(git show) · 저장 원장. 네트워크 막음 · 키 환경변수 지움 · API 0.
- 15분봉 맥락(ATT)은 PR #68 m15_exec 앞부분(자료 · 맥락 준비)만 불러 얻음. 계좌 루프는 돌리지 않음.
- 원가격 · 원수량 · 종목명은 내보내지 않음. 개수 · 비율 · 날짜 간격만."""
import bisect
import json
import os
import pickle
import socket
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

B2, B3, REPO = (str(Path(x).resolve()) for x in sys.argv[1:4])
OLD, CTRL, SIG, L76, L78, OUT = sys.argv[4:10]
OUT = Path(OUT)
OUT.mkdir(parents=True, exist_ok=True)
LO, HI = "20250918", "20260331"
SNAP = "00b98ab1655c84806357f44f2de6f1509ef1447f"
_real_socket = socket.socket


def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지")


socket.socket = _blocked
socket.create_connection = _blocked
for k in list(os.environ):
    if k.startswith(("KIS", "DART", "PAPER", "DISCORD")):
        os.environ.pop(k)
t0 = time.time()
LOG = []


def say(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


jl = lambda p: json.load(open(p, encoding="utf-8"))
O = pickle.load(open(OLD, "rb"))
CL = {c: dict(v["rows"]) for c, v in O[0].items()}
CAL = sorted(d for d in CL["005930"] if LO <= d <= HI)
assert len(CAL) == 127
ALLCAL = sorted(CL["005930"])
CT = jl(CTRL)
SG = jl(SIG)
F76 = jl(L76)
F78 = jl(L78)
prev_td = lambda d: ALLCAL[bisect.bisect_left(ALLCAL, d) - 1]
tgap = lambda a, b: bisect.bisect_left(ALLCAL, b) - bisect.bisect_left(ALLCAL, a)   # a → b 거래일 수(달력 005930)

# ═════════ 단위(원장) ═════════
U = {}
U["D1_signal_rows"] = [(d, c) for d, v in SG["picks"].items() if LO <= d <= HI for c, _ in v]
for k in ("D1", "BASKET", "M15", "ETF"):
    U[f"{k}_control_fills"] = [(str(t), c, s) for t, c, s, n, p in CT[k] if LO <= str(t)[:8] <= HI]
for k in ("D1", "ETF", "BASKET"):
    U[f"{k}_candidate_locks"] = [(x["decided_at"], c) for x in F76[k]["decisions"] for c in x["targets"]] or []
    U[f"{k}_candidate_lock_events"] = [x["decided_at"] for x in F76[k]["decisions"]]
    U[f"{k}_candidate_fills"] = [(d, c, s) for d, c, s, n in F76[k]["trades"]]
U["M15_candidate_locks"] = [(x["locked_at"], x["code"]) for x in F78["locks"]]
U["M15_candidate_fills"] = [(t, c, s) for t, c, s, n in F78["trades"]]
counts = {k: {"n": len(v), "codes": len({x[1] for x in v}) if v and isinstance(v[0], tuple) else None,
              "days": len({str(x[0])[:8] for x in v}) if v and isinstance(v[0], tuple) else len(set(v))} for k, v in U.items()}
say("단위", json.dumps(counts, ensure_ascii=False))


# ═════════ 입력 파일 · 증거 칸 ═════════
def fields_of(folder):
    fs = sorted(Path(B2, folder).glob("*.json"))
    top = Counter()
    rec = Counter()
    for f in fs:
        j = jl(f)
        top.update(j.keys())
        rows = j.get("rows")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            rec.update(rows[0].keys())
        elif isinstance(rows, dict):
            for v in rows.values():
                if v:
                    rec.update(v[0].keys())
                    break
    return {"files": len(fs), "file_level_keys": dict(top), "record_level_keys(dict 행)": dict(rec)}


FIELDS = {f: fields_of(f) for f in ("price-data", "volume-data", "investor-data", "share-data", "opinion-data", "event-data", "dart-events", "etf-data")}
EVIDENCE_KEYS = ("as_of", "available_at", "fetched_at", "fetched", "version", "revision", "hash", "provenance", "rcept_no", "접수일", "받은날")
say("증거 칸(파일 단위 · 행 단위)", json.dumps({f: {"file": [k for k in v["file_level_keys"] if k in EVIDENCE_KEYS],
                                              "record": [k for k in v["record_level_keys(dict 행)"] if k in EVIDENCE_KEYS]} for f, v in FIELDS.items()}, ensure_ascii=False))


# ═════════ git 판 이력(처음 들어온 시각 · 값 수정) ═════════
def vintages(path):
    out = subprocess.run(["git", "-C", REPO, "log", "--format=%H %cI", SNAP, "--", path], capture_output=True, text=True).stdout.split("\n")
    return [x.split() for x in out if x.strip()][::-1]


def first_seen(path):
    v = vintages(path)
    return v[0][1] if v else None


def price_versions(code):
    out = []
    for h, when in vintages(f"price-data/{code}.json"):
        raw = subprocess.run(["git", "-C", REPO, "show", f"{h}:price-data/{code}.json"], capture_output=True, text=True).stdout
        try:
            out.append((when, {str(d): float(c) for d, c in json.loads(raw).get("closes") or []}))
        except ValueError:
            pass
    return out


# 가격 레코드: 체결(통제 D1 · 바구니 · 후보 D1 · 바구니) + D1 신호 줄의 그날 종가
need = defaultdict(set)
for d, c in U["D1_signal_rows"]:
    need[c].add(d)
for k in ("D1_control_fills", "BASKET_control_fills", "D1_candidate_fills", "BASKET_candidate_fills"):
    for t, c, s in U[k]:
        need[c].add(t[:8])
rev = {"records": 0, "first_seen_before_decision": 0, "value_changed_across_vintages": 0, "used_equals_first_vintage": 0,
       "used_not_in_any_vintage": 0, "codes": len(need), "codes_with_any_change": 0, "vintages_per_code_median": None}
nv = []
for c, days in sorted(need.items()):
    vs = price_versions(c)
    nv.append(len(vs))
    changed_code = False
    for d in sorted(days):
        rev["records"] += 1
        vals = [v[d] for _, v in vs if d in v]
        firsts = [w for w, v in vs if d in v]
        if firsts and firsts[0][:10].replace("-", "") <= d:
            rev["first_seen_before_decision"] += 1
        if len(set(vals)) > 1:
            rev["value_changed_across_vintages"] += 1
            changed_code = True
        used = CL.get(c, {}).get(d)
        if vals and used == vals[0]:
            rev["used_equals_first_vintage"] += 1
        if used is not None and used not in vals:
            rev["used_not_in_any_vintage"] += 1
    rev["codes_with_any_change"] += changed_code
rev["vintages_per_code_median"] = sorted(nv)[len(nv) // 2] if nv else None
say("가격 판", rev)

FS = {f: first_seen(f"{f}/005930.json") for f in ("price-data", "volume-data", "investor-data", "share-data", "opinion-data", "event-data", "dart-events", "etf-data")}
FS["m15-kis"] = first_seen("m15-kis/005930/2025.csv")
say("저장소에 처음 들어온 시각(005930 파일 기준)", FS)

# ═════════ 실측 시점 검사(D1 신호 줄) ═════════
os.chdir(B2)
sys.path[:0] = [B2, B2 + "/research"]
import caps  # noqa: E402
import final_group  # noqa: E402
import study  # noqa: E402

flows = {}
chk = Counter()
same_day_share_dates = set()
for d in sorted({d for d, _ in U["D1_signal_rows"]}):
    n_same = 0
    for c in CL:
        tl = caps.timeline(c)
        k = bisect.bisect_right([x[0] for x in tl], d) - 1
        if k >= 0 and tl[k][0] == d:
            n_same += 1
    if n_same:
        same_day_share_dates.add(d)
for d, c in U["D1_signal_rows"]:
    if c not in flows:
        flows[c] = [x["date"] for x in final_group.flow_rows(c)]
    days = flows[c]
    idx = bisect.bisect_left(days, d)
    used_max = days[idx - 2] if idx >= 2 else None                       # flow_sum(lag=2) · steady(shift=1)의 마지막 줄
    if used_max is None:
        chk["flow_missing"] += 1
    else:
        g = tgap(used_max, d)
        chk[f"flow_gap_{min(g, 5)}"] += 1
        if used_max >= d:
            chk["flow_VIOLATION"] += 1
    tl = study.target_timeline(c)
    tdays = [x for x, _ in tl]
    kk = bisect.bisect_left(tdays, d)
    if kk and tdays[kk - 1] >= d:
        chk["opinion_VIOLATION"] += 1
    chk["opinion_used" if kk else "opinion_none"] += 1
    sh = caps.timeline(c)
    ks = bisect.bisect_right([x[0] for x in sh], d) - 1
    if ks < 0:
        chk["share_none"] += 1
    elif sh[ks][0] == d:
        chk["share_same_day_own"] += 1
    else:
        chk["share_before"] += 1
    if d in same_day_share_dates:
        chk["rank_date_has_any_same_day_share_filing"] += 1
say("D1 신호 줄 시점 실측", dict(chk))

# 바구니: 사건 접수일 ≤ t0(결정 전 거래일) < 결정일
EV = {}
for p in Path(B2, "event-data").glob("*.json"):
    b = jl(p)
    EV[b.get("code") or p.stem] = [(r["date"], r["kind"]) for r in b.get("rows") or [] if r.get("date") and r.get("kind") in ("자사주취득", "무상증자")]
bchk = Counter()
for t, c, s in U["BASKET_control_fills"]:
    if s != "buy":
        continue
    dec = prev_td(t[:8])                                                 # 다음 날 종가 체결 → 판단은 전 거래일
    t0_ = prev_td(dec)                                                   # step의 t0 = 판단일 앞 거래일
    ev = [x for x, k in EV.get(c, []) if prev_td(t0_) < x <= t0_]
    bchk["buy_with_event"] += bool(ev)
    bchk["event_VIOLATION"] += any(x >= dec for x in ev)
    bchk["event_gap_days_min"] = min(bchk.get("event_gap_days_min", 99), min((tgap(x, dec) for x in ev), default=99))
say("바구니 사건 시점 실측", dict(bchk))

# 정지 흔적 · 기업행동 증거(체결 종목)
gap = Counter()
traded = {c for k in ("D1_control_fills", "BASKET_control_fills", "D1_candidate_fills", "BASKET_candidate_fills") for _, c, _ in U[k]}
for c in traded:
    ds = sorted(d for d in CL.get(c, {}) if LO <= d <= HI)
    miss = sorted(set(CAL) - set(ds))
    gap["codes"] += 1
    gap["codes_with_missing_train_days"] += bool(miss)
    gap["missing_code_days"] += len(miss)
CA_KINDS = ("감자", "분할", "합병", "무상증자", "유상증자", "유무상증자")
ca = Counter()
for c in traded:
    p = Path(B2, "dart-events", f"{c}.json")
    if not p.exists():
        ca["codes_no_dart_file"] += 1
        continue
    rows = jl(p)["rows"]
    hit = [str(r.get("rcept_no", ""))[:8] for k in CA_KINDS for r in rows.get(k) or [] if LO <= str(r.get("rcept_no", ""))[:8] <= "20261007"]
    ca["codes_with_dart_file"] += 1
    ca["codes_with_CA_filing_20250918_20261007"] += bool(hit)
say("정지 흔적(가격 빈 날) · 기업행동 공시", dict(gap), dict(ca))

# ═════════ 15분봉: 맥락이 전 거래일인지 실측 ═════════
os.environ["MR_D1PICKS"] = os.environ.get("MR_D1PICKS", "")
m15 = {}
try:
    HERE = Path(__file__).resolve().parent
    src = (HERE / "m15_exec.py").read_text(encoding="utf-8").split("\ndef run(mult):")[0]
    P = {"__name__": "pit_m15", "__file__": str(HERE / "m15_exec.py")}
    sys.argv = [sys.argv[0], B3, str(OUT / "m15_tmp")]
    exec(compile(src, "m15_exec(앞부분 · 자료 · 맥락만)", "exec"), P)
    G = P["G"]
    data, ATT, IN = G["data"], G["ATT"], G["IN"]
    mc = Counter()
    for t, c, s in U["M15_control_fills"]:
        if s != "buy":
            continue
        b = data[c]
        k = bisect.bisect_left(b["t"], t)
        assert b["t"][k] == t
        ks = k - 1                                                       # 신호 봉(체결 앞 봉)
        x = ATT[c][ks]
        mc["buys"] += 1
        if x is None:
            mc["ctx_none"] += 1
            continue
        mc["ctx_day_before_signal_bar_day"] += x["날"] < b["t"][ks][:8]
        mc["ctx_VIOLATION"] += x["날"] >= b["t"][ks][:8]
        fe = x.get("수급끝")
        mc["flow_end_before_ctx_day"] += bool(fe) and fe < x["날"]
        mc["flow_VIOLATION"] += bool(fe) and fe >= b["t"][ks][:8]
        mc["in_universe_prev_day_rank"] += bool(IN[c][ks])
        day = t[:8]
        last = [i for i, tt in enumerate(b["t"]) if tt[:8] == day]
        dc = CL.get(c, {}).get(day)
        if last and dc:
            mc["fill_day_bar_close_eq_daily_close"] += abs(float(b["c"][last[-1]]) - dc) < 1e-6
            mc["fill_day_compared"] += 1
    m15 = dict(mc)
except Exception as e:                                                   # 실패도 기록
    m15 = {"error": repr(e)[:300]}
say("15분봉 맥락 실측", m15)

# ═════════ 분류 ═════════
CAUSES = ("U1_UNIVERSE_T_SNAPSHOT_없음", "U2_가격_BASIS(원/수정)_증거_없음", "U3_거래정지·기업행동_상태_증거_없음",
          "U4_레코드_판·처음_도착시각_없음(저장소 처음 들어온 때가 결정 뒤)", "U5_같은날_접수_주식수(시각_없음)")
UNIT_CAUSES = {}
for k, v in U.items():
    n = len(v)
    base = {CAUSES[0]: n, CAUSES[1]: n, CAUSES[2]: n, CAUSES[3]: n}
    if k == "D1_signal_rows":
        base[CAUSES[4]] = chk["rank_date_has_any_same_day_share_filing"]
    if k.startswith("ETF"):
        base[CAUSES[0]] = n                                              # 시장 폭(BR)이 주식 상위100에 기댐
    UNIT_CAUSES[k] = base
CLASS = {k: {"PROVEN_PIT": 0, "CONSERVATIVE_ASSUMPTION": 0, "UNKNOWN_EVIDENCE": len(v),
             "VIOLATION": 0} for k, v in U.items()}
viol = chk["flow_VIOLATION"] + chk["opinion_VIOLATION"] + bchk["event_VIOLATION"] + (m15.get("ctx_VIOLATION", 0) + m15.get("flow_VIOLATION", 0) if "error" not in m15 else 0)
INPUT_TYPES = {
    "가격 종가(price-data)": {"timing": "CONSERVATIVE_ASSUMPTION(그날 종가 · 판단은 종가 뒤 · 체결은 다음 날 종가)", "value_basis": "UNKNOWN_EVIDENCE", "version": "UNKNOWN_EVIDENCE"},
    "고가/저가/거래량(volume-data)": {"timing": "CONSERVATIVE_ASSUMPTION(그날까지)", "value_basis": "UNKNOWN_EVIDENCE", "version": "UNKNOWN_EVIDENCE"},
    "주식수(share-data · 접수일)": {"timing": f"접수일 < 판단일 CONSERVATIVE · 같은 날 UNKNOWN_EVIDENCE(시각 없음)", "value_basis": "UNKNOWN_EVIDENCE(수정주가 × 그때 주식수 · caps.py 주석)", "version": "UNKNOWN_EVIDENCE"},
    "수급(investor-data)": {"timing": "CONSERVATIVE_ASSUMPTION(T−2 · 실측 위반 0)", "value_basis": "해당 없음", "version": "UNKNOWN_EVIDENCE(정정 판 없음)"},
    "목표가(opinion-data)": {"timing": "CONSERVATIVE_ASSUMPTION(판단일 앞 날짜만 · 실측 위반 0)", "value_basis": "해당 없음", "version": "UNKNOWN_EVIDENCE"},
    "사건(event-data · 바구니)": {"timing": "CONSERVATIVE_ASSUMPTION(판단 전 거래일까지 접수 · 실측 위반 0)", "value_basis": "해당 없음", "version": "UNKNOWN_EVIDENCE(정정 연결 없음)"},
    "15분봉(m15-kis)": {"timing": "CONSERVATIVE_ASSUMPTION(봉 닫힌 뒤 판단 · 다음 봉 시가)", "value_basis": "UNKNOWN_EVIDENCE", "version": "UNKNOWN_EVIDENCE"},
    "15분봉 일봉 맥락(전 거래일)": {"timing": "CONSERVATIVE_ASSUMPTION(prev_day · 수급 끝 당김 · 실측)", "value_basis": "가격과 같음", "version": "UNKNOWN_EVIDENCE"},
    "Universe(t) · 시총 순위": {"timing": "UNKNOWN_EVIDENCE(지금 남은 종목만 · 상장폐지 종목 없음)", "value_basis": "UNKNOWN_EVIDENCE", "version": "UNKNOWN_EVIDENCE"},
    "거래정지 · 기업행동 상태": {"timing": "UNKNOWN_EVIDENCE(상태 자료 없음)", "value_basis": "-", "version": "-"},
}
RES = {"units": counts, "fields": FIELDS, "first_seen_in_repo(005930)": FS, "price_vintages": rev, "d1_signal_timing": dict(chk),
       "basket_event_timing": dict(bchk), "halt_gaps": dict(gap), "corporate_action_filings": dict(ca), "m15_context_timing": m15,
       "classification_per_unit": CLASS, "unknown_causes_non_exclusive": UNIT_CAUSES,
       "primary_cause_rule": "원인 순서 U1 > U2 > U3 > U4 > U5 중 처음 해당하는 것 하나(모든 단위가 U1에 해당 → 1차 원인 전부 U1)",
       "input_types": INPUT_TYPES, "proven_violations_found": viol, "seconds": round(time.time() - t0)}
(OUT / "PIT-COVERAGE.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
(OUT / "run.log").write_text("\n".join(LOG) + "\n", encoding="utf-8")
say("끝", round(time.time() - t0), "초")
