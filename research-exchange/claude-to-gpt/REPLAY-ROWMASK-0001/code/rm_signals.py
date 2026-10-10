"""REPLAY-ROWMASK-0001 · D1 신호만 뽑기(손익 계산 없음).
python3 -E -P rm_signals.py <b2> <캐시.pkl> <출력 폴더> <이름>
PR #41/#68 daily_exec.py 앞부분(1일봉 FIX: 달별 calm · 수급 T−2)을 그대로 불러 PICKS(HOLD 통과 줄)와 칸 수(SIZE)를 날마다 적음."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = sys.argv[4]
_src = (HERE / "daily_exec.py").read_text(encoding="utf-8").split("RUNS, CUTS = {}, {}")[0]
G = {"__name__": "rm_sig", "__file__": str(HERE / "daily_exec.py")}
exec(compile(_src, "daily_exec(앞부분 · PR #41 그대로)", "exec"), G)
OUT = Path(sys.argv[3])
LO, HI = "20250918", "20260331"
picks = {d: sorted([r["code"], G["SIZE"](r)] for r in rs) for d, rs in G["PICKS"].items() if LO <= d <= HI}
inside = {}
for r in G["nrl"].inside:
    if LO <= r["date"] <= HI:
        inside.setdefault(r["date"], []).append([r["code"], r.get("시총순위")])
out = {"name": NAME, "days": [d for d in G["DAYS"] if LO <= d <= HI], "picks": picks,
       "top100": {d: sorted(v) for d, v in inside.items()}, "BR": {d: v for d, v in G["BR"].items() if LO <= d <= HI},
       "ahead_present": any("ahead" in r for r in G["nrl"].inside[:1000])}
(OUT / f"signals_{NAME}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print("신호", NAME, "날", len(out["days"]), "· 신호 날", len(picks), "· 신호 줄", sum(len(v) for v in picks.values()), flush=True)
