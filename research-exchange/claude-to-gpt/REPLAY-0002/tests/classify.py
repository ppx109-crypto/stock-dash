"""REPLAY-0002 결정론적 분류기(규칙 1세트 — PREREG-LOCK 4장).

사용: python3 -I tests/classify.py <저장소 경로> <출력 폴더>
- 저장소 git 객체만 읽습니다(고정 커밋 C). 네트워크 · API · 운영 모듈 import · .pkl 열기 없음.
- 장부에서는 code · entry · exit 열만 읽습니다. pnl_pct_engine 값은 읽자마자 버립니다(원인 입력 아님).
- entry · exit는 '증거가 있어야 할 자리'를 찾는 열쇠로만 씁니다. 재구성 사건의 값으로 쓰지 않습니다.
"""
import csv, hashlib, io, json, os, subprocess, sys
from datetime import date, datetime, timezone, timedelta

LEDGER_COMMIT = "a61f033ecd16ba0976c955a93bfec70c7463ad53"
LEDGER_PATH = "research-exchange/claude-to-gpt/RULES-0002/results/d1_ledger_ASIS.csv"
LEDGER_SHA = "86c5f56df56d8a7ac5b691152343568d8436f1bea90c10add318bbd9b354209b"
DATA_COMMIT = "5998f42e9acbb0fd3912ae9ebc63c5e1edfb39dc"
BASE_COMMIT = "00b98ab1655c84806357f44f2de6f1509ef1447f"
KERNEL_REF = "63e47a1bc49f183a692e606d0c55191e716e90a2:research-exchange/claude-to-gpt/REPLAY-0001/account_kernel.py"
ORDER = ["MISSING", "UNTRUSTED", "AMBIGUOUS", "DERIVABLE_WITH_LOCKED_RULE", "PRESENT"]   # 앞이 더 나쁨
OK = ("PRESENT", "DERIVABLE_WITH_LOCKED_RULE")
FIELDS = ["F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08", "F09", "F10", "F11", "F12", "F13"]
SPLITLIKE = ("분할", "병합", "증자", "감자", "주식배당", "합병")

# 엔진(B)이 읽는 원천 — nrl.py · lab.py · study.py · caps.py · final_group.py · research/ntools.py @B 정적 읽기 결과
ENGINE_SOURCES = {
    "price-data": "study.load_prices → 일봉 종가(caps.py:100 '한투 수정주가')",
    "volume-data": "lab.RANGE_DIR · ntools.VOL → 거래량 · 고가 · 저가",
    "share-data": "caps → 주식수(시가총액 순위 TOP100)",
    "event-data": "caps · ntools.EVENTS → 공시 목록",
    "loan-data": "caps → 원주가(수정 안 한 종가, 2017~, 일부 종목)",
    "investor-data": "final_group.flow_rows → 투자자별 순매수(teacher · steady)",
    "opinion-data": "study.target_timeline → 목표가(target_cut)",
    "study/features.json": "lab.load → 특징 표(rule.holds · aligned · rank · calm 문턱의 원료)",
}
# TASK 필수지만 엔진은 안 읽는 원천 후보(A2) — 시가가 있는 원천 · 목록 · 조사 자료
EXTRA_SOURCES = {
    "kosdaq-data": "코스닥 일봉(시가 · 고가 · 저가 · 종가)",
    "hourly-data": "시간봉 CSV(연도별)",
    "hourly-kis": "시간봉 CSV(한투, 연도별)",
    "public-data": "조사 자료(since · disclosures)",
    "study/flow_universe.json": "현재 목록",
    "study/kosdaq_codes.json": "현재 목록",
}


def git(repo, *args, binary=False):
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode("utf-8")


class Blobs:
    """git cat-file --batch 로 고정 커밋의 파일을 읽음(없으면 None)."""
    def __init__(self, repo):
        self.p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)
        self.cache = {}

    def get(self, spec):
        if spec in self.cache:
            return self.cache[spec]
        self.p.stdin.write((spec + "\n").encode()); self.p.stdin.flush()
        head = self.p.stdout.readline().decode().split()
        if len(head) < 3 or head[1] == "missing":
            self.cache[spec] = None
            return None
        n = int(head[2]); body = self.p.stdout.read(n); self.p.stdout.read(1)
        self.cache[spec] = body
        return body

    def json(self, commit, path):
        b = self.get(f"{commit}:{path}")
        if b is None:
            return None
        try:
            return json.loads(b.decode("utf-8"))
        except ValueError:
            return "UNPARSABLE"


def load_ledger(text):
    """장부에서 code · entry · exit만 남김(pnl_pct_engine · slots 값은 분류 입력으로 쓰지 않음)."""
    rows = []
    for i, r in enumerate(csv.DictReader(io.StringIO(text))):
        rows.append({"i": i, "code": r["code"], "entry": r["entry"], "exit": r["exit"],
                     "slots_present": r.get("slots") not in (None, "")})
    return rows


def worst(sts):
    return min(sts, key=ORDER.index)


def nextday(days, d):
    import bisect
    k = bisect.bisect_right(days, d)
    return days[k] if k < len(days) else None


def file_history(repo, dirs):
    """경로별 git 추가 시각(첫 등장)과 이 커밋까지 바뀐 횟수 — 선형 1회."""
    out = git(repo, "log", DATA_COMMIT, "--format=@%ct", "--name-only", "--", *dirs)
    first, count, t = {}, {}, None
    for line in out.splitlines():
        if line.startswith("@"):
            t = int(line[1:])
        elif line.strip():
            count[line] = count.get(line, 0) + 1
            first[line] = t           # log는 최신→과거 순이므로 마지막에 남는 값이 첫 등장
    return first, count


def kst_date(ts):
    return datetime.fromtimestamp(ts, timezone(timedelta(hours=9))).strftime("%Y%m%d")


def classify(repo, rows, blobs, hist_first, hist_count):
    C = DATA_COMMIT
    code_cache = {}

    def series(code):
        if code in code_cache:
            return code_cache[code]
        s = {}
        p = blobs.json(C, f"price-data/{code}.json")
        s["price"] = sorted(r[0] for r in p["closes"]) if isinstance(p, dict) and p.get("closes") else None
        v = blobs.json(C, f"volume-data/{code}.json")
        s["volume"] = sorted(r[0] for r in v["날"]) if isinstance(v, dict) and v.get("날") else None
        inv = blobs.json(C, f"investor-data/{code}.json")
        s["investor"] = sorted(r[0] for r in inv["rows"]) if isinstance(inv, dict) and inv.get("rows") else None
        sh = blobs.json(C, f"share-data/{code}.json")
        s["share"] = sorted(r[0] for r in sh["날"]) if isinstance(sh, dict) and sh.get("날") else None
        op = blobs.json(C, f"opinion-data/{code}.json")
        s["opinion"] = sorted(r["date"] for r in op["rows"]) if isinstance(op, dict) and op.get("rows") else None
        ln = blobs.json(C, f"loan-data/{code}.json")
        s["loan"] = sorted(r["date"] for r in ln["rows"] if r.get("종가")) if isinstance(ln, dict) and ln.get("rows") else None
        ev = blobs.json(C, f"event-data/{code}.json")
        s["events"] = sorted((r["date"], r.get("kind") or "", r.get("title") or "") for r in ev["rows"]) \
            if isinstance(ev, dict) and ev.get("rows") is not None else None
        kq = blobs.json(C, f"kosdaq-data/{code}.json")
        s["kq_open"] = sorted(r[0] for r in kq["rows"] if r[1]) if isinstance(kq, dict) and kq.get("rows") else None
        hopen = set()
        for src in ("hourly-data", "hourly-kis"):
            for y in range(2015, 2027):
                b = blobs.get(f"{C}:{src}/{code}/{y}.csv")
                if b:
                    for line in b.decode("utf-8").splitlines():
                        parts = line.split(",")
                        if len(parts) >= 2 and parts[0][:8].isdigit() and parts[0][8:10] == "09" and parts[1] not in ("", "0", "0.0"):
                            hopen.add(parts[0][:8])
        s["hour_open"] = sorted(hopen) or None
        code_cache[code] = s
        return s

    groups = {}
    for r in rows:
        groups.setdefault((r["code"], r["entry"]), []).append(r["i"])
    feat_in_git = blobs.get(f"{C}:study/features.json") is not None
    lab_cost_line = "lab.py:39 COST = 0.25  # 왕복 비용 어림값(%) — 외부 출처 · 적용기간 없음"
    out = []
    for r in rows:
        code, e, x = r["code"], r["entry"], r["exit"]
        s = series(code)
        F, why = {}, {}

        def put(f, st, *reasons):
            F[f] = st
            why[f] = list(reasons)

        # F01 · F02
        put("F01", "DERIVABLE_WITH_LOCKED_RULE", "R1:D1_NEW82_ASIS(d1_diag.py SPECS ASIS)")
        if len(groups[(code, e)]) == 1:
            put("F02", "DERIVABLE_WITH_LOCKED_RULE", "R2:label_only")
        else:
            put("F02", "AMBIGUOUS", "MULTI_ROW_GROUP_NO_TRADE_ID(부분청산/독립 매매 구분 증거 없음)")

        def has(key, d):
            return s[key] is not None and d in s[key]

        def signal_inputs(d):
            st, rs = [], []
            if not feat_in_git:
                st.append("MISSING"); rs.append("FEATURES_TABLE_NOT_IN_GIT(study/features.json; lab.build 재생성은 고정 규칙 아님)")
            for key in ("price", "volume", "investor"):
                if not has(key, d):
                    st.append("MISSING"); rs.append(f"NO_{key.upper()}_ROW_AT_DATE")
                else:
                    st.append("UNTRUSTED"); rs.append(f"{key.upper()}_NO_RECORD_AVAILABLE_AT_VERSION_SOURCE(파일 덮어씀 · fetched 파일 단위)")
            if s["share"] is None:
                st.append("MISSING"); rs.append("NO_SHARE_FILE(시가총액 순위)")
            else:
                st.append("UNTRUSTED"); rs.append("SHARE_DATA_OVERWRITTEN")
            if s["opinion"] is None:
                st.append("MISSING"); rs.append("NO_OPINION_FILE(target_cut)")
            else:
                st.append("UNTRUSTED"); rs.append("OPINION_NO_AVAILABLE_AT")
            return st, rs

        st, rs = signal_inputs(e)
        put("F03", worst(st), *rs)
        # F04: 신호 시점 · available_at · 버전
        st4, rs4 = [], []
        if not has("price", e):
            st4.append("MISSING"); rs4.append("NO_PRICE_ROW_AT_ENTRY")
        else:
            pf = hist_first.get(f"price-data/{code}.json")
            if pf is None or kst_date(pf) > e:
                st4.append("UNTRUSTED"); rs4.append("NO_FIRST_ARRIVAL_VERSION(파일 git 첫 등장이 신호일 뒤 · R5 불성립)")
            else:
                st4.append("UNTRUSTED"); rs4.append("GIT_TIME_NOT_AVAILABILITY(R5 버전 증명 없음)")
        st4.append("UNTRUSTED"); rs4.append("CALM_FULL_PERIOD_THRESHOLD(rule.calm_edge · MEAS-0001 2.1763 · 실행에 확인된 미래참조)")
        st4.append("UNTRUSTED"); rs4.append("SIGNAL_TIME_NOT_RECORDED(엔진은 날짜만 · 계산 시각 없음)")
        put("F04", worst(st4), *rs4)
        # F05: R3 — 다음 거래일 09:00, 입력 일봉이 OK일 때만
        if not has("price", e):
            put("F05", "MISSING", "NO_PRICE_ROW_AT_ENTRY")
        else:
            nd = nextday(s["price"], e)
            if nd is None:
                put("F05", "MISSING", "NO_NEXT_TRADING_DAY_IN_SERIES")
            else:
                put("F05", "UNTRUSTED", "R3_INPUT_PRICE_SERIES_UNTRUSTED",
                    "ENGINE_BUYS_SAME_DAY_CLOSE(lab.run spot=row['i']+delay, delay=0) — R3과 다름")
        # F06: R4 — 다음 거래일 시가 · 원주가 · 조정 표시
        nd = nextday(s["price"], e) if s["price"] else None
        if nd is None:
            put("F06", "MISSING", "NO_NEXT_TRADING_DAY")
        else:
            srcs = [k for k in ("kq_open", "hour_open") if s[k] and nd in s[k]]
            if not srcs:
                put("F06", "MISSING", "NO_OPEN_PRICE_FOR_NEXT_DAY(price-data는 종가만)")
            else:
                put("F06", "UNTRUSTED", "OPEN_FOUND_IN:" + "+".join(srcs),
                    "NO_ADJUSTMENT_FLAG_NO_AVAILABLE_AT_NO_VERSION")
        out.append({"r": r, "F": F, "why": why, "nd": nd})
    # F07: R8 — 앞서 열린 모든 행의 F06 + F13 + NAV, slots는 UNTRUSTED
    opened = sorted(out, key=lambda o: (o["r"]["entry"], o["r"]["i"]))
    prev_bad, acc = {}, "PRESENT"
    for o in opened:              # 그 행까지 진입한 모든 행의 F06 가운데 가장 나쁜 상태(당시 NAV는 앞선 모든 체결이 필요)
        acc = worst([acc, o["F"]["F06"]])
        prev_bad[o["r"]["i"]] = acc
    for o in out:
        r = o["r"]; code, e, x = r["code"], r["entry"], r["exit"]
        s = code_cache[code]
        F, why = o["F"], o["why"]

        def put(f, st, *reasons):
            F[f] = st
            why[f] = list(reasons)
        # F13 비용
        put("F13", "UNTRUSTED", lab_cost_line, "REPLAY-0001 합성 비용률은 SYNTHETIC(관측 아님)")
        chain = prev_bad[r["i"]]
        put("F07", worst([chain, "UNTRUSTED"]), f"R8_CHAIN_F06_WORST={chain}", "SLOTS_FROM_RUN_WITH_KNOWN_LOOKAHEAD",
            "NAV_AT_DECISION_NOT_RECORDED", "F13_UNTRUSTED")
        # F08 청산 신호(자리 찾기만)
        stx, rsx = [], []
        if not feat_in_git:
            stx.append("MISSING"); rsx.append("FEATURES_TABLE_NOT_IN_GIT")
        if not (s["price"] and x in s["price"]):
            stx.append("MISSING"); rsx.append("NO_PRICE_ROW_AT_EXIT")
        else:
            stx.append("UNTRUSTED"); rsx.append("EXIT_RULE_USES_SAME_DAY_CLOSE_NO_AVAILABLE_AT")
        stx.append("UNTRUSTED"); rsx.append("TIER_DEPENDS_ON_CALM_FULL_PERIOD")
        put("F08", worst(stx), *rsx)
        # F09 평가가격 — 보유 기간 날짜가 일봉에 다 있는지 + 조정 여부
        if not s["price"]:
            put("F09", "MISSING", "NO_PRICE_FILE")
        else:
            win = [d for d in s["price"] if e <= d <= x]
            if not win or win[0] != e or win[-1] != x:
                put("F09", "MISSING", "PRICE_SERIES_GAP_IN_HOLDING_WINDOW")
            else:
                raw = s["loan"] is not None and all(d in s["loan"] for d in win)
                put("F09", "UNTRUSTED", "PRICE_DATA_ADJUSTED(caps.py:100) · NO_AS_OF_AVAILABLE_AT_VERSION",
                    "RAW_CLOSE_IN_LOAN_DATA_FULL_WINDOW" if raw else "RAW_CLOSE_NOT_FULL_WINDOW")
        # F10 Universe(t)
        put("F10", "MISSING", "NO_DATED_UNIVERSE_SNAPSHOT(현재 파일 · 현재 목록뿐 — 대체 금지)",
            "ENGINE_UNIVERSE=TOP100_FROM_CURRENT_FILES(생존자 편향)")
        # F11 거래가능성(넷 따로)
        sub = {"halt": "MISSING", "new_listing": "MISSING", "delisting": "MISSING"}
        hl = s["volume"] is not None and e in s["volume"]
        sub["price_limit"] = "UNTRUSTED" if hl else "MISSING"
        put("F11", worst(list(sub.values())), "halt:MISSING(명시 기록 없음 · 거래량 0 추정 금지)",
            "new_listing:MISSING(상장일 명시 기록 없음)", "delisting:MISSING(폐지 기록 없음)",
            "price_limit:" + sub["price_limit"] + "(R6 입력 고가 · 저가 · 원종가 UNTRUSTED)")
        o["F11_sub"] = sub
        # F12 기업행동
        if s["events"] is None:
            put("F12", "MISSING", "NO_EVENT_FILE")
        else:
            hit = [k for (d, k, t) in s["events"] if e <= d <= x and any(w in (k + t) for w in SPLITLIKE)]
            if hit:
                put("F12", "MISSING", "SPLITLIKE_EVENT_IN_WINDOW_NO_RATIO_NO_RECORD_DATE(R7 불성립)",
                    "KERNEL_UNSUPPORTED_CORP_ACTION")
            else:
                put("F12", "UNTRUSTED", "EVENT_LIST_OVERWRITTEN_NO_AVAILABLE_AT(없음을 증명 못함)")
    return out


def summarize(out):
    rows = []
    counts = {f: {s: 0 for s in ORDER} for f in FIELDS}
    complete = 0
    for o in sorted(out, key=lambda o: o["r"]["i"]):
        r = o["r"]
        h = hashlib.sha256(f"{r['i']}|{r['code']}|{r['entry']}".encode()).hexdigest()
        for f in FIELDS:
            counts[f][o["F"][f]] += 1
        ok = all(o["F"][f] in OK for f in FIELDS)
        complete += ok
        rows.append({"row_hash": h, "status": {f: o["F"][f] for f in FIELDS},
                     "reasons": {f: o["why"][f] for f in FIELDS}, "F11_sub": o["F11_sub"], "complete": ok})
    f04 = [o["F"]["F04"] in OK for o in out]
    f06 = [o["F"]["F06"] in OK for o in out]
    if complete == len(out):
        verdict = "RECONSTRUCTIBLE"
    elif not any(a and b for a, b in zip(f04, f06)):
        verdict = "BLOCKED_NEEDS_DATA"
    else:
        verdict = "PARTIAL"
    return rows, counts, complete, verdict


def main(repo, outdir):
    os.makedirs(outdir, exist_ok=True)
    blobs = Blobs(repo)
    lb = blobs.get(f"{LEDGER_COMMIT}:{LEDGER_PATH}")
    sha = hashlib.sha256(lb).hexdigest()
    if sha != LEDGER_SHA:
        raise SystemExit("장부 hash 다름 — 중지")
    rows = load_ledger(lb.decode("utf-8"))
    dirs = ["price-data", "volume-data", "share-data", "event-data", "loan-data", "investor-data", "opinion-data",
            "kosdaq-data", "hourly-data", "hourly-kis"]
    first, count = file_history(repo, dirs)
    out = classify(repo, rows, blobs, first, count)
    lst, counts, complete, verdict = summarize(out)
    list_hash = hashlib.sha256(json.dumps(lst, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    examples = {}
    for f in FIELDS:
        for st in ("AMBIGUOUS", "MISSING", "UNTRUSTED"):
            ex = [x["row_hash"][:10] for x in lst if x["status"][f] == st][:3]
            if ex:
                examples.setdefault(f, {})[st] = ex
    reason_counts = {}
    for x in lst:
        for f in FIELDS:
            for rs in x["reasons"][f]:
                key = f + " " + rs.split("(")[0]
                reason_counts[key] = reason_counts.get(key, 0) + 1
    f11 = {k: {s: sum(1 for x in lst if x["F11_sub"][k] == s) for s in ORDER} for k in lst[0]["F11_sub"]}
    cov = {"task": "REPLAY-0002", "ledger_sha256": sha, "data_commit": DATA_COMMIT, "base_commit": BASE_COMMIT,
           "kernel_ref": KERNEL_REF, "rows": len(lst), "fields": FIELDS,
           "field_status_counts": counts, "denominator": len(lst),
           "rows_complete": complete, "verdict": verdict,
           "rows_with_F04_ok": sum(1 for x in lst if x["status"]["F04"] in OK),
           "rows_with_F06_ok": sum(1 for x in lst if x["status"]["F06"] in OK),
           "F11_sub_counts": f11, "reason_counts": dict(sorted(reason_counts.items())),
           "examples_row_hash10": examples,
           "evidence_kind": {"HISTORICAL_MODEL": len(lst), "OBSERVED_KIS_PAPER": 0},
           "row_list_sha256": list_hash, "row_list": lst,
           "ledger_period": {"entry_min": min(r["entry"] for r in rows), "entry_max": max(r["entry"] for r in rows),
                             "exit_max": max(r["exit"] for r in rows)},
           "codes": len({r["code"] for r in rows})}
    json.dump(cov, open(os.path.join(outdir, "COVERAGE.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              sort_keys=True)
    # 원천 재고(INPUT-INVENTORY)
    inv = []
    codes = sorted({r["code"] for r in rows})
    for d, why in list(ENGINE_SOURCES.items()) + list(EXTRA_SOURCES.items()):
        if d.endswith(".json"):
            b = blobs.get(f"{DATA_COMMIT}:{d}")
            ent = {"source": d, "role": why, "engine_reads": d in ENGINE_SOURCES, "in_git_at_C": b is not None,
                   "blob_sha256": hashlib.sha256(b).hexdigest() if b else None}
        else:
            try:
                tree = git(repo, "rev-parse", f"{DATA_COMMIT}:{d}").strip()
            except subprocess.CalledProcessError:
                tree = None
            files = git(repo, "ls-tree", "-r", "--name-only", DATA_COMMIT, "--", d).split() if tree else []
            fc = [first[p] for p in files if p in first]
            have = sum(1 for c in codes if any(p.startswith(f"{d}/{c}") for p in files))
            ent = {"source": d, "role": why, "engine_reads": d in ENGINE_SOURCES, "in_git_at_C": tree is not None,
                   "tree_sha1": tree, "files": len(files), "ledger_codes_with_file": have, "ledger_codes": len(codes),
                   "git_first_add_kst_min": kst_date(min(fc)) if fc else None,
                   "git_first_add_kst_max": kst_date(max(fc)) if fc else None,
                   "git_versions_total": sum(count.get(p, 0) for p in files)}
        inv.append(ent)
    json.dump({"task": "REPLAY-0002", "data_commit": DATA_COMMIT, "base_commit": BASE_COMMIT, "sources": inv,
               "ledger": {"commit": LEDGER_COMMIT, "path": LEDGER_PATH, "sha256": sha, "rows": len(rows),
                          "columns_read": ["code", "entry", "exit"], "columns_dropped": ["pnl_pct_engine", "slots(값)"]}},
              open(os.path.join(outdir, "INPUT-INVENTORY.raw.json"), "w", encoding="utf-8"), ensure_ascii=False,
              indent=1, sort_keys=True)
    print(verdict, "complete", complete, "list_hash", list_hash)
    return cov


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
