"""research/customer_sample.py 합성 시험(GPT #444 round 5 · 6): 봉인 거절 경로와 정상 경로 · 포함 확률 이론값.

거절해야 하는 것: 미해결 · 끝 영수증 아님 · 빈/형식 틀린 범위 닫기 영수증 · 합의 주소가 형식뿐이거나 댓글 본문에 지문 없음 · 고정 범위 파일 없음 · 종목 집합 불일치 · 목록 ↔ 기록 불일치 ·
원문 보관 없음 · 대조 영수증 없음/지문 다름 · git 커밋 실패 · 커밋 안 된 변경 · 계획 없음 · 기존 봉인 파일.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import customer_sample as s  # noqa: E402

work = Path(tempfile.mkdtemp())
os.chdir(work)
for d in ("customer-data", "research", "dart-events"):
    (work / d).mkdir()
(work / "plan.md").write_text("계획")
manifest = []
for i in range(120):
    code = f"{i:06d}"
    (work / f"dart-events/{code}.json").write_text("{}")
    fil = [{"rcept_no": f"{i:03d}{k}", "rcept_dt": f"{2018 + k}0331", "kind": "원본", "state": "받음",
            "passages": [], "zip_sha256": f"h{i}{k}"} for k in range(1 + i % 4)]
    manifest.append({"code": code, "zips": ",".join(f"{f['rcept_no']}:{f['zip_sha256']}" for f in fil)})
    body = {"code": code, "filings": fil, "list_receipt": {"complete": True},
            "listed_reports": [{"rcept_no": f["rcept_no"]} for f in fil]}
    (work / f"customer-data/{code}.json").write_text(json.dumps(body))
(work / "customer-data/raw-assets.jsonl").write_text("".join(json.dumps(m) + "\n" for m in manifest))
(work / "customer-data/_last_run.json").write_text(json.dumps({"state": "모두 받음"}))
(work / "customer-data/_scope.json").write_text(json.dumps({"schema": "mpos19-scope-v1", "codes": [f"{i:06d}" for i in range(120)]}))


def git(*a):
    return subprocess.run(["git", *a], cwd=work, capture_output=True, text=True)


def receipt(ok=True):
    Path("research/customer_verify_receipt.json").write_text(json.dumps({"ok": ok, "input_sha256": s.input_digest()}))


def commit():
    git("add", "-A"); git("commit", "-qm", "c")


def run(*args):
    sys.argv = ["x", *args]
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = s.main()
    return code, buf.getvalue()


def refused(word):
    code, out = run("--seal", "--plan=plan.md")
    assert code == 2 and word in out and not Path("research/customer_sample.json").exists(), (word, out)


# git 없음 → 거절
receipt(); refused("git 커밋")
git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t"); commit()

# 대조 영수증 실패 → 거절
receipt(False); commit(); refused("원문 대조 영수증")
receipt(); commit()

# 커밋 안 된 변경 → 거절
Path("customer-data/zz.txt").write_text("x"); refused("커밋되지 않은"); Path("customer-data/zz.txt").unlink()

# 미해결 + 끝 영수증 '부분' + 빈 범위 닫기 영수증 → 거절(GPT round 6 재현 경로)
p = Path("customer-data/000000.json"); b = json.loads(p.read_text()); orig = p.read_text()
b["filings"].append({"rcept_no": "000x", "rcept_dt": "20200331", "kind": "원본", "state": "미해결 · HTTP 500 · DART ?"})
b["listed_reports"].append({"rcept_no": "000x"}); p.write_text(json.dumps(b))
Path("customer-data/_last_run.json").write_text(json.dumps({"state": "부분 수집 · 호출 예산"}))
Path("customer-data/_closure.json").write_text("{}")
receipt(); commit(); refused("범위 닫기 영수증 형식")
# 형식은 맞지만 입력 지문이 다름 → 거절
scope_sha = s.sha_file("customer-data/_scope.json")
Path("customer-data/_closure.json").write_text(json.dumps({"schema": "mpos19-closure-v1", "scope_sha256": scope_sha,
                                                         "excluded": [], "input_sha256": "x", "agreed_in": "https://github.com/a"}))
receipt(); commit(); refused("입력 지문")
# 지문 · 제외 목록은 맞지만 합의 주소가 'https://github.com/'뿐(GPT round 7 재현 경로) → 거절
excl = [{"code": "000000", "rcept_no": "000x", "reason": "서버 오류 지속"}]
import hashlib  # noqa: E402
excl_sha = hashlib.sha256(json.dumps(sorted([e["code"], e["rcept_no"], e["reason"]] for e in excl)).encode()).hexdigest()
def closure(url):
    Path("customer-data/_closure.json").write_text(json.dumps({"schema": "mpos19-closure-v1", "scope_sha256": scope_sha, "excluded": excl,
                                                             "input_sha256": s.input_digest(), "agreed_in": url}))
closure("https://github.com/"); receipt(); commit(); refused("합의 근거")
# 주소 형식은 맞지만 댓글 본문에 지문이 없음(가짜 gh) → 거절 · 지문이 모두 있으면 통과 경로
fake = work / "bin"; fake.mkdir()
(fake / "gh").write_text("#!/usr/bin/env bash\ncat \"$GH_FAKE_BODY\"\n"); (fake / "gh").chmod(0o755)
os.environ["PATH"] = f"{fake}:{os.environ['PATH']}"
body_file = work / "body.txt"; os.environ["GH_FAKE_BODY"] = str(body_file)
url = "https://github.com/ppx109-crypto/stock-dash/pull/444#issuecomment-123"
closure(url); body_file.write_text("동의합니다"); receipt(); commit(); refused("합의 근거")
body_file.write_text(f"범위 닫기 동의 {s.input_digest()} {excl_sha} {scope_sha}")
assert "합의 근거" not in " ".join(s.seal_checks()), s.seal_checks()
Path("customer-data/_closure.json").unlink(); p.write_text(orig)
Path("customer-data/_last_run.json").write_text(json.dumps({"state": "모두 받음"}))

# 종목 집합 불일치(고정 범위에 없는 종목 파일) → 거절 · dart-events가 늘어도 고정 범위가 기준
Path("dart-events/999999.json").write_text("{}"); receipt(); commit()
Path("customer-data/999999.json").write_text(json.dumps({"code": "999999", "filings": [], "list_receipt": {"complete": True}, "listed_reports": []}))
receipt(); commit(); refused("종목 집합"); Path("customer-data/999999.json").unlink(); Path("dart-events/999999.json").unlink()
# 고정 범위 파일 없음 → 거절
sc = Path("customer-data/_scope.json").read_text(); Path("customer-data/_scope.json").unlink(); receipt(); commit(); refused("고정 범위")
Path("customer-data/_scope.json").write_text(sc)

# 목록 ↔ 기록 불일치 → 거절
b = json.loads(orig); b["listed_reports"].append({"rcept_no": "zzz"}); p.write_text(json.dumps(b)); receipt(); commit(); refused("목록 ↔ 기록")
p.write_text(orig)

# 원문 보관 없음 → 거절
mf = Path("customer-data/raw-assets.jsonl"); morig = mf.read_text(); mf.write_text("".join(morig.splitlines(True)[1:]))
receipt(); commit(); refused("원문 보관 없음"); mf.write_text(morig)

# 계획 없음 → 거절
receipt(); commit()
code, out = run("--seal"); assert code == 2 and "계획" in out, out

# 정상 → 1회 씀 · 기존 봉인 있으면 거절(바이트 그대로)
code, out = run("--seal", "--plan=plan.md")
assert code == 0 and Path("research/customer_sample.json").exists(), out
sealed = json.loads(Path("research/customer_sample.json").read_text())
assert len(sealed["sealed"]["snapshot_commit"]) == 40 and sealed["sealed"]["input_sha256"] != sealed["final_sha256"]
assert all(abs(r["pi"] - (60 / 120) / r["R_i"]) < 1e-12 for r in sealed["final"])
assert all(abs(r["pi_marginal"] - (40 / 120) / r["R_i"]) < 1e-12 and abs(r["pi_conditional"] - (40 / 60) / r["R_i"]) < 1e-12
           for r in sealed["dev"])
before = Path("research/customer_sample.json").read_bytes()
code, out = run("--seal", "--plan=plan.md")
assert code == 2 and "이미 있음" in out and Path("research/customer_sample.json").read_bytes() == before, out
print("표본 시험 통과")
