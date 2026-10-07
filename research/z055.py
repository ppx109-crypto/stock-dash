"""2차 연구 STEP 6 — A(1일봉 '새 82') 매매 목록을 쪼개기 고친 시총(CAPS_ADJ=1 · NRL_CACHE 따로 구움)과 옛 시총으로 뽑아 덤프.
Z_TAG=adj|raw → scratchpad/z055_d1_{tag}.json = [(코드, 산 날, 판 날, 손익%(왕복 0.25% 뺀 값), 칸)] · 씨앗 0 · ntools.T.once와 같음.
CAPS_ADJ=1 NRL_CACHE=.../nrl-cache-adj.pkl Z_TAG=adj python research/z055.py
"""
import json
import os
import sys

sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import ntools as T  # noqa: E402

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
got = T.once("일봉 새 82회차")
rows = [(t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for s in ("앞", "뒤") if got.get(s) for t in got[s]["매매목록"]]
json.dump(rows, open(SP + f"z055_d1_{os.environ.get('Z_TAG', 'adj')}.json", "w"))
for s in ("앞", "뒤"):
    g = got.get(s) or {}
    print(s, {k: v for k, v in g.items() if k != "매매목록" and not isinstance(v, (list, dict))}, flush=True)
print("매매", len(rows))
