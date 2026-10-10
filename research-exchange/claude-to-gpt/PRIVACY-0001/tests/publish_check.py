"""공개 직전 redaction 자기검사. 사용:
python3 -I tests/publish_check.py <PRIVACY-0001 폴더> <저장소 작업 폴더> <PR 본문 파일> <결과 json> 파일...
대상: 지정 파일들 + PR 본문 + origin/main..HEAD 커밋 메시지. 값은 출력하지 않고 hash · 규칙 · 개수만."""
import hashlib, importlib.util, json, os, re, subprocess, sys
ROOT, REPO, BODY, OUT = (os.path.abspath(x) for x in sys.argv[1:5])
FILES = sys.argv[5:]
def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
G = load("guard", "guard.py"); MZ = load("materialize", os.path.join("tests", "materialize.py"))
FX = json.load(open(os.path.join(ROOT, "fixtures", "fixtures.json"), encoding="utf-8"))
SECRETS = sorted({v for f in FX["attack"] + FX["allow"] for v in MZ.values(f["id"]).values()})
SID = re.compile(r"session_[A-Za-z0-9]{10,}")
g = G.Guard()

def check(name, text, as_json=False):
    fnd = g.scan_text(text)
    if as_json:
        try:
            fnd += g.scan_obj(json.loads(text))
        except ValueError:
            pass
    s = G.summarize(fnd)
    leaks = sum(1 for x in SECRETS if x in text)
    sids = len(SID.findall(text))
    ok = not fnd and not leaks and not sids
    return {"target": name, "sha256": hashlib.sha256(text.encode()).hexdigest(), "rules": s["rules"],
            "count": s["count"], "synthetic_value_hits": leaks, "session_id_like_hits": sids,
            "result": "PASS" if ok else "FAIL"}

res = []
for f in FILES:
    res.append(check(os.path.relpath(os.path.abspath(f), ROOT), open(f, encoding="utf-8").read(), f.endswith(".json")))
res.append(check("PR-BODY", open(BODY, encoding="utf-8").read()))
log = subprocess.run(["git", "-C", REPO, "log", "origin/main..HEAD", "--format=%H%x00%B%x01"], capture_output=True,
                     text=True, check=True).stdout
for chunk in [c for c in log.split("\x01") if c.strip()]:
    h, _, msg = chunk.strip().partition("\x00")
    res.append(check("COMMIT-MESSAGE:" + h[:12], msg))
doc = {"task": "PRIVACY-0001", "targets": res, "all_pass": all(r["result"] == "PASS" for r in res)}
open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
print("ALL_PASS" if doc["all_pass"] else "FAIL", [(r["target"], r["result"], r["count"], r["synthetic_value_hits"], r["session_id_like_hits"]) for r in res if r["result"] != "PASS"])
