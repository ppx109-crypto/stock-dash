"""POOL-GLOBAL-0064 시험 — 듀얼 모멘텀 고르기(미래 안 봄 · 수익 > 0 · 모두 음수면 국고채) · 격자 · 잠금."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "POOL-GLOBAL-0064"
sys.path.insert(0, "/home/user/stock-dash/research")
import pool_global as G
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
ms = ["20200131", "20200228", "20200331", "20200430"]
lane = lambda v: dict(zip(ms, v))
px = {c: lane([10, 9, 8, 7]) for c in G.GLOBAL}
px["133690"] = lane([10, 11, 12, 13]); px["241180"] = lane([10, 10.2, 10.4, 10.6])
check("1 3달 수익 상위 1 = 나스닥(+30%) · 상위 2 = 나스닥 · 니케이", G.mom_pick(px, "20200430", 1, 3) == ["133690"] and G.mom_pick(px, "20200430", 2, 3) == ["133690", "241180"])
down = {c: lane([10, 9, 8, 7]) for c in G.GLOBAL}
check("2 모두 음수면 국고채 148070", G.mom_pick(down, "20200430", 2, 3) == ["148070"])
check("3 미래 안 봄: p=03-31이면 04-30 값 무시(2달)", G.mom_pick(dict(px, **{"241180": dict(lane([10, 10, 10, 10]), **{"20200430": 99})}), "20200331", 2, 2) == ["133690"])
check("4 격자 6 = 단기채 · 나스닥 비교 + K {1, 2} × L {6, 12}", len(G.grid()) == 6 and [c for _, c in G.grid()[2:]] == [{"k": 1, "l": 6}, {"k": 1, "l": 12}, {"k": 2, "l": 6}, {"k": 2, "l": 12}])
T = Path(tempfile.mkdtemp())
good = G.lock_body(); (T / "ok.json").write_text(json.dumps(good))
check("5 입력 잠금 15칸(뿌리 · 코드 4 · ETF 8 · 지금 판 달 값 · POOL-1 달 값)이 같으면 통과", G.verify_inputs(T / "ok.json") == good and len(good) == 15)
(T / "bad.json").write_text(json.dumps(dict(good, **{"etf-data/133690.json": "0" * 64})))
old = (G.LOCK, G.EVALS); G.LOCK, G.EVALS = T / "bad.json", T / "e.jsonl"
try:
    G.run(); stopped = False
except SystemExit as e:
    stopped = "133690" in str(e)
G.LOCK, G.EVALS = old
check("6 잠금이 다르면 첫 STARTED 전에 멈춤", stopped and not (T / "e.jsonl").exists())
print(f"모두 {ok}개 통과")
