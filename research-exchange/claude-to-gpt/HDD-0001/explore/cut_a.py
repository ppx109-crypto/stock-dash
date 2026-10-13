"""자르기 시험: KMF_CUT 날부터 자료를 처음부터 안 읽은 새 프로세스로 다시 셈 → 자른 날 앞 날별 손익이 전체와 같은지(모든 판)."""
import subprocess, json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
full = json.loads(subprocess.run([sys.executable, "run_a.py", "--daily"], cwd=here, capture_output=True, text=True, check=True).stdout)
res = {}
for c in ("20260401", "20260701", "20260915", "20261001", "20261013"):
    part = json.loads(subprocess.run([sys.executable, "run_a.py", "--daily"], cwd=here, capture_output=True, text=True, check=True, env=dict(os.environ, KMF_CUT=c)).stdout)
    res[c] = sum(1 for k in full for d, v in part[k].items() if d < c and abs(v - full[k][d]) > 1e-9)
print("자르기 시험 다른 칸", res)
json.dump(res, open(os.path.join(here, "cut_a.json"), "w"))
