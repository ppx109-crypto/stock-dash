"""전체 시험 차이 검사(BOOST-0001-D · GPT 구현 검토 6705430244 §2-C) — 같은 기계에서 기준 판과 지금 판의 실패 · 오류 시험 이름 집합을 견줌.

- 기준(base) = 주어진 커밋(PR이면 PR의 base · 아니면 main과의 merge-base)을 git worktree로 따로 꺼내 그 안에서 돌림.
- 지금(head) = 이 저장소 작업 폴더 그대로(작업 흐름에서는 받은 커밋 · 로컬에서는 커밋 안 한 고침까지 포함).
- 각 판에서 `python -m unittest discover -s tests`와 같은 셈(작업 폴더 = 그 판 · sys.path[0] = '' · start = tests)으로 모든 시험을 돌리고
  실패(failure) · 오류(error · 불러오기 실패 포함) · 뜻밖의 통과(unexpected success) 시험 이름을 모음(건너뜀 · 예상 실패는 뺌).
- 판정: **지금 실패 집합 ⊆ 기준 실패 집합**이고 아래 불변식이 모두 맞으면 green(끝 값 0) · 하나라도 어기면 red(끝 값 1) ·
  어느 한 판이라도 시험을 끝까지 못 돌리면 red(끝 값 1 · 견줄 수 없음 = 통과 아님).
- 불변식(GPT 구현 검토 판 2 · 6708390773 §2-B — 시험을 지우거나 건너뛰기를 늘려 green이 되는 길을 막음):
  지금 돌린 시험 수 ≥ 기준 · 모은 시험 수 ≥ 기준 · 건너뛴 수 ≤ 기준 · 기준에 있던 시험 이름이 지금 빠짐 0 · 기준에서 안 건너뛰던 시험이
  지금 건너뜀(새로 건너뜀) 0.
- 남기는 것(--out 폴더 · 자유 문장 아님 · 목록): base.json · head.json(시험 수 · 모은 시험 이름 · 실패 · 오류 · 건너뜀 이름) ·
  diff.json(두 집합 · 새 실패 · 고쳐진 것 · 불변식 · 빠진 시험 · 새로 건너뜀 · 판정) · summary.md(같은 목록) — GITHUB_STEP_SUMMARY가 있으면
  summary.md를 거기에도 덧붙임.
- D 묶음 고정(--bundle 고정 파일): 고정 파일(tests/fixtures/boost_d_required_tests.json)의 모듈만 돌려 **모은 시험 이름 = 고정 목록 ·
  개수 = 고정 개수 · 목록 지문 = 고정 지문 · 실패 · 오류 · 건너뜀 0 · 이 도구 sha256 = 고정 값**일 때만 green. 필수 시험 파일이나 이 도구를
  고치면 고정 파일도 함께 다시 써야 함(--pin · 모두 통과할 때만 씀) → 지운 시험 · 바꾼 도구가 고정 파일 차이로 검토에 드러남.
사용: python tools/test_diff.py --base <커밋> --out <폴더> [--start tests] [--timeout 초]
      python tools/test_diff.py --bundle <고정 파일> --out <폴더>        (D 묶음 · 필수 job)
      python tools/test_diff.py --pin <고정 파일> [--modules "모듈 …"]    (고정 파일 다시 쓰기)
키 · 증권사를 부르지 않음(시험은 가짜 · 고정 자료).
"""
import argparse
import hashlib
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
out, start, mode, verbosity = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
loader = unittest.TestLoader()
suite = loader.discover(start) if mode == "discover" else loader.loadTestsFromNames([x for x in start.split(",") if x])


def flat(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            yield from flat(t)
        else:
            yield t


ids = sorted(t.id() for t in flat(suite))          # 돌리기 전에 모음(돌린 뒤에는 suite가 시험을 비움)
res = unittest.TextTestRunner(stream=sys.stderr, verbosity=verbosity).run(suite)
body = {"tests_run": res.testsRun, "collected": len(ids), "ids": ids,
        "failures": sorted({t.id() for t, _ in res.failures}),
        "errors": sorted({t.id() for t, _ in res.errors}),
        "unexpected_successes": sorted({t.id() for t in res.unexpectedSuccesses}),
        "skipped": len(res.skipped), "skipped_ids": sorted({t.id() for t, _ in res.skipped}),
        "expected_failures": len(res.expectedFailures)}
with open(out, "w", encoding="utf-8") as f:
    json.dump(body, f, ensure_ascii=False, indent=1)
"""
PIN_KIND = "boost-d-required-tests/1"
COLLECT = r"""
import json, sys, unittest
out, names = sys.argv[1], [x for x in sys.argv[2].split(",") if x]


def flat(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            yield from flat(t)
        else:
            yield t


with open(out, "w", encoding="utf-8") as f:
    json.dump(sorted(t.id() for t in flat(unittest.TestLoader().loadTestsFromNames(names))), f, ensure_ascii=False)
"""


def _env():
    """시험을 돌릴 환경 — 바깥 GIT_* 값(작업 흐름의 git 설정)에 끌려가지 않게 뺌 · 바이트코드 캐시를 쓰지 않음(같은 크기 파일을
    1초 안에 고쳐 쓰면 옛 캐시를 읽는 일을 줄임)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=600, env=_env())


def run_suite(root, out_json, start="tests", timeout=3600, names=None, verbosity=1):
    """root 판에서 시험을 돌려 모은 이름 · 실패 · 오류 · 건너뜀을 모음 → 본문(dict) 또는 None(끝까지 못 돌림).
    names(모듈 이름 목록)를 주면 discover 대신 그 모듈만(D 묶음)."""
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    if out_json.exists():
        out_json.unlink()
    mode, arg = ("names", ",".join(names)) if names else ("discover", start)
    try:
        r = subprocess.run([sys.executable, "-c", RUNNER, str(out_json), arg, mode, str(int(verbosity))], cwd=str(root),
                           capture_output=True, text=True, timeout=timeout, env=_env())
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


def collect_ids(root, names, timeout=600):
    """root 판에서 모듈(names)의 시험 이름만 모음(돌리지 않음 · 따로 띄운 python) → 정렬 목록 또는 None(못 모음)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "ids.json"
        try:
            subprocess.run([sys.executable, "-c", COLLECT, str(out), ",".join(names)], cwd=str(root), capture_output=True, text=True,
                           timeout=timeout, env=_env())
            return json.loads(out.read_text(encoding="utf-8"))
        except (subprocess.TimeoutExpired, OSError, ValueError):
            return None


def failed_set(body):
    """실패 · 오류 · 뜻밖의 통과 이름 집합."""
    return set(body.get("failures") or []) | set(body.get("errors") or []) | set(body.get("unexpected_successes") or [])


def compare(base_bad, head_bad):
    """→ {"green", "base_failed", "head_failed", "new_failures", "fixed"} (모두 정렬 목록)."""
    base_bad, head_bad = set(base_bad), set(head_bad)
    new = sorted(head_bad - base_bad)
    return {"green": not new, "base_failed": sorted(base_bad), "head_failed": sorted(head_bad), "new_failures": new,
            "fixed": sorted(base_bad - head_bad)}


def invariants(base, head):
    """시험 지우기 · 건너뛰기 늘리기 막기(판 2 §2-B) → {"invariants": {이름: 맞음?}, "invariants_ok", "missing_tests", "newly_skipped", 수 …}.
    본문에 ids · skipped_ids가 없으면(옛 꼴) 그 불변식은 맞지 않음으로 봄(견줄 수 없음 = 통과 아님)."""
    b_ids, h_ids = base.get("ids"), head.get("ids")
    b_skip, h_skip = base.get("skipped_ids"), head.get("skipped_ids")
    have = all(isinstance(x, list) for x in (b_ids, h_ids, b_skip, h_skip))
    missing = sorted(set(b_ids) - set(h_ids)) if have else []
    newly = sorted(set(h_skip) - set(b_skip)) if have else []
    checks = {"tests_run": int(head.get("tests_run") or 0) >= int(base.get("tests_run") or 0),
              "collected": have and len(h_ids) >= len(b_ids),
              "skipped": int(head.get("skipped") or 0) <= int(base.get("skipped") or 0),
              "missing_tests": have and not missing,
              "newly_skipped": have and not newly}
    return {"invariants": checks, "invariants_ok": all(checks.values()), "missing_tests": missing, "newly_skipped": newly,
            "base_collected": len(b_ids) if have else None, "head_collected": len(h_ids) if have else None,
            "base_skipped": base.get("skipped"), "head_skipped": head.get("skipped")}


def ids_sha(ids):
    """시험 이름 목록 지문(정렬 · 빈칸 없는 JSON · UTF-8 → sha256)."""
    return hashlib.sha256(json.dumps(sorted(ids), ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def tool_sha():
    """이 도구 파일의 sha256(고정 파일에 묶음 · 도구를 바꾸면 고정 파일도 다시 써야 함)."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def bundle_check(pin, body):
    """D 묶음 결과(body) ↔ 고정 파일(pin) → {"green", "checks", "missing", "extra", …}."""
    ids = body.get("ids") or []
    want = pin.get("ids") or []
    missing, extra = sorted(set(want) - set(ids)), sorted(set(ids) - set(want))
    checks = {"no_failures": not failed_set(body),
              "no_skips": int(body.get("skipped") or 0) == 0 and not body.get("skipped_ids"),
              "all_run": int(body.get("tests_run") or 0) == len(ids),
              "ids_equal_pin": not missing and not extra and len(ids) == len(set(ids)),
              "count_equal_pin": len(ids) == pin.get("count") == len(want),
              "ids_sha_equal_pin": ids_sha(ids) == pin.get("ids_sha256") == ids_sha(want),
              "tool_sha_equal_pin": tool_sha() == pin.get("tool_sha256"),
              "pin_kind": pin.get("kind") == PIN_KIND}
    return {"green": all(checks.values()), "checks": checks, "missing": missing, "extra": extra, "count": len(ids),
            "pin_count": pin.get("count"), "failed": sorted(failed_set(body)), "skipped_ids": body.get("skipped_ids") or []}


def load_pin(path):
    try:
        pin = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return pin if isinstance(pin, dict) and isinstance(pin.get("modules"), list) and pin["modules"] else None


def run_bundle(pin_path, out, root=None, timeout=3600):
    """--bundle: 고정 파일의 모듈만 돌려 고정 목록과 견줌 → 끝 값(0 green · 1 red). 결과 폴더: bundle.json · check.json · ids.txt · summary.md."""
    root = Path(root).resolve() if root else ROOT
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    pin = load_pin(pin_path)
    if pin is None:
        print(f"⚠️ 고정 파일을 못 읽음 · {pin_path}")
        return 1
    body = run_suite(root, out / "bundle.json", names=pin["modules"], timeout=timeout, verbosity=2)
    if body is None:
        print("⚠️ red · D 묶음을 끝까지 못 돌림")
        return 1
    got = bundle_check(pin, body)
    (out / "check.json").write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "ids.txt").write_text("\n".join(body.get("ids") or []) + "\n", encoding="utf-8")
    lines = ["## D 묶음 시험(필수 · 고정 목록 대조)", "", f"- 판정: {'green' if got['green'] else 'red'}",
             f"- 모은 시험 {got['count']}개 · 고정 {got['pin_count']}개 · 모듈 {len(pin['modules'])}개", ""]
    lines += [f"- {k}: {'맞음' if v else '어김'}" for k, v in got["checks"].items()]
    for title, key in (("고정 목록에만(빠진 시험)", "missing"), ("지금에만(고정 파일에 없는 시험)", "extra"), ("실패 · 오류", "failed"),
                       ("건너뜀", "skipped_ids")):
        lines += ["", f"### {title} ({len(got[key])})"] + ([f"- `{x}`" for x in got[key]] or ["- (없음)"])
    md = "\n".join(lines)
    (out / "summary.md").write_text(md + "\n", encoding="utf-8")
    _step(md)
    print(md)
    return 0 if got["green"] else 1


LOAD_FAILED = ("unittest.loader._FailedTest", "unittest.loader.ModuleImportFailure")


def write_pin(pin_path, modules=None, root=None, timeout=3600):
    """--pin: 모듈의 시험 이름을 모아(돌리지 않음 · 통과 여부는 --bundle이 따로 봄) 고정 파일을 (다시) 씀 → 끝 값.
    불러오기 실패(그 모듈 시험을 못 모음)가 있으면 쓰지 않음. 옛 고정 목록에서 빠지는 시험 수를 찍음(검토에 드러남)."""
    root = Path(root).resolve() if root else ROOT
    old = load_pin(pin_path)
    modules = list(modules or (old or {}).get("modules") or [])
    if not modules:
        print("⚠️ 모듈 목록이 없음(--modules로 주거나 옛 고정 파일이 있어야 함)")
        return 1
    ids = collect_ids(root, modules, timeout=timeout)
    if not ids or any(x.startswith(LOAD_FAILED) for x in ids):
        print("⚠️ 고정 파일을 쓰지 않음 · 시험 이름을 못 모았거나 불러오기 실패가 있음")
        return 1
    pin = {"kind": PIN_KIND, "modules": modules, "count": len(ids), "ids_sha256": ids_sha(ids), "tool_sha256": tool_sha(), "ids": ids}
    Path(pin_path).parent.mkdir(parents=True, exist_ok=True)
    Path(pin_path).write_text(json.dumps(pin, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    gone = sorted(set((old or {}).get("ids") or []) - set(ids))
    print(f"고정 파일을 씀 · 시험 {len(ids)}개 · 지문 {pin['ids_sha256'][:12]}" + (f" · 옛 목록에서 빠진 시험 {len(gone)}개" if gone else ""))
    return 0


def _step(md):
    step = os.getenv("GITHUB_STEP_SUMMARY")
    if step:
        try:
            with open(step, "a", encoding="utf-8") as f:
                f.write(md + "\n")
        except OSError:
            print("⚠️ 작업 요약에 쓰지 못함(결과 폴더에는 있음)")


def summary_md(diff, meta):
    """요약(목록만)."""
    lines = ["## 전체 시험 차이 검사(BOOST-0001-D)", "",
             f"- 판정: {'green(지금 실패 ⊆ 기준 실패 · 불변식 맞음)' if diff['green'] else 'red(새 실패 또는 불변식 어김)'}",
             f"- 기준: `{meta.get('base')}` · 시험 {meta.get('base_tests')}개 · 건너뜀 {diff.get('base_skipped')}",
             f"- 지금: `{meta.get('head')}`{' (커밋 안 한 고침 포함)' if meta.get('head_dirty') else ''} · 시험 {meta.get('head_tests')}개 · "
             f"건너뜀 {diff.get('head_skipped')}", ""]
    for k, v in (diff.get("invariants") or {}).items():
        lines.append(f"- 불변식 {k}: {'맞음' if v else '어김'}")
    lines.append("")
    for title, key in (("기준 실패 · 오류", "base_failed"), ("지금 실패 · 오류", "head_failed"), ("새 실패(지금에만)", "new_failures"),
                       ("고쳐진 것(기준에만)", "fixed"), ("빠진 시험(기준에만 있던 이름)", "missing_tests"),
                       ("새로 건너뜀", "newly_skipped")):
        rows = diff.get(key) or []
        lines.append(f"### {title} ({len(rows)})")
        lines += [f"- `{x}`" for x in rows] or ["- (없음)"]
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="기준 판과 지금 판의 실패 · 오류 시험 집합 견주기 · D 묶음 고정 대조")
    ap.add_argument("--base", default=None, help="기준 커밋(PR base 또는 merge-base)")
    ap.add_argument("--out", default=None, help="결과 폴더")
    ap.add_argument("--start", default="tests")
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--root", default=None, help="지금 판 폴더(기본: 이 저장소)")
    ap.add_argument("--bundle", default=None, help="D 묶음 고정 파일(이 모듈만 돌려 고정 목록과 견줌)")
    ap.add_argument("--pin", default=None, help="고정 파일을 (다시) 씀(모두 통과할 때만)")
    ap.add_argument("--modules", default=None, help="--pin 때 모듈 이름(빈칸 구분 · 없으면 옛 고정 파일의 목록)")
    a = ap.parse_args(argv)
    if a.pin:
        return write_pin(a.pin, a.modules.split() if a.modules else None, a.root, a.timeout)
    if not a.out:
        print("⚠️ --out 결과 폴더를 주세요")
        return 1
    if a.bundle:
        return run_bundle(a.bundle, a.out, a.root, a.timeout)
    if not a.base:
        print("⚠️ --base 기준 커밋을 주세요(또는 --bundle · --pin)")
        return 1
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
    diff.update(invariants(base_body, head_body))
    diff["green"] = bool(diff["green"] and diff["invariants_ok"])
    meta = {"base": base, "head": head, "head_dirty": dirty, "base_tests": base_body["tests_run"], "head_tests": head_body["tests_run"]}
    diff.update(meta)
    (out / "diff.json").write_text(json.dumps(diff, ensure_ascii=False, indent=1), encoding="utf-8")
    md = summary_md(diff, meta)
    (out / "summary.md").write_text(md + "\n", encoding="utf-8")
    _step(md)
    print(md)
    return 0 if diff["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
