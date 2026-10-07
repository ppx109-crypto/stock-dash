"""N12 — 좁은 장 RL(docs/RL-NARROW.md): 내림장(코스피200 < 60일선 · 어제까지)에선 빈칸 엔진(③ 돌리기 · ② 달러)을 끄면?
실제 엔진 연구판(i013 · 운영과 같은 FINAL 설정 · lookahead.py)으로: 지금 · 200일선 아래 쉼(I_GREG=down_off · 예전 시험) · 60일선 아래 쉼(down60_off).
python research/z044.py
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lookahead import FINAL  # noqa: E402

for lab, extra in (("지금(운영)", {}), ("200일선 아래 쉼", {"I_GREG": "down_off"}), ("60일선 아래 쉼(N12)", {"I_GREG": "down60_off"})):
    env = {**os.environ, **FINAL, **extra, "I_MTM": "0"}
    out = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "i013.py")], env=env, capture_output=True, text=True).stdout
    print(f"== {lab} ==")
    print("\n".join(l for l in out.splitlines() if l.strip().startswith(("B ", "C ", "C1", "C2"))), flush=True)
