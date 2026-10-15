import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "research"))
import rxkit as R  # noqa: E402


class RxKit(unittest.TestCase):
    def test_lint_catches_zero_as_missing_and_dict_dup(self):
        tmp_path = Path(tempfile.mkdtemp())
        p = tmp_path / "j.py"
        p.write_text("a = (x or -1e9) > (y or -1e9)\n"
                     "b = (t or -1) > 0\n"
                     "c = name or other\n"
                     "e = dict(sysenv(), **ENV, Z_D1_LED=str(led))\n"
                     "f = x or -1e9  # 허용\n", encoding="utf-8")
        hits = R.lint([str(p)], allow=("j.py:5",))
        assert any("j.py:1" in h for h in hits)
        assert any("j.py:2" in h for h in hits)
        assert not any("j.py:3" in h for h in hits)
        assert any("j.py:4" in h and "dict" in h for h in hits)
        assert not any("j.py:5" in h for h in hits)

    def test_dag_runs_after_and_skips_on_fail(self):
        tmp_path = Path(tempfile.mkdtemp())
        py = sys.executable
        jobs = {
            "a": dict(cmd=[py, "-c", "open('a.txt','w').write('1')"], cwd=str(tmp_path), out=str(tmp_path / "a.log")),
            "b": dict(cmd=[py, "-c", "assert open('a.txt').read()=='1'"], cwd=str(tmp_path), out=str(tmp_path / "b.log"), after=["a"]),
            "bad": dict(cmd=[py, "-c", "raise SystemExit(3)"], cwd=str(tmp_path), out=str(tmp_path / "x.log")),
            "c": dict(cmd=[py, "-c", "pass"], cwd=str(tmp_path), out=str(tmp_path / "c.log"), after=["bad"]),
        }
        rc = R.run_dag(jobs, workers=2, log=lambda *_: None, poll=0.05)
        assert rc == {"a": 0, "b": 0, "bad": 3, "c": None}

    def test_receipt_binds_only_stage_code(self):
        tmp_path = Path(tempfile.mkdtemp())
        code_a = tmp_path / "door.py"
        code_a.write_text("x=1")
        other = tmp_path / "judge.py"
        other.write_text("y=1")
        out = tmp_path / "led.json"
        out.write_text("[]")
        rp = tmp_path / "receipt_build.json"
        code = R.stage_code([str(code_a)])
        assert R.write_receipt(str(rp), code, {"G": {"판정": "PASS", "파일": {str(out): R.sha(str(out))}}}) == []
        other.write_text("y=2")                                     # 그 단계와 무관한 코드 고침 → 영수증 그대로 유효
        assert R.check_receipt(str(rp), R.stage_code([str(code_a)])) == []
        code_a.write_text("x=2")                                    # 그 단계 코드 고침 → 무효
        assert "그 단계 코드가 바뀜" in R.check_receipt(str(rp), R.stage_code([str(code_a)]))
        out.write_text("[1]")                                       # 결과 파일 바뀜 → 무효
        assert any("파일" in w for w in R.check_receipt(str(rp), code))
        json.loads(rp.read_text())

    def test_dry_catches_builder_error_and_bad_env(self):
        def broken():
            return {"j": dict(cmd=["x"], env=dict(**{"K": "1"}, K="2"))}

        def badenv():
            return {"j": dict(cmd=["x"], env={"K": 1})}

        def ok():
            return {"j": dict(cmd=["x"], env={"K": "1"})}
        bad = R.dry({"broken": broken, "badenv": badenv, "ok": ok})
        assert any(b.startswith("broken: 일감 만들기 실패") for b in bad)
        assert any("badenv/j" in b for b in bad)
        assert not any(b.startswith("ok") for b in bad)

    def test_dry_smoke_timeout_and_missing_output_fail(self):
        py = sys.executable
        tmp = Path(tempfile.mkdtemp())
        bad = R.dry({}, smoke={"slow": dict(cmd=[py, "-c", "import time; time.sleep(5)"]),
                               "noout": dict(cmd=[py, "-c", "pass"], expect=[str(tmp / "x.csv")]),
                               "good": dict(cmd=[py, "-c", "open(%r,'w').write('1')" % str(tmp / "y.csv")], expect=[str(tmp / "y.csv")])}, timeout=1)
        assert any("slow" in b and "미완료" in b for b in bad)
        assert any("noout" in b for b in bad)
        assert not any("good" in b for b in bad)

    def test_review_prompt_mentions_checklist(self):
        t = R.review_prompt("/x/MPOS-0009")
        assert "RESEARCH-SELF-UPGRADE.md" in t and "마른 실행" in t


if __name__ == "__main__":
    unittest.main()
