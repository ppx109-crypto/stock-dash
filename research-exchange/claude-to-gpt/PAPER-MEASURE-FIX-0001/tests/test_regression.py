"""PAPER-MEASURE-FIX-0001 회귀 시험(합성 · 실측 아님 · 네트워크 0). python3 -I tests/test_regression.py
작업트리 안 시험 파일은 tests/ 아래 임시 폴더에 만들고 끝나면 지웁니다."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import build_daily_measurement as B  # noqa: E402
import sanitize_fills as F  # noqa: E402

KEY = "TEST-ONLY-KEY-000000000000000000"
HEAD = B.HEADLINE_KEYS
R = []
START = {"date": "2026-09-30", "cash_krw": 1_000_000, "positions": {}}
PRICES = {"2026-09-30": {}, "2026-10-01": {"005930": 5100}, "2026-10-02": {"005930": 4900}, "2026-10-05": {"005930": 5000}}


def exp(days, **kw):
    return {"days": days, "calendar": "TEST-KRX", "generated_at": "2026-10-08T00:00:00+09:00", "provenance": "합성 시험", **kw}


EXP3 = exp(["2026-10-01", "2026-10-02", "2026-10-05"])
COST = {k: {"krw": 0, "kind": "assumed"} for k in F.COST_ITEMS}


def kis_rows():
    r = {"ord_dt": "20261001", "ord_tmd": "093000", "sll_buy_dvsn_cd": "02", "pdno": "005930", "tot_ccld_qty": "100",
         "avg_prvs": "5000", "odno": "T0001", "ord_gno_brno": "T01", "cncl_yn": "N"}
    return [r, {**r, "ord_dt": "20261005", "sll_buy_dvsn_cd": "01", "avg_prvs": "5050", "odno": "T0002"}]


def ledger():
    fills, n = F.normalize(kis_rows(), KEY.encode(), {"defaults": {"instrument_type": "STOCK", "market_at_fill": "KOSPI", "costs": COST}})
    return fills, n


def case(name, fn):
    try:
        fn()
        R.append({"case": name, "result": "PASS"})
    except Exception as e:  # noqa: BLE001
        R.append({"case": name, "result": "FAIL", "why": f"{type(e).__name__}: {str(e)[:160]}"})


def raises(fn, text=None):
    try:
        fn()
    except B.MeasureError as e:
        assert text is None or text in str(e), str(e)
        return
    raise AssertionError("MeasureError 안 남")


def m(prices=PRICES, expected=EXP3, start=START, fills=None):
    return B.measure(ledger()[0] if fills is None else fills, start, prices, expected_days=expected)


# ── D1 거래일 완전성 ──
def t_missing_middle_day():
    p = {k: v for k, v in PRICES.items() if k != "2026-10-02"}
    raises(lambda: m(p), "평가가격이 없습니다")


def t_extra_or_out_of_range_day():
    raises(lambda: m({**PRICES, "2026-10-06": {"005930": 1}}), "범위 밖")
    raises(lambda: m({**PRICES, "2026-09-29": {}}), "범위 밖")
    raises(lambda: m(PRICES, exp(["2026-10-01", "2026-10-02"])), "범위 밖")


def t_duplicate_price_day():
    raises(lambda: m({**PRICES, "2026-10-02T00:00": {"005930": 4900}}), "형식")
    raises(lambda: m({**{k: v for k, v in PRICES.items() if k != "2026-10-02"}, "2026-10-2": {"005930": 4900}}), "형식")


def t_expected_contract():
    raises(lambda: m(PRICES, exp(["2026-10-01", "2026-10-01", "2026-10-02", "2026-10-05"])), "중복")
    raises(lambda: m(PRICES, exp(["2026-10-02", "2026-10-01", "2026-10-05"])), "중복")
    raises(lambda: m(PRICES, exp(["2026-09-30", "2026-10-01", "2026-10-02", "2026-10-05"])), "시작일")
    raises(lambda: m(PRICES, exp(["20261001", "2026-10-02", "2026-10-05"])), "YYYY-MM-DD")
    for k in ("days", "calendar", "generated_at", "provenance"):
        bad = {**EXP3}
        bad.pop(k)
        raises(lambda b=bad: m(PRICES, b), "모두 있어야")
        raises(lambda k=k: m(PRICES, {**EXP3, k: "" if k != "days" else []}), "모두 있어야")
    try:
        B.measure(ledger()[0], START, PRICES)
    except TypeError:
        pass
    else:
        raise AssertionError("expected_days 없이 계산됨")


# ── D2 상태 · headline ──
def t_incomplete_headline_null():
    st = {"date": "2026-09-30", "cash_krw": 0, "positions": {"005930": 100}}
    o = B.measure([], st, {"2026-09-30": {"005930": 100}, "2026-10-01": {"005930": 101}, "2026-10-02": {}},
                  expected_days=exp(["2026-10-01", "2026-10-02"]))
    assert o["data_status"] == "INCOMPLETE" and o["days_valid"] == 1 and o["days_total"] == 2, o["data_status"]
    assert all(o[k] is None for k in HEAD), [k for k in HEAD if o[k] is not None]
    assert o["days"] is None and o["months"] is None
    assert [d["status"] for d in o["diagnostic_partial_days"]] == ["OK", "NULL"] and o["first_invalid"] == "2026-10-02"
    assert B.public_guard(o) == [] and B.whitelist_guard(o) == []


def t_all_invalid():
    fl = ledger()[0]
    fl[0]["costs"]["sell_tax"] = {"krw": None, "kind": "missing"}
    o = m(fills=fl)
    assert o["data_status"] == "INVALID" and o["days_valid"] == 0 and all(o[k] is None for k in HEAD)


def t_complete_three_days():
    o = m()
    assert o["data_status"] == "MEASURED_COMPLETE" and o["days_valid"] == o["days_total"] == 3, o["data_status"]
    assert all(o[k] is not None for k in HEAD) and len(o["days"]) == 3 and "diagnostic_partial_days" not in o
    assert o["provenance"]["calendar"] == "TEST-KRX" and o["completeness"]["expected_days"] == 3
    assert B.public_guard(o) == [] and B.whitelist_guard(o) == []


# ── D3 비공개 입력 경계(CLI) ──
def _write_set(d):
    d = Path(d)
    fills, n = ledger()
    (d / "rows.json").write_text(json.dumps(kis_rows()), encoding="utf-8")
    (d / "ctx.json").write_text(json.dumps({"defaults": {"instrument_type": "STOCK", "costs": COST}}), encoding="utf-8")
    (d / "ledger.jsonl").write_text("".join(json.dumps(f) + "\n" for f in fills), encoding="utf-8")
    (d / "start.json").write_text(json.dumps(START), encoding="utf-8")
    (d / "prices.json").write_text(json.dumps(PRICES), encoding="utf-8")
    (d / "exp.json").write_text(json.dumps(EXP3), encoding="utf-8")
    (d / "flows.json").write_text("[]", encoding="utf-8")
    (d / "ca.json").write_text("[]", encoding="utf-8")
    (d / "counts.json").write_text(json.dumps({"ok": True, "counts": n}), encoding="utf-8")
    return d


ENV = {k: v for k, v in os.environ.items() if k != F.KEY_ENV}


def run_sanitize(rows, ctx, out, cwd=None):
    return subprocess.run([sys.executable, "-I", str(HERE / "sanitize_fills.py"), "--kis-rows", str(rows), "--context", str(ctx),
                           "--out", str(out)], capture_output=True, text=True, env={**ENV, F.KEY_ENV: KEY}, cwd=cwd)


def run_build(paths, out, cwd=None):
    args = [sys.executable, "-I", str(HERE / "build_daily_measurement.py"), "--out", str(out)]
    for k, v in paths.items():
        args += [f"--{k}", str(v)]
    return subprocess.run(args, capture_output=True, text=True, env=ENV, cwd=cwd)


def build_paths(d):
    return {"fills": d / "ledger.jsonl", "start": d / "start.json", "prices": d / "prices.json", "expected-days": d / "exp.json",
            "flows": d / "flows.json", "corp-actions": d / "ca.json", "sanitize-counts": d / "counts.json"}


def t_private_inputs_inside_git(probe):
    with tempfile.TemporaryDirectory() as td:
        d = _write_set(td)
        p = run_sanitize(d / "rows.json", d / "ctx.json", d / "out.jsonl")
        assert p.returncode == 0, p.stdout
        p = run_build(build_paths(d), d / "pub.json")
        assert p.returncode == 0 and json.loads(p.stdout)["data_status"] == "MEASURED_COMPLETE", p.stdout
        hit = 0
        for label in ("kis-rows", "context", "out"):
            src = {"kis-rows": d / "rows.json", "context": d / "ctx.json", "out": d / "out2.jsonl"}
            if label != "out":
                inside = probe / f"s_{label}.json"
                shutil.copy(src[label], inside)
            else:
                inside = probe / "s_out.jsonl"
            src[label] = inside
            p = run_sanitize(src["kis-rows"], src["context"], src["out"])
            assert p.returncode == 2 and "작업트리" in p.stdout and not (probe / "s_out.jsonl").exists(), (label, p.stdout)
            assert not (d / "out2.jsonl").exists(), label
            hit += 1
        for label, path in build_paths(d).items():
            inside = probe / f"b_{label}{path.suffix}"
            shutil.copy(path, inside)
            p = run_build({**build_paths(d), label: inside}, d / f"pub_{label}.json")
            assert p.returncode == 2 and "작업트리" in p.stdout and not (d / f"pub_{label}.json").exists(), (label, p.stdout)
            hit += 1
        assert hit == 10, hit


def t_symlink_and_relative(probe):
    with tempfile.TemporaryDirectory() as td:
        d = _write_set(td)
        inside = probe / "real_rows.json"
        shutil.copy(d / "rows.json", inside)
        link_out = d / "link_to_inside.json"                 # 밖 링크 → 안 파일
        link_out.symlink_to(inside)
        p = run_sanitize(link_out, d / "ctx.json", d / "o1.jsonl")
        assert p.returncode == 2 and not (d / "o1.jsonl").exists(), p.stdout
        link_in = probe / "link_to_outside.json"             # 안 링크 → 밖 파일
        link_in.symlink_to(d / "prices.json")
        p = run_build({**build_paths(d), "prices": link_in}, d / "pub1.json")
        assert p.returncode == 2 and not (d / "pub1.json").exists(), p.stdout
        rel = os.path.relpath(inside, d)                     # '..'로 안을 가리키는 상대경로
        assert rel.startswith("..")
        p = run_sanitize(rel, "ctx.json", "o2.jsonl", cwd=d)
        assert p.returncode == 2 and not (d / "o2.jsonl").exists(), p.stdout
        p = run_sanitize("rows.json", "ctx.json", "o3.jsonl", cwd=d)   # 밖 상대경로는 허용
        assert p.returncode == 0 and (d / "o3.jsonl").exists(), p.stdout


def t_public_out_inside_allowed(probe):
    with tempfile.TemporaryDirectory() as td:
        d = _write_set(td)
        out = probe / "public.json"
        p = run_build(build_paths(d), out)
        assert p.returncode == 0 and out.exists(), p.stdout
        o = json.loads(out.read_text(encoding="utf-8"))
        assert o["data_status"] == "MEASURED_COMPLETE" and B.public_guard(o) == [] and B.whitelist_guard(o) == []


def t_json_duplicate_key_cli():
    with tempfile.TemporaryDirectory() as td:
        d = _write_set(td)
        raw = json.dumps(PRICES)[:-1] + ', "2026-10-02": {"005930": 1}}'
        (d / "prices.json").write_text(raw, encoding="utf-8")
        p = run_build(build_paths(d), d / "pub.json")
        assert p.returncode == 2 and "같은 키" in p.stdout and not (d / "pub.json").exists(), p.stdout
        (d / "exp.json").write_text(json.dumps(exp(["2026-10-01", "2026-10-05"])), encoding="utf-8")
        (d / "prices.json").write_text(json.dumps({k: v for k, v in PRICES.items() if k != "2026-10-02"}), encoding="utf-8")
        p = run_build(build_paths(d), d / "pub2.json")       # 기대일에서도 빼면 그 날은 측정 대상이 아님(입력자 책임)
        assert p.returncode == 0, p.stdout


probe = Path(tempfile.mkdtemp(prefix="_probe_", dir=HERE / "tests"))
try:
    assert F.inside_git_worktree(probe), "시험 폴더가 Git 작업트리 안이 아님"
    for n, f in (("D1 중간 거래일 누락 거부", t_missing_middle_day), ("D1 기대보다 많은 · 범위 밖 가격일 거부", t_extra_or_out_of_range_day),
                 ("D1 같은 날 다른 표기 거부", t_duplicate_price_day), ("D1 expected_days 계약(중복 · 순서 · 필드 · 필수)", t_expected_contract),
                 ("D1 JSON 같은 키 두 번 거부(CLI)", t_json_duplicate_key_cli),
                 ("D2 첫날 유효 · 다음날 평가 누락 → INCOMPLETE · headline null", t_incomplete_headline_null),
                 ("D2 전부 무효 → INVALID · headline null", t_all_invalid), ("완전한 합성 3일 → MEASURED_COMPLETE", t_complete_three_days),
                 ("D3 비공개 입력 10개 각각 작업트리 안 → 거부", lambda: t_private_inputs_inside_git(probe)),
                 ("D3 symlink 두 방향 · '..' 상대경로 거부", lambda: t_symlink_and_relative(probe)),
                 ("공개 출력은 작업트리 안 허용(검사 통과)", lambda: t_public_out_inside_allowed(probe))):
        case(n, f)
finally:
    shutil.rmtree(probe)

out = {"kind": "synthetic_regression_test(실측 아님)", "cases": R, "passed": sum(r["result"] == "PASS" for r in R), "total": len(R)}
print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(0 if out["passed"] == out["total"] else 1)
