"""REPLAY-0002 실행 · 시험(본 실행 1회 + 결정론 재실행 1회 = 결과 실행 2회).

사용: python3 -I tests/run_tests.py <저장소 경로> <REPLAY-0002 폴더>
- 네트워크 차단, KIS/DART/PAPER/DISCORD 환경변수 제거, 파일 열기 기록(.pkl · 운영 상태 파일 열기 0 확인).
- 섞기 · exit 바꾸기 시험은 같은 프로세스에서 분류 함수에 바꾼 입력을 넣음(결과 재실행으로 세지 않음).
"""
import ast, hashlib, importlib.util, json, os, random, resource, socket, sys, time

for k in list(os.environ):
    if any(w in k.upper() for w in ("KIS", "DART", "PAPER", "DISCORD")):
        del os.environ[k]


def _blocked(*a, **k):
    raise OSError("network blocked in REPLAY-0002")


socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
OPENED = []
sys.addaudithook(lambda ev, args: OPENED.append(str(args[0])) if ev == "open" and args and isinstance(args[0], str) else None)

REPO, ROOT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
OUT1, OUT2 = os.path.join(ROOT, "run1"), os.path.join(ROOT, "run2")
spec = importlib.util.spec_from_file_location("classify", os.path.join(ROOT, "tests", "classify.py"))
CL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CL)

t0 = time.time()
cov1 = CL.main(REPO, OUT1)
cov2 = CL.main(REPO, OUT2)
res = {"determinism": {"run1_list_hash": cov1["row_list_sha256"], "run2_list_hash": cov2["row_list_sha256"],
                       "same": cov1["row_list_sha256"] == cov2["row_list_sha256"]}}
b1 = open(os.path.join(OUT1, "COVERAGE.json"), "rb").read()
b2 = open(os.path.join(OUT2, "COVERAGE.json"), "rb").read()
res["determinism"]["coverage_file_sha256_same"] = hashlib.sha256(b1).hexdigest() == hashlib.sha256(b2).hexdigest()

# 누수 시험: pnl_pct_engine 섞기 → 분류 입력 · 결과 같음
blobs = CL.Blobs(REPO)
text = blobs.get(f"{CL.LEDGER_COMMIT}:{CL.LEDGER_PATH}").decode("utf-8")
lines = text.splitlines()
head, body = lines[0], [l.split(",") for l in lines[1:]]
ci = head.split(",").index("pnl_pct_engine")
pn = [r[ci] for r in body]
rnd = random.Random(20261008)
rnd.shuffle(pn)
shuf = "\n".join([head] + [",".join(r[:ci] + [p] + r[ci + 1:]) for r, p in zip(body, pn)]) + "\n"
rows0, rows1 = CL.load_ledger(text), CL.load_ledger(shuf)
first, count = CL.file_history(REPO, ["price-data", "volume-data", "share-data", "event-data", "loan-data",
                                      "investor-data", "opinion-data", "kosdaq-data", "hourly-data", "hourly-kis"])


def lst(rows):
    out = CL.classify(REPO, rows, blobs, first, count)
    return CL.summarize(out)[0]


L0 = lst(rows0)
L1 = lst(rows1)
h = lambda L: hashlib.sha256(json.dumps(L, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
res["pnl_shuffle"] = {"pnl_values_changed_rows": sum(1 for a, b in zip([r[ci] for r in body], pn) if a != b),
                      "loaded_rows_equal": rows0 == rows1, "result_hash_equal": h(L0) == h(L1),
                      "matches_run1": h(L0) == cov1["row_list_sha256"]}
# exit를 entry로 바꿔도 진입 쪽 필드는 같음
rows2 = [dict(r, exit=r["entry"]) for r in rows0]
L2 = lst(rows2)
ENTRY_SIDE = ["F01", "F02", "F03", "F04", "F05", "F06", "F07", "F10", "F11", "F13"]
diff = sum(1 for a, b in zip(L0, L2) for f in ENTRY_SIDE if a["status"][f] != b["status"][f]
           or a["reasons"][f] != b["reasons"][f])
res["exit_swap"] = {"entry_side_fields": ENTRY_SIDE, "entry_side_diffs": diff,
                    "exit_side_changed_rows": sum(1 for a, b in zip(L0, L2) if a != b)}
# 정적 검사: pnl_pct_engine 값을 읽는 코드가 없음(문자열이 첨자 · get 인자로 쓰이지 않음)
tree = ast.parse(open(os.path.join(ROOT, "tests", "classify.py"), encoding="utf-8").read())
bad = []
for node in ast.walk(tree):
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == "pnl_pct_engine":
        bad.append(node.lineno)
    if isinstance(node, ast.Call) and any(isinstance(a, ast.Constant) and a.value == "pnl_pct_engine" for a in node.args):
        bad.append(node.lineno)
res["static_no_pnl_read"] = {"violations": bad, "ok": not bad}
secs = time.time() - t0
pkl = sorted({p for p in OPENED if p.endswith(".pkl")})
ops_state = sorted({p for p in OPENED if any(s in p for s in ("-live/", ".env", "paper-orders"))})
ops_mods = sorted(m for m, v in sys.modules.items() if getattr(v, "__file__", None)
                  and os.path.abspath(v.__file__).startswith("/home/user/stock-dash" + os.sep)
                  and "research-exchange" not in v.__file__)
res["isolation"] = {"network": "socket connect 차단", "pkl_opened": pkl, "ops_state_opened": ops_state,
                    "ops_modules_imported": ops_mods, "ok": not pkl and not ops_state and not ops_mods}
res["budget"] = {"seconds": round(secs, 1), "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                 "limit_seconds": 300, "limit_mb": 512, "result_runs": 2}
res["budget"]["within"] = res["budget"]["seconds"] <= 300 and res["budget"]["max_rss_mb"] <= 512
res["all_ok"] = (res["determinism"]["same"] and res["determinism"]["coverage_file_sha256_same"]
                 and res["pnl_shuffle"]["loaded_rows_equal"] and res["pnl_shuffle"]["result_hash_equal"]
                 and res["exit_swap"]["entry_side_diffs"] == 0 and res["static_no_pnl_read"]["ok"]
                 and res["isolation"]["ok"])
json.dump(res, open(os.path.join(ROOT, "TEST-RESULT.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
