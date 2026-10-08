"""일부러 결함을 넣은 복사본에서 시험이 실패하는지 확인. python3 -I tests/mutation_check.py <임시폴더>"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
TMP = Path(sys.argv[1])
SRC = (HERE / "cost_contract.py").read_text(encoding="utf-8")
MUT = {
    "M1 2026 코스닥 0.0015(기존 결함)": ('("20260101", "20261008", 0.0020))\n# 일반 KOSPI', '("20260101", "20261008", 0.0015))\n# 일반 KOSPI'),
    "M2 2019-06-03 경계 하루 밀림": ('("20170101", "20190602", 0.0030), ("20190603"', '("20170101", "20190603", 0.0030), ("20190604"'),
    "M3 매수에도 세금": ("    _day(day)\n    return 0.0", "    _day(day)\n    return 0.0020"),
    "M4 모르는 기간 기본값 0.0015": ('        raise UnknownTax(f"{market} {day} 계약 없음({scenario})")', "        return 0.0015"),
    "M5 ETF도 주식 표": ('    if instrument_type != "STOCK":', '    if instrument_type not in ("STOCK", "ETF"):'),
}
out = []
for name, (a, b) in MUT.items():
    assert SRC.count(a) == 1, name
    d = TMP / name.split()[0]
    (d / "tests").mkdir(parents=True, exist_ok=True)
    (d / "cost_contract.py").write_text(SRC.replace(a, b), encoding="utf-8")
    shutil.copy(HERE / "tests" / "test_cost_contract.py", d / "tests" / "test_cost_contract.py")
    p = subprocess.run([sys.executable, "-I", str(d / "tests" / "test_cost_contract.py")], capture_output=True, text=True)
    failed = [c["case"] for c in json.loads(p.stdout)["cases"] if c["result"] != "PASS"] if p.stdout.strip() else ["실행 오류"]
    out.append({"mutation": name, "caught": p.returncode != 0, "failed_cases": failed})
res = {"kind": "mutation_check(합성)", "mutations": out, "caught": sum(o["caught"] for o in out), "total": len(out)}
print(json.dumps(res, ensure_ascii=False, indent=1))
sys.exit(0 if res["caught"] == res["total"] else 1)
