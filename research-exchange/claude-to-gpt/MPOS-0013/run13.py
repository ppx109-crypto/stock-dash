"""MPOS-0013 진단 계산: z100gd로 REPRO_G · F_SIDEDOWN_G(MPOS-0012 잠근 장부)를 다시 돌려 갈래별 · 매매별 날 기록을 남김.
바탕 csv가 MPOS-0012 영수증의 바탕 지문과 바이트까지 같아야 함(기록만 더했는지 확인)."""
import json
import os
import sys
from pathlib import Path

HERE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos13")   # 계산 폴더
M12 = HERE.parent / "r8/research-exchange/claude-to-gpt/MPOS-0012"
sys.path.insert(0, str(M12))
import mpos12 as M  # noqa: E402

X = M.X
RB = json.load(open(M12 / "receipt_build.json"))
jobs = {}
for c in ("REPRO_G", "F_SIDEDOWN_G"):
    led = M.WORK / f"led_{c}.json"
    assert X.sha(str(led)) == RB[c]["장부 지문"], c
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    env.update(M.ENV)
    env.update(Z_D1_LED=str(led), Z_OUT=str(HERE / f"base_{c}.csv"), Z_ATTR=str(HERE / f"attr_{c}.csv"), Z_TRADE_OUT=str(HERE / f"trade_{c}.json"))
    jobs[c] = dict(cmd=[sys.executable, str(M.TREE_RUN), str(HERE / f"{c}.mods.json"), str(HERE / "z100gd.py")], env=env, cwd=str(M.TREE),
                   out=str(HERE / f"{c}.log"), clean=[str(HERE / f"base_{c}.csv"), str(HERE / f"trade_{c}.json")])
bad = X.dry({"z100gd": lambda: jobs})
if bad:
    sys.exit(f"마른 실행 FAIL {bad}")
rc = X.run_dag(jobs, workers=2, log=lambda m: print(m, flush=True))
rec = {c: {"rc": rc[c], "바탕 같음": X.sha(str(HERE / f"base_{c}.csv")) == RB[c]["바탕 지문"],
           "바깥 모듈": json.load(open(HERE / f"{c}.mods.json"))["바깥"]} for c in jobs}
json.dump(rec, open(HERE / "receipt13.json", "w"), ensure_ascii=False, indent=1)
print(rec)
