"""전체 시험 차이 검사(BOOST-0001-D · GPT 구현 검토 6705430244 §2-C) — 같은 기계에서 기준 판과 지금 판의 실패 · 오류 시험 이름 집합을 견줌.

- 기준(base) = 주어진 커밋(PR이면 PR의 base · 아니면 main과의 merge-base)을 git worktree로 따로 꺼내 그 안에서 돌림.
- 지금(head) = 이 저장소 작업 폴더 그대로(작업 흐름에서는 받은 커밋 · 로컬에서는 커밋 안 한 고침까지 포함).
- 각 판에서 `python -m unittest discover -s tests`와 같은 셈(작업 폴더 = 그 판 · sys.path[0] = '' · start = tests)으로 모든 시험을 돌리고
  실패(failure) · 오류(error · 불러오기 실패 포함) · 뜻밖의 통과(unexpected success) 시험 이름을 모음(건너뜀 · 예상 실패는 뺌).
- 판정: **지금 실패 집합 ⊆ 기준 실패 집합**이면 green(끝 값 0) · 새 실패가 하나라도 있으면 red(끝 값 1) ·
  어느 한 판이라도 시험을 끝까지 못 돌리면 red(끝 값 1 · 견줄 수 없음 = 통과 아님).
- 남기는 것(--out 폴더 · 자유 문장 아님 · 목록): base.json · head.json(시험 수 · 실패 · 오류 이름) · diff.json(두 집합 · 새 실패 · 고쳐진 것 ·
  판정) · summary.md(같은 목록) — GITHUB_STEP_SUMMARY가 있으면 summary.md를 거기에도 덧붙임.
사용: python tools/test_diff.py --base <커밋> --out <폴더> [--start tests] [--timeout 초]
키 · 증권사를 부르지 않음(시험은 가짜 · 고정 자료).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = r"""
import json, sys, unittest
out, start = sys.argv[1], sys.argv[2]
suite = unittest.TestLoader().discover(start)
res = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
body = {"tests_run": res.testsRun,
        "failures": sorted({t.id() for t, _ in res.failures}),
        "errors": sorted({t.id() for t, _ in res.errors}),
        "unexpected_successes": sorted({t.id() for t in res.unexpectedSuccesses}),
        "skipped": len(res.skipped), "expected_failures": len(res.expectedFailures)}
with open(out, "w", encoding="utf-8") as f:
    json.dump(body, f, ensure_ascii=False, indent=1)
"""


def _env():
    """시험을 돌릴 환경 — 바깥 GIT_* 값(작업 흐름의 git 설정)에 끌려가지 않게 뺌."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=600, env=_env())


def run_suite(root, out_json, start="tests", timeout=3600):
    """root 판에서 모든 시험을 돌려 실패 · 오류 이름을 모음 → 본문(dict) 또는 None(끝까지 못 돌림)."""
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    if out_json.exists():
        out_json.unlink()
    try:
        r = subprocess.run([sys.executable, "-c", RUNNER, str(out_json), start], cwd=str(root), capture_output=True, text=True,
                           timeout=timeout, env=_env())
    except subprocess.TimeoutExpired:
        print(f"⚠️ {root}: {timeout}초 안에 시험이 끝나지 않음")
        return None
    try:
        body = json.loads(out_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print(f"⚠️ {root}: 시험 결과 파일이 없음(끝 값 {r.returncode}) · {(r.stderr or '')[-500:]}")
        return None
    body["returncode"] = r.returncode
    return body


def failed_set(body):
    """실패 · 오류 · 뜻밖의 통과 이름 집합."""
    return set(body.get("failures") or []) | set(body.get("errors") or []) | set(body.get("unexpected_successes") or [])


def compare(base_bad, head_bad):
    """→ {"green", "base_failed", "head_failed", "new_failures", "fixed"} (모두 정렬 목록)."""
    base_bad, head_bad = set(base_bad), set(head_bad)
    new = sorted(head_bad - base_bad)
    return {"green": not new, "base_failed": sorted(base_bad), "head_failed": sorted(head_bad), "new_failures": new,
            "fixed": sorted(base_bad - head_bad)}


def summary_md(diff, meta):
    """요약(목록만)."""
    lines = ["## 전체 시험 차이 검사(BOOST-0001-D)", "",
             f"- 판정: {'green(지금 실패 ⊆ 기준 실패)' if diff['green'] else 'red(새 실패 있음)'}",
             f"- 기준: `{meta.get('base')}` · 시험 {meta.get('base_tests')}개",
             f"- 지금: `{meta.get('head')}`{' (커밋 안 한 고침 포함)' if meta.get('head_dirty') else ''} · 시험 {meta.get('head_tests')}개", ""]
    for title, key in (("기준 실패 · 오류", "base_failed"), ("지금 실패 · 오류", "head_failed"), ("새 실패(지금에만)", "new_failures"),
                       ("고쳐진 것(기준에만)", "fixed")):
        lines.append(f"### {title} ({len(diff[key])})")
        lines += [f"- `{x}`" for x in diff[key]] or ["- (없음)"]
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="기준 판과 지금 판의 실패 · 오류 시험 집합 견주기")
    ap.add_argument("--base", required=True, help="기준 커밋(PR base 또는 merge-base)")
    ap.add_argument("--out", required=True, help="결과 폴더")
    ap.add_argument("--start", default="tests")
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--root", default=None, help="지금 판 폴더(기본: 이 저장소)")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve() if a.root else ROOT
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    got = git(["rev-parse", "--verify", f"{a.base}^{{commit}}"], root)
    if got.returncode != 0:
        print(f"⚠️ 기준 커밋을 찾지 못함 · {a.base}")
        return 1
    base = got.stdout.strip()
    head = git(["rev-parse", "HEAD"], root).stdout.strip()
    dirty = bool(git(["status", "--porcelain", "--untracked-files=no"], root).stdout.strip())
    tmp = Path(tempfile.mkdtemp(prefix="test-diff-"))
    tree = tmp / "base"
    try:
        add = git(["worktree", "add", "--detach", "--quiet", str(tree), base], root)
        if add.returncode != 0:
            print(f"⚠️ 기준 판을 꺼내지 못함 · {add.stderr.strip()[:300]}")
            return 1
        print(f"기준 판 {base[:12]} 시험 중…")
        base_body = run_suite(tree, out / "base.json", a.start, a.timeout)
    finally:
        git(["worktree", "remove", "--force", str(tree)], root)
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"지금 판 {head[:12]}{' + 커밋 안 한 고침' if dirty else ''} 시험 중…")
    head_body = run_suite(root, out / "head.json", a.start, a.timeout)
    if base_body is None or head_body is None:
        diff = {"green": False, "why": "한 판이라도 시험을 끝까지 못 돌려 견줄 수 없음", "base_ran": base_body is not None,
                "head_ran": head_body is not None}
        (out / "diff.json").write_text(json.dumps(diff, ensure_ascii=False, indent=1), encoding="utf-8")
        print("⚠️ red · " + diff["why"])
        return 1
    diff = compare(failed_set(base_body), failed_set(head_body))
    meta = {"base": base, "head": head, "head_dirty": dirty, "base_tests": base_body["tests_run"], "head_tests": head_body["tests_run"]}
    diff.update(meta)
    (out / "diff.json").write_text(json.dumps(diff, ensure_ascii=False, indent=1), encoding="utf-8")
    md = summary_md(diff, meta)
    (out / "summary.md").write_text(md + "\n", encoding="utf-8")
    step = os.getenv("GITHUB_STEP_SUMMARY")
    if step:
        try:
            with open(step, "a", encoding="utf-8") as f:
                f.write(md + "\n")
        except OSError:
            print("⚠️ 작업 요약에 쓰지 못함(결과 폴더에는 있음)")
    print(md)
    return 0 if diff["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
