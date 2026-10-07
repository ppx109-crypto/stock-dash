"""DATA-0001 시험 실행기. 사용: python3 -I tests/run_tests.py <DATA-0001 폴더> <결과 json>
- 소켓 연결 차단, KIS/DART/PAPER/DISCORD 환경변수 제거.
- 파일 열기 기록 훅: 열린 경로가 허용 디렉터리(이 폴더 · 파이썬 표준 라이브러리) 밖이면 위반.
- 42 fixture 2회(결정론) + 공통 불변식 I1~I7 + 변이 M01~M21."""
import hashlib, importlib.util, json, os, re, resource, socket, sys, sysconfig, time

for k in list(os.environ):
    if any(w in k.upper() for w in ("KIS", "DART", "PAPER", "DISCORD")):
        del os.environ[k]
def _blocked(*a, **k):
    raise OSError("network blocked in DATA-0001")
socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked

ROOT, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
ALLOWED = sorted({ROOT, os.path.realpath(ROOT), sysconfig.get_paths()["stdlib"], sysconfig.get_paths()["platstdlib"],
                  os.path.realpath(sysconfig.get_paths()["stdlib"])})
OPENED = []
sys.addaudithook(lambda ev, a: OPENED.append(str(a[0])) if ev == "open" and a and isinstance(a[0], str) else None)

spec = importlib.util.spec_from_file_location("validator", os.path.join(ROOT, "validator.py"))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
FX = json.load(open(os.path.join(ROOT, "fixtures", "fixtures.json"), encoding="utf-8"))["fixtures"]
MUTS = {"M01": ["FX03"], "M02": ["FX05", "FX06"], "M03": ["FX07"], "M04": ["FX08"], "M05": ["FX09", "FX10", "FX24"],
        "M06": ["FX11", "FX12", "FX13"], "M07": ["FX14", "FX15"], "M08": ["FX16"], "M09": ["FX17"], "M10": ["FX18"],
        "M11": ["FX19"], "M12": ["FX20"], "M13": ["FX22"], "M14": ["FX25"], "M15": ["FX27"], "M16": ["FX29"],
        "M17": ["FX31"], "M18": ["FX32"], "M19": ["FX33"], "M20": ["FX35"], "M21": ["FX40"]}


def suite(mutations=()):
    out = {}
    for fx in FX:
        try:
            r = V.run_fixture(fx, mutations)
            got = {"rejected": r["rejected"], "duplicates": r["duplicates"], "answers": r["answers"]}
            exp = {"rejected": fx["expect"]["rejected"], "duplicates": fx["expect"]["duplicates"],
                   "answers": [q["expect"] for q in fx["queries"]]}
            out[fx["id"]] = {"pass": got == exp, "got": got, "expected": exp, "accepted": r["accepted"]}
        except Exception as x:          # 변이로 실행이 깨지면 그 fixture가 잡은 것으로 기록
            out[fx["id"]] = {"pass": False, "crash": type(x).__name__ + ": " + str(x)[:120], "accepted": []}
    return out


def invariants(res):
    bad = {f"I{i}": [] for i in range(1, 8)}
    tz = re.compile(r"\+09:00$")
    for fid, r in res.items():
        acc = r["accepted"]
        idx = {(a["record_id"], a["version"]): a for a in acc}
        seen = {}
        for a in acc:
            k = (a["record_id"], a["version"])
            seen.setdefault(k, set()).add(a["normalized_sha256"])
            if a["version"] > 1:
                par = idx.get((a["record_id"], a["version"] - 1))
                if not par or par["record_type"] != a["record_type"] or not a["is_correction"]:
                    bad["I2"].append(fid)
            if a["record_type"] in ("SIGNAL", "ACCOUNT_STATE"):
                lim = a["payload"]["decision_at"] if a["record_type"] == "SIGNAL" else a["as_of"]
                for ref in a["payload"]["inputs"]:
                    rid, _, v = ref.rpartition("@")
                    src = idx.get((rid, int(v)))
                    if src is None or V.datetime.fromisoformat(src["available_at"]) > V.datetime.fromisoformat(lim):
                        bad["I3"].append(fid)
            if V.has_key_deep(a, V.PRIVACY_KEYS):
                bad["I4"].append(fid)
            if a["record_type"] == "PRICE_BAR_RAW" and (a["payload"].get("adjusted") is not False
                                                        or any(x in a["payload"] for x in V.ADJ_KEYS)):
                bad["I5"].append(fid)
            if a["record_type"] == "FILL":
                if a["source_mode"] == "OBSERVED_KIS_PAPER" and not (a["evidence_ref"] and V.EVIDENCE_RE.match(a["evidence_ref"])):
                    bad["I6"].append(fid)
                if a["source_mode"] == "HISTORICAL_MODEL" and a["evidence_ref"]:
                    bad["I6"].append(fid)
            for k in ("as_of", "available_at", "fetched_at", "created_at"):
                if not tz.search(a[k]):
                    bad["I7"].append(fid)
        if any(len(s) > 1 for s in seen.values()):
            bad["I1"].append(fid)
    return {k: sorted(set(v)) for k, v in bad.items()}


def canon(res):
    return hashlib.sha256(json.dumps({k: {"pass": v["pass"], "got": v.get("got"), "crash": v.get("crash")}
                                      for k, v in sorted(res.items())}, sort_keys=True, ensure_ascii=False,
                                     default=str).encode()).hexdigest()


t0 = time.time()
r1, r2 = suite(), suite()
inv = invariants(r1)
# 스키마 실제 실행: 받아진 레코드 전부를 schemas/*.schema.json으로 검사(작은 표준 라이브러리 검사기)
spec2 = importlib.util.spec_from_file_location("schema_check", os.path.join(ROOT, "tests", "schema_check.py"))
SC = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(SC)
SCH = SC.load(os.path.join(ROOT, "schemas"))
schema_errs = {}
n_checked = 0
for fid, v in r1.items():
    for a in v["accepted"]:
        n_checked += 1
        e = SC.check_record(a, SCH)
        if e:
            schema_errs.setdefault(fid, []).append({"record_id": a["record_id"], "errors": e})
# 스키마 검사기가 실제로 잡는지: 거부돼야 할 모양 몇 개를 스키마에 넣어 봄
probe = json.loads(json.dumps(FX[0]["records"][0]))
probes = {"no_tz": dict(probe, available_at="2026-01-05T15:40:00"),
          "adjusted_raw": dict(probe, payload=dict(probe["payload"], adjusted=True)),
          "missing_envelope": {k: v for k, v in probe.items() if k != "ingest_run_id"}}
schema_probe = {k: bool(SC.check_record(v, SCH)) for k, v in probes.items()}
mut = {}
for m, must in MUTS.items():
    rm = suite({m})
    failed = sorted(k for k, v in rm.items() if not v["pass"])
    mut[m] = {"expected_catchers": must, "failed_fixtures": failed,
              "caught_by_expected": sorted(set(must) & set(failed)), "caught": bool(set(must) & set(failed)),
              "crashes": sorted(k for k, v in rm.items() if v.get("crash"))}
secs = time.time() - t0
outside = sorted({p for p in OPENED if not any(os.path.realpath(p).startswith(a + os.sep) or os.path.realpath(p) == a
                                                for a in ALLOWED)})
mods = sorted(n for n, m in sys.modules.items() if getattr(m, "__file__", None)
              and not any(os.path.realpath(m.__file__).startswith(a + os.sep) for a in ALLOWED))
n_pass = sum(v["pass"] for v in r1.values())
doc = {"task": "DATA-0001",
       "validator_sha256": hashlib.sha256(open(os.path.join(ROOT, "validator.py"), "rb").read()).hexdigest(),
       "fixtures_sha256": hashlib.sha256(open(os.path.join(ROOT, "fixtures", "fixtures.json"), "rb").read()).hexdigest(),
       "fixtures_total": len(FX), "fixtures_pass": n_pass,
       "fixtures": {k: {kk: vv for kk, vv in v.items() if kk != "accepted"} for k, v in r1.items()},
       "invariants": inv, "invariants_ok": not any(inv.values()),
       "schema_check": {"schemas": sorted(SCH), "accepted_records_checked": n_checked, "errors": schema_errs,
                        "ok": not schema_errs, "probe_rejected": schema_probe, "probe_ok": all(schema_probe.values()),
                        "engine": "tests/schema_check.py(표준 라이브러리 부분 구현)"},
       "determinism": {"run1": canon(r1), "run2": canon(r2), "same": canon(r1) == canon(r2)},
       "mutations": mut, "mutations_all_caught": all(v["caught"] for v in mut.values()),
       "isolation": {"allowed_dirs": ALLOWED, "opened_outside_allowed": outside, "modules_outside_allowed": mods,
                     "network": "socket connect 차단", "ok": not outside and not mods},
       "budget": {"seconds": round(secs, 2), "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                  "limit_seconds": 300, "limit_mb": 512}}
doc["budget"]["within"] = secs <= 300 and doc["budget"]["max_rss_mb"] <= 512
doc["status"] = "READY" if (n_pass == len(FX) == 42 and doc["invariants_ok"] and doc["mutations_all_caught"]
                            and doc["determinism"]["same"] and doc["isolation"]["ok"]
                            and doc["schema_check"]["ok"] and doc["schema_check"]["probe_ok"]) else "BLOCKED"
doc["scope_note"] = "합성 fixture 검증만. 실제 수집 · 전략 성과 · 모의 준비 · 실전 승인 아님. PAPER_VALIDATION_READY=false"
json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(doc["status"], f"{n_pass}/{len(FX)}", "inv_ok", doc["invariants_ok"], "schema", doc["schema_check"]["ok"], doc["schema_check"]["probe_ok"], n_checked, "mut", sum(v["caught"] for v in mut.values()),
      "/", len(mut), "det", doc["determinism"]["same"], "iso", doc["isolation"]["ok"], doc["budget"])
for k, v in r1.items():
    if not v["pass"]:
        print(" FAIL", k, v.get("crash") or {"got": v["got"], "exp": v["expected"]})
for k, v in mut.items():
    if not v["caught"]:
        print(" MUT-MISS", k, v["failed_fixtures"])
if outside or mods:
    print(" ISO", outside[:5], mods[:5])
