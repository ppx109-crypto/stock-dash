"""일봉 새 86회차(세 갈래 공통 실험 · 1일봉) — 후보 문의 수급 조건을 바꾼 판(research/flowvar.py). 기준 = 새 82회차. 씨앗 8 · 두 반(2017 ~ 2020 · 2021 ~)."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule
import flowvar as FV

names = list(FV.KINDS)
pick = names[:3] if os.environ.get("Q_PART", "1") == "1" else names[3:]
print(f"== 일봉 새 86회차: 수급 조건 바꾼 판 ({os.environ.get('Q_PART', '1')}) ==", flush=True)
base = None
for k in pick:
    got = T.once(k, holds=lambda r, k=k: (rule.holds(r) or nrl.aligned(r)) and FV.teach(r["code"], r["date"], k, before=True) and not nrl.target_cut(r))
print("끝", flush=True)
