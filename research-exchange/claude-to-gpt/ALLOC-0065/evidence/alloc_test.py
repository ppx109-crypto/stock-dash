"""ALLOC-0065 시험 — 다시 맞춤 셈 · 비용 · 기준 재현 · 격자 · 추천 규칙 · 이웃 · 잠금."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "ALLOC-0065"
sys.path.insert(0, "/home/user/stock-dash/research")
import alloc as A
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
days = ["20200130", "20200131", "20200203", "20200204"]
A.CACHE["T"] = (days, dict(zip(days, [1, 1, 1.1, 1.1])), dict(zip(days, [1, 1, 1.0, 1.0])), dict(zip(days, [1, 1, 1.0, 1.0])))
A.B_CELLS["T"] = None
n = A.account({"b": "T", "wb": 0.5, "wc": 0.0})
grow = 0.5 * 1.1 + 0.5
cost = A.COST_A_DOWN * abs(grow * 0.5 - 0.55) + A.COST_ETF * abs(grow * 0.5 - 0.5)
check("1 달 첫날(02-03) 값이 바뀐 뒤 목표 몫으로 다시 맞춤 · A를 줄인 몫 0.30% · B를 늘린 몫 0.05% 비용", abs(n["20200203"] - (grow - cost)) < 1e-12)
n0 = A.account({"b": "T", "wb": 0.0, "wc": 0.0})
check("2 A 100%면 다시 맞춤 비용 0 · A와 같은 NAV", n0["20200204"] == 1.1)
del A.CACHE["T"], A.B_CELLS["T"]
r = A.score(A.account({"b": "U3_n6", "wb": 0.0, "wc": 0.0}))
check("3 기준(지금 판 100%) = MIX-0054 최종 · 연 34.113% · 손실 40 · −14.043%", r["annual_pct"] == 34.113 and r["loss_months"] == 40 and r["worst_full_month_pct"] == -14.043)
g = A.grid()
check("4 격자 27 = 기준 + B 0 · C {0.1, 0.2} 2 + POOL-1 칸 2 × wB {0.1 ~ 0.4} 4 × wC {0, 0.1, 0.2} 3", len(g) == 27 and len({json.dumps(c, sort_keys=True) for _, c in g}) == 27)
rows = [{"name": "기준", "within": True, "annual_raw": 0.34, "loss_months": 40, "eff": 2.4},
        {"name": "x", "within": True, "annual_raw": 0.33, "loss_months": 38, "eff": 3.0},
        {"name": "y", "within": True, "annual_raw": 0.30, "loss_months": 35, "eff": 3.5},
        {"name": "z", "within": False, "annual_raw": 0.36, "loss_months": 41, "eff": 2.0}]
r1, r2 = A.pick(rows)
check("5 추천: 수익 = 잣대 안 연 최고(기준) · 균형 = 연 ≥ 기준 − 3%p 안 효율 최고(x · y는 3%p 넘게 낮아 빠짐) · 잣대 밖 z 빠짐", r1["name"] == "기준" and r2["name"] == "x")
nb = A.neighbors({"b": "U3_n6", "wb": 0.2, "wc": 0.1})
check("6 이웃: wB ± 0.1 · wC ± 0.1 · POOL-1 다른 칸 = 5개", len(nb) == 5 and {"b": "U4_n10", "wb": 0.2, "wc": 0.1} in nb)
T = Path(tempfile.mkdtemp())
good = A.lock_body(); (T / "ok.json").write_text(json.dumps(good))
check("7 입력 잠금이 같으면 통과", A.verify_inputs(T / "ok.json") == good)
(T / "bad.json").write_text(json.dumps(dict(good, **{"etf-data/133690.json": "0" * 64})))
old = (A.LOCK, A.EVALS); A.LOCK, A.EVALS = T / "bad.json", T / "e.jsonl"
try:
    A.run(); stopped = False
except SystemExit as e:
    stopped = "133690" in str(e)
A.LOCK, A.EVALS = old
check("8 잠금이 다르면 첫 STARTED 전에 멈춤", stopped and not (T / "e.jsonl").exists())
print(f"모두 {ok}개 통과 · 잠금 {len(good)}칸")
