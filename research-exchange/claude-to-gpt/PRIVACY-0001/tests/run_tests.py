"""PRIVACY-0001 시험 실행기. 사용: python3 -I tests/run_tests.py <PRIVACY-0001 폴더> <결과 json>
공격 34 · 허용 12 · 결정론 2회 · mutant 9 · 독립 redaction 검사 · 격리(허용 디렉터리 · 쓰기 위치 · 소켓 · 환경변수)."""
import hashlib, importlib.util, json, os, resource, socket, sys, sysconfig, time
STARTUP_MODS = set(sys.modules)
os.environ.clear()                       # 이 프로세스 안 환경변수를 비움(바깥 셸은 그대로)
def _blocked(*a, **k):
    raise OSError("network blocked in PRIVACY-0001")
socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
ROOT, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
ALLOWED = sorted({ROOT, sysconfig.get_paths()["stdlib"], sysconfig.get_paths()["platstdlib"]})
OPENS = []
def _hook(ev, a):
    if ev == "open" and a and isinstance(a[0], str):
        OPENS.append((a[0], str(a[1]) if len(a) > 1 else "r"))
sys.addaudithook(_hook)

def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
G = load("guard", "guard.py")
MZ = load("materialize", os.path.join("tests", "materialize.py"))
FX = json.load(open(os.path.join(ROOT, "fixtures", "fixtures.json"), encoding="utf-8"))
ALL = FX["attack"] + FX["allow"]
SECRETS = sorted({v for f in ALL for v in MZ.values(f["id"]).values()})


def run_suite(mut=()):
    g = G.Guard(mut)
    res = {}
    for f in ALL:
        data, _ = MZ.materialize(f)
        fnd = g.scan_text(data) if f["kind"] == "text" else g.scan_obj(data)
        rules = sorted({x["rule"] for x in fnd})
        res[f["id"]] = {"rules": rules, "expected": f["expect_rules"], "pass": rules == f["expect_rules"],
                        "self_check": g.self_check(fnd), "findings": fnd}
    return res


def redaction_leaks(res):
    blob = json.dumps(res, ensure_ascii=False)
    return sum(1 for s in SECRETS if s in blob)


def public_view(res):
    return {k: {"rules": v["rules"], "expected": v["expected"], "pass": v["pass"], "self_check": v["self_check"],
                "count": len(v["findings"])} for k, v in res.items()}


def canon(res):
    return hashlib.sha256(json.dumps(public_view(res), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


t0 = time.time()
r1, r2 = run_suite(), run_suite()
atk = [f["id"] for f in FX["attack"]]; alw = [f["id"] for f in FX["allow"]]
mut = {}
for m, must in FX["mutants"].items():
    rm = run_suite({m})
    failed = sorted(k for k, v in rm.items() if not v["pass"])
    leaks = redaction_leaks(rm)
    self_fail = sorted(k for k, v in rm.items() if not v["self_check"])
    hit = sorted(set(must) & set(failed))
    if "REDACTION" in must and leaks:
        hit.append("REDACTION")
    mut[m] = {"expected_catchers": must, "caught_by": hit, "caught": bool(hit), "failed_fixtures": failed,
              "redaction_leak_count": leaks, "gate_self_check_failed": self_fail}
secs = time.time() - t0
inside = lambda p: any(os.path.realpath(p) == a or os.path.realpath(p).startswith(a + os.sep) for a in ALLOWED)
outside_reads = sorted({p for p, m in OPENS if not inside(p)})
bad_writes = sorted({p for p, m in OPENS if any(c in m for c in "wax+") and not os.path.realpath(p).startswith(ROOT)})
new_mods = sorted(n for n, mm in sys.modules.items() if n not in STARTUP_MODS and getattr(mm, "__file__", None)
                  and not inside(mm.__file__))
doc = {"task": "PRIVACY-0001",
       "guard_sha256": hashlib.sha256(open(os.path.join(ROOT, "guard.py"), "rb").read()).hexdigest(),
       "fixtures_sha256": hashlib.sha256(open(os.path.join(ROOT, "fixtures", "fixtures.json"), "rb").read()).hexdigest(),
       "attack_total": len(atk), "attack_blocked_exact": sum(r1[i]["pass"] for i in atk),
       "allow_total": len(alw), "allow_false_positive": sum(1 for i in alw if not r1[i]["pass"]),
       "fixtures": public_view(r1),
       "gate_self_check_all": all(v["self_check"] for v in r1.values()),
       "redaction_leaks_baseline": redaction_leaks(r1),
       "determinism": {"run1": canon(r1), "run2": canon(r2), "same": canon(r1) == canon(r2)},
       "mutants": mut, "mutants_caught": sum(v["caught"] for v in mut.values()), "mutants_total": len(mut),
       "isolation": {"allowed_dirs": ["<PRIVACY-0001>" if a == ROOT else "<python-stdlib>" for a in ALLOWED],
                     "reads_outside_allowed": len(outside_reads), "writes_outside_folder": len(bad_writes),
                     "new_modules_outside_allowed": new_mods, "env_cleared": True, "network": "socket connect 차단"},
       "budget": {"seconds": round(secs, 3), "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}}
iso = doc["isolation"]
iso["ok"] = iso["reads_outside_allowed"] == 0 and iso["writes_outside_folder"] == 0 and not new_mods
doc["status"] = "READY" if (doc["attack_blocked_exact"] == len(atk) and doc["allow_false_positive"] == 0
                            and doc["mutants_caught"] == len(mut) and doc["determinism"]["same"]
                            and doc["redaction_leaks_baseline"] == 0 and doc["gate_self_check_all"] and iso["ok"]) else "BLOCKED"
doc["scope_note"] = "합성 공개 차단 게이트 검증만. 과거 이력 청정 · 실제 자료 · 전략 · PAPER_VALIDATION_READY · 실전 승인 아님"
text = json.dumps(doc, ensure_ascii=False, indent=1)
text = text.replace(ROOT, "<PRIVACY-0001>")
assert not any(s in text for s in SECRETS), "결과에 합성 값이 들어감"
open(OUT, "w", encoding="utf-8").write(text)
print(doc["status"], "attack", doc["attack_blocked_exact"], "/", len(atk), "allowFP", doc["allow_false_positive"],
      "mut", doc["mutants_caught"], "/", len(mut), "det", doc["determinism"]["same"], "iso", iso, doc["budget"])
for k, v in r1.items():
    if not v["pass"]:
        print(" FAIL", k, v["rules"], "기대", v["expected"])
for k, v in mut.items():
    if not v["caught"]:
        print(" MUT-MISS", k, v["failed_fixtures"])
