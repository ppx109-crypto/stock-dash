"""수급 숫자(개인 · 외국인 · 기관 …)에 저녁 넥스트레이드 값이 섞였나(사용자 2026-10-06 "남은것도 확인 후 수정").

저장된 investor-data(저녁 · 밤에 받음)와 지금(확정 뒤) 한투에 다시 물은 값을 날마다 칸마다 견줌. 숫자 칸 이름 · 개수만 찍음(응답 본문 · 키 없음).
python research/probe_flows.py   · PROBE_N(종목 수, 기본 40)
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.chdir(Path(__file__).resolve().parent.parent)
import broker_kis  # noqa: E402

N = int(os.getenv("PROBE_N", "40"))
DAYS = ("20260929", "20260930", "20261001", "20261002", "20261006")
client = broker_kis.market()
files = sorted(Path("investor-data").glob("*.json"))[:N]
diff = defaultdict(lambda: defaultdict(int))
seen = defaultdict(int)
for f in files:
    body = json.loads(f.read_text(encoding="utf-8"))
    cols = body["cols"]
    have = {r[0]: r for r in body["rows"]}
    try:
        got = client.investor_daily(f.stem, max(DAYS))
    except broker_kis.BrokerError as e:
        print(f.stem, "못 물음", e)
        continue
    for g in got:
        d = g["date"]
        if d not in DAYS or d not in have:
            continue
        seen[d] += 1
        for i, c in enumerate(cols[1:], 1):
            a, b = have[d][i], g.get(c)
            if a is not None and b is not None and abs(float(a) - float(b)) > max(abs(float(b)) * 0.001, 0.5):
                diff[d][c] += 1
for d in DAYS:
    print(f"{d}: 견준 종목 {seen[d]} · 칸별 다른 종목 수 {dict(diff[d]) or '없음'}", flush=True)
