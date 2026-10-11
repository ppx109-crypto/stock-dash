"""보고 전용(판정 밖 · GPT #263 기록 보완) — 잣대 밖 칸들의 가장 나쁜 완료 달 이름. 잠긴 safelev.py의 셈을 그대로 씀."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import safelev as S  # noqa: E402
rows = json.loads((S.BOX / "evidence/all_rows.json").read_text())
for r in rows:
    if r["full"]["within"]:
        continue
    navs = S.T.full(r["cfg"])
    ds = sorted(navs); mo = {}
    for j in range(1, len(ds)):
        mo[ds[j][:6]] = mo.get(ds[j][:6], 1.0) * navs[ds[j]] / navs[ds[j - 1]]
    full = {m: v - 1 for m, v in mo.items() if S.T.FIRST_FULL <= m <= S.T.LAST_FULL}
    m, v = min(full.items(), key=lambda x: x[1])
    print(f"{r['name']}: 가장 나쁜 완료 달 {m} {v*100:.3f}% · 기록 값 {r['full']['worst_full_month_pct']}% · 같음 {abs(v - r['full']['worst_full_month_raw']) < 1e-12}")
