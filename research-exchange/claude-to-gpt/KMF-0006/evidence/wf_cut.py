"""KMF-0006 자르기 시험(손익 판정 안 함 · 06-01부터 안 읽음): 후보 26개의 날별 손익을 자른 날 뒤 자료를 처음부터 안 읽고 다시 셈 → 자른 날 앞까지 한 칸도 같아야 함.
걷기 고르기는 이 날별 손익을 '그달 앞 달들'로만 쓰므로(합성 시험 2 · 3), 후보 손익이 앞만이면 걷기 전체도 앞만입니다."""
import json, os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
code = ("import sys,json;sys.path.insert(0,'research');import kmf as K,kmf6 as K6;"
        "p=K6.daily_pnl(K.load());print(json.dumps(p))")
env = dict(os.environ, KMF_CUT="20260601")
full = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
res = []
for ct in ("20260302", "20260401", "20260504"):
    env["KMF_CUT"] = ct
    part = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    diff = sum(1 for n in part for d in part[n] if d < ct and abs(part[n][d] - full[n][d]) > 1e-9)
    fut = sum(1 for n in part for d in part[n] if d >= ct)
    res.append({"cut": ct, "candidates": len(part), "diff": diff, "future_days": fut})
print(json.dumps({"pass": all(r["diff"] == 0 and r["future_days"] == 0 for r in res), "runs": res}, ensure_ascii=False))
