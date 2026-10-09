"""REPLAY-CONTRACT-HARDENING-0001 · 변이 점검(사전등록 밖 추가 · 실행 뒤 작성) — 게이트를 하나씩 일부러 끈 어댑터로 fixtures_v2를 돌려 시험이 실제로 실패하는지 봄.
python3 -E -P mutation_check.py <call_budget 계획.json> <작업 폴더> <출력.json>
원본 코드는 바꾸지 않고, 작업 폴더에 복사본을 만들어 문자열 하나만 바꿉니다. 네트워크 없음."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN, WORK, OUT = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
MUT = {
    "M1_as_of_무시(미래 정정본 읽음)": ('if parse_avail(x["available_at_kst"])[0] <= as_of),', 'if True),'),
    "M2_날짜만_공개를_0시로(당일 사용 허용)": ("23, 59, 59, tzinfo=KST), \"date\"", "0, 0, 0, tzinfo=KST), \"date\""),
    "M3_성과게이트_끔": ('    if bad or idn["cash_gap"] > 1e-6', '    if False and bad'),
    "M4_STALE을_유효로": ('                reasons.append("UNKNOWN_MTM_STALE")', '                pass'),
    "M5_출처검사_끔": ('    prov = check_pair_provenance(raw_resp, adj_resp, cache_bytes)', '    prov = []'),
    "M6_팔기먼저_끔": ('        plan.sort(key=lambda x: (x[0] != "sell", x[1]))', '        pass'),
    "M7_잠금창_끔": ('if ca_day.get(c) and f["decided_at"] < ca_day[c] <= d:', 'if False:'),
    "M8_기준일_정확일치만(PR86 방식)": ("first_on_or_after = lambda x: next((d for d in dset if d >= x), None)",
                                  "first_on_or_after = lambda x: x if x in dset else None"),
}
res = {}
for name, (a, b) in MUT.items():
    wd = WORK / name.split("_")[0]
    if wd.exists():
        shutil.rmtree(wd)
    shutil.copytree(HERE, wd, ignore=shutil.ignore_patterns("__pycache__", "mutation_check.py"))
    src = (wd / "raw_replay_v2.py").read_text()
    assert src.count(a) == 1, name
    (wd / "raw_replay_v2.py").write_text(src.replace(a, b))
    p = subprocess.run([sys.executable, "-E", "-P", str(wd / "fixtures_v2.py"), PLAN, str(wd / "out")], capture_output=True, text=True)
    if p.returncode != 0:
        res[name] = {"caught": True, "how": "시험 실행 오류", "error_last_line": (p.stderr.strip().splitlines() or [""])[-1][:200]}
        continue
    summ = json.loads(p.stdout.strip().splitlines()[-1])
    fails = {g: v["fail"] for g, v in summ.items() if isinstance(v, dict) and v["fail"]}
    res[name] = {"caught": bool(fails), "how": "시험 실패", "failed_tests": fails}
out = {"mutations": res, "all_caught": all(v["caught"] for v in res.values()),
       "note": "사전등록 밖 추가 점검. 원본 raw_replay_v2.py는 그대로이며, 작업 폴더 복사본에서 한 줄씩만 바꿈."}
Path(OUT).write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({k: (v["caught"], sorted(t for g in v.get("failed_tests", {}).values() for t in g) or v.get("error_last_line")) for k, v in res.items()}, ensure_ascii=False))
