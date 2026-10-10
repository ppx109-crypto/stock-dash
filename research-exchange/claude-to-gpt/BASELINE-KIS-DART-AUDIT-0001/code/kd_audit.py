"""BASELINE-KIS-DART-AUDIT-0001 · KIS · OpenDART 읽기 전용 대조(자격이 있을 때만) + 로컬 사전 진단(네트워크 없음).
python3 -E -P kd_audit.py <b2> <b3> <옛 nrl-cache.pkl> <targets 폴더(로컬)> <출력 폴더>

① 자격 확인: 환경변수 KIS_APP_KEY · KIS_APP_SECRET · DART_CRTFC_KEY가 '있는지'만 봄(값 · 길이 · 일부 글자는 읽지도 찍지도 않음).
   없으면 그 API의 호출은 0회 · BLOCKED. 저장소 · 조직 secrets 목록은 열지 않음.
② (자격이 있을 때만 — 이번 실행에서는 해당 없음) 사전등록 §2의 endpoint만 부름. 이 파일에는 호출 코드를 넣지 않았고, 자격이 생기면 사전등록대로 새 커밋으로 넣음.
③ 로컬 사전 진단(공식 응답 아님 · 저장 사본 · 판 불명): 15분봉 4건의 봉 수 · 마지막 봉 시각 · 차이 크기 · 앞뒤 날 비율, 기업행동 8종목의 공시 종류 · 날짜 수.
원가격 · 종목명 · 원시 응답은 내보내지 않음(비율 · 개수 · 해시만)."""
import json, os, pickle, socket, sys, time, hashlib
from pathlib import Path
from collections import Counter

def _blocked(*a, **k):
    raise RuntimeError("네트워크 금지(이번 실행: 자격 없음 · 로컬 진단만)")

B2, B3, OLD, TG, OUT = sys.argv[1:6]
OUT = Path(OUT); (OUT / "evidence").mkdir(parents=True, exist_ok=True)
LOG = []
def say(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print(s, flush=True)

have = {k: bool(os.environ.get(k)) for k in ("KIS_APP_KEY", "KIS_APP_SECRET", "DART_CRTFC_KEY")}
kis_ok, dart_ok = have["KIS_APP_KEY"] and have["KIS_APP_SECRET"], have["DART_CRTFC_KEY"]
say("자격 있음 여부(값 안 읽음)", have)
calls = {"KIS_auth": 0, "KIS_quote": 0, "DART": 0, "retries": 0}
if kis_ok or dart_ok:
    raise SystemExit("자격이 있음: 사전등록 §2 호출 코드를 새 커밋으로 넣은 뒤 실행해야 함(이 판은 호출 코드 없음)")
socket.socket = _blocked; socket.create_connection = _blocked

L = json.load(open(Path(TG, "targets_local_only.json")))
salt = Path(TG, "salt_local_only.txt").read_text().strip()
H = lambda *x: hashlib.sha256((salt + "|" + "|".join(x)).encode()).hexdigest()[:16]
CL = {c: dict(v["rows"]) for c, v in pickle.load(open(OLD, "rb"))[0].items()}
CAL = sorted(CL["005930"])

# ── API 대조 결과(0회) ──
api = {"kis": {"credential_present": kis_ok, "auth_calls": 0, "quote_calls": 0, "status": "BLOCKED: KIS_APP_KEY · KIS_APP_SECRET 이 실행환경에 없음"},
       "dart": {"credential_present": dart_ok, "calls": 0, "status": "BLOCKED: DART_CRTFC_KEY 가 실행환경에 없음"},
       "call_caps": {"KIS(인증 포함)": 500, "DART": 250, "retry_per_request": 2}, "calls_used": calls}
pb = {"denominator_price_records(PR80)": 747, "denominator_codes": 71,
      "queried_ok": 0, "query_unavailable": 747, "stored_eq_official_raw": 0, "stored_eq_official_adjusted": 0, "neither": 0, "UNKNOWN": 747,
      "repo_claim(코드 주장 · 응답 아님)": "price-data는 collect_prices.py → broker_kis.daily(FHKST03010100 · FID_ORG_ADJ_PRC='0' = 수정주가 · broker_kis.py L300 주석)"}

# ── 로컬 사전 진단: 15분봉 4건 ──
def bars(code, day):
    out = []
    for f in sorted(Path(B3, "m15-kis", code).glob("*.csv")):
        for ln in f.read_text(encoding="utf-8").splitlines():
            p = ln.split(",")
            if len(p) == 6 and p[0][:8] == day:
                out.append((p[0][8:], float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    return sorted(out)
cases = []
for c, d in L["mismatch"]:
    b = bars(c, d)
    dc = CL[c][d]
    i = CAL.index(d)
    adj = []
    for dd in (CAL[i - 1], CAL[i + 1]):
        bb = bars(c, dd)
        if bb and CL[c].get(dd):
            adj.append(round(bb[-1][4] / CL[c][dd], 6))
    lo, hi = min(x[3] for x in b), max(x[2] for x in b)
    last = b[-1]
    hint = []
    if len(b) < 26 or last[0] != "1515":
        hint.append("봉 누락 의심")
    if adj and all(abs(r - 1) < 1e-9 for r in adj):
        hint.append("앞뒤 날은 일치 → basis 차이 아님 쪽")
    elif adj and all(abs(r - adj[0]) < 1e-6 and abs(r - 1) > 1e-6 for r in adj):
        hint.append("앞뒤 날도 같은 비율 → basis 차이 의심")
    if last[0] == "1515" and len(b) >= 26:
        hint.append("1515 봉까지 있음 · 15:30 단일가 빠짐 의심(저장소 2026-10-05 탐색 기록과 같은 모양)")
    cases.append({"case": H(c, d), "bars": len(b), "last_bar": last[0], "diff_pct_last_vs_daily": round((last[4] / dc - 1) * 100, 3),
                  "daily_close_within_day_range": lo <= dc <= hi, "daily_close_within_last_bar_range": last[3] <= dc <= last[2],
                  "adjacent_days_ratio_last_over_daily": adj, "local_hint": hint, "final_class": "UNKNOWN(공식 응답 없음)"})
mm = {"denominator": 82, "mismatch": len(cases), "classified_by_official_response": 0,
      "classes_allowed": ["마감 동시호가", "봉 누락", "basis 차이", "timezone/장구분", "기타 UNKNOWN"], "final": {"UNKNOWN": len(cases)},
      "local_prediagnosis(공식 응답 아님)": cases}

# ── 로컬 사전 진단: 기업행동 8종목 ──
CA = ("감자", "분할", "합병", "무상증자", "유상증자", "유무상증자")
kinds, rows_n, corr = Counter(), 0, 0
per = []
for c in L["ca"]:
    rows = json.load(open(Path(B2, "dart-events", f"{c}.json")))["rows"]
    got = [(k, str(r.get("rcept_no", ""))) for k in CA for r in rows.get(k) or [] if "20250918" <= str(r.get("rcept_no", ""))[:8] <= "20261007"]
    kinds.update(k for k, _ in got)
    rows_n += len(got)
    per.append({"code": H(c), "filings": len(got), "kinds": sorted({k for k, _ in got}),
                "in_train(≤20260331)": sum(1 for _, r in got if r[:8] <= "20260331")})
ca = {"denominator_codes": 8, "dart_queried_ok": 0, "query_unavailable": 8, "UNKNOWN": 8,
      "local_stored_copy(저장 사본 · 판 불명 · 접수 시각 없음)": {"filings": rows_n, "by_kind": dict(kinds), "per_code": per},
      "price_link_checked": 0, "note": "효력일 · 정정 연결은 공식 응답 없이 확인 불가. 접수일만으로 같은 날 사용을 PIT로 올리지 않음."}
for name, obj in (("api-coverage", api), ("price-basis-summary", pb), ("corporate-action-summary", ca), ("m15-daily-mismatch-summary", mm)):
    (OUT / "evidence" / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=1))
say("API", json.dumps(api, ensure_ascii=False)); say("가격 basis", json.dumps(pb, ensure_ascii=False))
say("15분봉 4건(로컬)", json.dumps([{k: v for k, v in x.items() if k != "case"} for x in cases], ensure_ascii=False))
say("기업행동(로컬)", json.dumps({k: v for k, v in ca.items() if k != "local_stored_copy(저장 사본 · 판 불명 · 접수 시각 없음)"}, ensure_ascii=False), dict(kinds))
(OUT / "evidence" / "run.log").write_text("\n".join(LOG) + "\n", encoding="utf-8")
say("끝")
