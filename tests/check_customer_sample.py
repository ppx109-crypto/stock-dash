"""research/customer_sample.py 합성 시험: 봉인 조건(미해결 · 끝 영수증 · 기존 봉인 덮어쓰기 거절) · 포함 확률 이론값 · 개발 주변/조건부 확률."""
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import customer_sample as s  # noqa: E402

work = Path(tempfile.mkdtemp())
os.chdir(work)
(work / "customer-data").mkdir()
(work / "research").mkdir()
(work / "plan.md").write_text("계획")
(work / "customer-data/raw-assets.jsonl").write_text("")
for i in range(120):
    n = 1 + i % 4
    fil = [{"rcept_no": f"{i:03d}{k}", "rcept_dt": f"{2018 + k}0331", "kind": "원본", "state": "받음", "passages": []} for k in range(n)]
    if i == 0:
        fil.append({"rcept_no": "000x", "rcept_dt": "20200331", "kind": "원본", "state": "미해결 · HTTP 500 · DART ?"})
    (work / f"customer-data/{i:06d}.json").write_text(json.dumps({"code": f"{i:06d}", "filings": fil, "list_receipt": {"complete": True}}))


def run(*args):
    sys.argv = ["x", *args]
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = s.main()
    return code, buf.getvalue()


(work / "customer-data/_last_run.json").write_text(json.dumps({"state": "부분 수집 · 호출 예산"}))
code, out = run("--seal", "--plan=plan.md")
assert code == 2 and "모두 받음" in out and "미해결 1건" in out and not Path("research/customer_sample.json").exists(), out
(work / "customer-data/_last_run.json").write_text(json.dumps({"state": "모두 받음"}))
code, out = run("--seal", "--plan=plan.md")
assert code == 2 and "미해결 1건" in out, out
p = work / "customer-data/000000.json"
b = json.loads(p.read_text()); b["filings"] = [f for f in b["filings"] if not f["state"].startswith("미해결")]; p.write_text(json.dumps(b))
code, out = run("--seal")
assert code == 2 and "계획" in out, out
code, out = run("--seal", "--plan=plan.md")
assert code == 0 and Path("research/customer_sample.json").exists(), out
sealed = json.loads(Path("research/customer_sample.json").read_text())
assert sealed["sealed"]["input_sha256"] != sealed["final_sha256"]
assert all(abs(r["pi"] - (60 / 120) / r["R_i"]) < 1e-12 for r in sealed["final"])
assert all(abs(r["pi_marginal"] - (40 / 120) / r["R_i"]) < 1e-12 and abs(r["pi_conditional"] - (40 / 60) / r["R_i"]) < 1e-12 for r in sealed["dev"])
before = Path("research/customer_sample.json").read_bytes()
code, out = run("--seal", "--plan=plan.md")
assert code == 2 and "이미 있음" in out and Path("research/customer_sample.json").read_bytes() == before, out
print("표본 시험 통과")
