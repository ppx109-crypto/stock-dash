"""self24.py의 힘 시험: sleeve.py에 결함을 하나씩 넣어 시험이 잡는지(끝 상태 ≠ 0). 출력: mut24_out.json."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "sleeve.py").read_text()
ENT = '''        for v in by_ex.get(d, []):
            if q_prev > EPS:
                recv.append((v["지급일"], q_prev * v["주당"]))
'''
MUTS = {
    "M1 보유 넘겨 팔기": [("            s = min(H, need)\n", "            s = need\n")],
    "M2 지급일 하나에 모두 지급": [("            if pay <= d:\n", "            if any(pp <= d for pp, _ in recv):\n")],
    "M3 받을 돈을 현금으로 침": [("        if slack + K < -1e-10:\n", "        if slack + K + sum(a for _, a in recv) < -1e-10:\n")],
    "M4 목표에 그날 slack": [("(H0 + s0 + K0 - b * B0)", "(H0 + slack + K0 - b * B0)")],
    "M5 분배락 날 산 수량에도 권리": [(ENT, ""), ("        # 억지 팔기(그날 BASE 거래 · 위 맞춤 뒤)\n", ENT.replace("q_prev", "q") + "        # 억지 팔기(그날 BASE 거래 · 위 맞춤 뒤)\n")],
    "M6 사기 비용 안 매김": [("                K -= t * (1 + cost)\n", "                K -= t\n")],
    "M7 실패 표시가 회복 뒤 지워짐": [('"자금 자격": "FAIL" if bad else "PASS"', '"자금 자격": "FAIL" if bad and bad[-1]["날"] == rows[-1]["날"] else "PASS"')],
    "M8 받을 돈을 계좌에 안 넣음": [('"계좌": B + H + R + K', '"계좌": B + H + K')],
}
out = {}
for name, reps in MUTS.items():
    m = src
    for a, b in reps:
        assert m.count(a) == 1, (name, a[:40])
        m = m.replace(a, b)
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "sleeve.py").write_text(m)
        shutil.copy(HERE / "self24.py", td)
        r = subprocess.run(["python3", "self24.py"], cwd=td, capture_output=True, text=True)
    fails = [ln[5:] for ln in r.stdout.splitlines() if ln.startswith("FAIL")]
    out[name] = {"잡힘": r.returncode != 0, "실패한 시험": fails}
    print(name, "잡힘" if r.returncode != 0 else "안 잡힘", len(fails))
json.dump(out, open(HERE / "mut24_out.json", "w"), ensure_ascii=False, indent=1)
