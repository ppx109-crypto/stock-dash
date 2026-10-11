"""POOL-SECTOR-0063 시험 — 모멘텀 고르기(미래 안 봄 · 수익 > 0 · 자료 부족 뺌) · 격자 · 잠금."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "POOL-SECTOR-0063"
sys.path.insert(0, "/home/user/stock-dash/research")
import pool_sector as S
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
ms = ["20200131", "20200228", "20200331", "20200430"]
def lane(vals): return dict(zip(ms, vals))
px = {c: lane([10, 10, 10, 10]) for c in S.SECTORS}
px["091160"] = lane([10, 11, 12, 13]); px["091170"] = lane([10, 10.5, 11, 11.5]); px["091180"] = lane([10, 9, 8, 7])
px["305720"] = {"20200430": 50}
check("1 3달 수익 상위 2: 091160(+30%) · 091170(+15%) · 내린 091180과 0%인 것은 빠짐 · 자료 1달인 305720 빠짐",
      S.mom_pick(px, "20200430", 2, 3) == ["091160", "091170"])
check("2 미래 안 봄: p=03-31이면 04-30 값 무시(2달 수익으로 091160 · 091170)", S.mom_pick(px, "20200331", 2, 2) == ["091160", "091170"])
check("3 수익 > 0인 업종이 K보다 적으면 그만큼만(K 3이어도 둘)", S.mom_pick(px, "20200430", 3, 3) == ["091160", "091170"])
check("4 격자 6 = 단기채 · KODEX 200 비교 + K {2, 3} × L {3, 6}", len(S.grid()) == 6 and [c for _, c in S.grid()[2:]] == [{"k": 2, "l": 3}, {"k": 2, "l": 6}, {"k": 3, "l": 3}, {"k": 3, "l": 6}])
T = Path(tempfile.mkdtemp())
good = S.lock_body(); (T / "ok.json").write_text(json.dumps(good))
check("5 입력 잠금 17칸(뿌리 · 코드 4 · ETF 11 · 지금 판 달 값)이 같으면 통과", S.verify_inputs(T / "ok.json") == good and len(good) == 17)
(T / "bad.json").write_text(json.dumps(dict(good, **{"etf-data/091160.json": "0" * 64})))
old = (S.LOCK, S.EVALS); S.LOCK, S.EVALS = T / "bad.json", T / "e.jsonl"
try:
    S.run(); stopped = False
except SystemExit as e:
    stopped = "091160" in str(e)
S.LOCK, S.EVALS = old
check("6 잠금이 다르면 첫 STARTED 전에 멈춤", stopped and not (T / "e.jsonl").exists())
print(f"모두 {ok}개 통과")
