"""통합 매매 규칙 점검(docs/AUDIT-UNIFIED.md) A2 · A3 — 자르기 · 더럽히기 시험을 여러 날에 걸쳐 4갈래로 동시에.
LA_MODE=cut | poison · A_DAYS=quarter(2018 ~ 2026 분기마다) | 쉼표 날짜 · A_PEEK=1이면 일부러 미래를 보는 판(반드시 불합격이어야 함)."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import lookahead as LA

days = os.environ.get("A_DAYS", "quarter")
if days == "quarter":
    import itools as I
    D = np.array(I.DAYS)
    want = [f"{y}{m:02d}15" for y in range(2018, 2027) for m in (1, 4, 7, 10)]
    days = [str(D[np.searchsorted(D, w)]) for w in want if w < str(D[-1])]
else:
    days = days.split(",")
extra = {"I_PEEK": "1"} if os.environ.get("A_PEEK") else {}
full = LA.run_i013(extra)
with ThreadPoolExecutor(4) as ex:
    res = list(ex.map(lambda d: (d, LA.compare(full, LA.run_i013(extra, d), d)), days))
bad = [(d, b) for d, b in res if b]
print(f"== 점검 {LA.MODE} · 날 {len(days)}개 · {'검사 눈(미래를 보는 판)' if extra else '최종 판'} ==")
for d, b in res:
    print(f"  {d}: {'합격' if not b else '불합격 — ' + ', '.join(b)}")
print(f"합격 {len(days) - len(bad)} / {len(days)}")
