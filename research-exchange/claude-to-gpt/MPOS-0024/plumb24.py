"""배관 점검(성과 아님 · 달러 · 단기채 값 안 씀): 실제 BASE 현금 경로(cash_path_base.json) + 값이 늘 같은 가짜 상품(손익 0 · 분배 없음)으로
보조 장부를 돌려 ① BASE 입력 불변 ② 자금 불능 날이 손익 없이도 생기는지 · 왜 생기는지(누적 비용 K < 0 · BASE slack = 0인 날)를 셈.
출력: plumb24_out.json."""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sleeve import run_sleeve  # noqa: E402

P = HERE / "cash_path_base.json"
rows = json.load(open(P))
base = [(r["날"], r["NAV"], max(0.0, r["slack"])) for r in rows]   # 부동소수 −2.2e−16 은 0으로(76날 · 최소 −2.22e−16)
keep = copy.deepcopy(base)
const = {d: 100.0 for d, _, _ in base}
out = {"입력": {"cash_path_base.json": hashlib.sha256(P.read_bytes()).hexdigest(), "sleeve.py": hashlib.sha256((HERE / "sleeve.py").read_bytes()).hexdigest()},
       "BASE slack = 0(≤ 1e−12) 날": sum(1 for _, _, s in base if s <= 1e-12), "전체 날": len(base),
       "부동소수 음수 slack 날(0으로 씀)": sum(1 for r in rows if r["slack"] < 0), "칸": {}}
for x in (0.1, 0.2, 0.3):
    r = run_sleeve(base, const, [], x=x, b=0.02)
    bad = r["자금 불능 날"]
    zero_days = {d for d, _, s in base if s <= 1e-12}
    out["칸"][f"x={x}"] = {"자금 자격": r["자금 자격"], "첫 자금 불능 날": r["첫 자금 불능 날"], "자금 불능 날 수": len(bad),
                          "그중 BASE slack = 0인 날": sum(1 for b_ in bad if b_["날"] in zero_days),
                          "최대 모자람(NAV 단위)": max((b_["모자람"] for b_ in bad), default=0.0),
                          "끝 날 H + K(= −누적 비용 · 손익 0이라)": r["행"][-1]["H"] + r["행"][-1]["K"], "누적 비용": r["비용"], "억지 팔기": r["억지 팔기"]}
out["BASE 입력 불변"] = base == keep
json.dump(out, open(HERE / "plumb24_out.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
