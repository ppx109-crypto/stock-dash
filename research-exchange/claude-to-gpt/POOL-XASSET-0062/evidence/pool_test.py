"""POOL-XASSET-0062 시험 — 혼자 계좌 셈 · 현금 · 달 첫날만 맞춤 · 격자 · 조건 · 잠금."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "POOL-XASSET-0062"
sys.path.insert(0, "/home/user/stock-dash/research")
import pool_xasset as P
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
days = ["20200130", "20200131", "20200203", "20200204", "20200302"]
P.PX = {"069500": {d: 1.0 for d in days}, "153130": {d: 100.0 for d in days},
        "AAA": dict(zip(days, [10.0, 10.0, 11.0, 12.1, 12.1])), "BBB": dict(zip(days, [10.0, 10.0, 9.0, 8.0, 8.0]))}
P.LO, P.HI = days[0], days[-1]
P.X.UNIVERSE["T"] = ("AAA",)
n = P.account({"hold": "AAA"})
check("1 계속 들기: 둘째 날 종가에 사고(비용 0.05%) 그 뒤 값 비율 그대로", abs(n["20200204"] - (1 - P.COST) * 1.21) < 1e-12)
P.X.UNIVERSE["T2"] = ("BBB",)
saved = P.X.trend_pick
P.X.trend_pick = lambda px, p, k, codes: []
n2 = P.account({"u": "T2", "n": 2})
check("2 고른 것이 없으면 현금(수익 0 · 비용 0) → NAV 1 그대로", all(abs(v - 1.0) < 1e-15 for v in n2.values()))
calls = []
P.X.trend_pick = lambda px, p, k, codes: (calls.append(p) or list(codes))
P.account({"u": "T", "n": 2})
check("3 다시 고르는 때: 둘째 날(첫 맞춤)과 달 첫 거래일만 · 신호는 전 거래일 p", calls == ["20200130", "20200131", "20200204"])
P.X.trend_pick = saved
del P.X.UNIVERSE["T"], P.X.UNIVERSE["T2"]
P.PX, P.LO, P.HI = None, P.D.LO, P.D.HI
check("4 격자 5 = 단기채 비교 + U4/U3 × N 6/10", len(P.grid()) == 5 and P.grid()[0][1] == {"hold": "153130"})
bond = {"annual_raw": 0.02}
x = {"worst_day_raw": -0.05, "worst_full_month_raw": -0.10, "annual_raw": 0.0501, "corr_raw": 0.5}
check("5 후보 조건: 손실 −15% 안 · 단기채 + 3%p · 상관 ≤ 0.5 · 하나라도 어기면 탈락",
      P.eligible(x, bond) and not P.eligible(dict(x, annual_raw=0.049), bond) and not P.eligible(dict(x, corr_raw=0.51), bond)
      and not P.eligible(dict(x, worst_full_month_raw=-0.151), bond))
T = Path(tempfile.mkdtemp())
good = P.lock_body(); (T / "ok.json").write_text(json.dumps(good))
check("6 입력 잠금 11칸(뿌리 · 코드 3 · ETF 6 · 지금 판 달 값 파일)이 같으면 통과", P.verify_inputs(T / "ok.json") == good and len(good) == 11)
(T / "bad.json").write_text(json.dumps(dict(good, **{"etf-data/133690.json": "0" * 64})))
old = (P.LOCK, P.EVALS); P.LOCK, P.EVALS = T / "bad.json", T / "e.jsonl"
try:
    P.run(); stopped = False
except SystemExit as e:
    stopped = "133690" in str(e)
P.LOCK, P.EVALS = old
check("7 잠금이 다르면 첫 STARTED 전에 멈춤", stopped and not (T / "e.jsonl").exists())
print(f"모두 {ok}개 통과")
