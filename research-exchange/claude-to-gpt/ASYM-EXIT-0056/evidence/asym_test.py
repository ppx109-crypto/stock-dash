"""ASYM-EXIT-0056 시험 — 버팀 셈 · 지금 판 재현 · 격자 · 이웃 · 채택 잣대 · 입력 잠금."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "ASYM-EXIT-0056"
sys.path.insert(0, "/home/user/stock-dash/research")
import asym_exit as A
import mix54_run as M
import regime_dev as D
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
# 가짜 판정 줄로 버팀 셈 시험
def run_states(raws, cfg):
    old = D.raw_state
    seq = iter(raws)
    feat = {f"d{i:03d}": {"i": i} for i in range(len(raws))}
    D.raw_state = lambda f, c: raws[f["i"]]
    try:
        return [v for _, v in sorted(A.states_asym(feat, cfg).items())]
    finally:
        D.raw_state = old
base = dict(A.FINAL)
up3 = ["상승"] * 3
mixed = up3 + ["횡보", "하락", "하락"]
check("1 p_up 없으면 지금 규칙 그대로(섞인 판정 횡보 · 하락 · 하락은 같은 판정 3일이 아니라 아직 상승)", run_states(mixed, base)[-1] == "상승")
check("2 새 규칙 p_up 3: '상승 아닌 날' 3일이면 빠져나옴(섞여도 셈) → 셋째 날 하락", run_states(mixed, dict(base, p_up=3, p_side=3))[-1] == "하락")
s1 = run_states(up3 + ["횡보", "상승", "상승"], dict(base, p_up=1, p_side=3))
check("3 p_up 1: 상승 아닌 날 하루면 다음 국면으로(그날 판정 횡보) · 다시 상승은 횡보에서 빠져나오는 규칙(p_side 3)을 따름", s1[3] == "횡보" and s1[5] == "횡보")
s2 = run_states(up3 + ["횡보"] * 3 + ["상승"], dict(base, p_up=1, p_side=1))
check("4 p_side 1: 횡보(인버스)에서 상승 아닌… 횡보 아닌 날 하루면 빠져나옴", s2[-1] == "상승")
s3 = run_states(["하락"] * 3 + ["상승", "상승"], dict(base, p_up=1, p_side=1))
check("5 하락에서는 지금 규칙(같은 판정 3일) 그대로 · 이틀 상승이면 아직 하락", s3[-1] == "하락")
D.BASE_CSV = M.BASES / f"{M.name(A.BASE)}.csv"; D.DATA, D.FEAT = None, None
n0, s0 = A._ORIG_STATES and D.account(dict(A.FINAL))
r0 = A.score(n0, s0)
check("6 지금 판 그대로(p_up 없음) = MIX-0054 최종 · 연 34.113% · 완료 114달 중 손실 40 · 가장 나쁜 완료 달 −14.043%",
      r0["annual_pct"] == 34.113 and r0["loss_months"] == 40 and r0["months"] == 114 and r0["worst_full_month_pct"] == -14.043)
check("7 격자 10 = 기준 + p_up {1,2,3} × p_side {1,2,3}", len(A.grid()) == 10 and A.grid()[0][1].get("p_up") is None)
nb = A.neighbors(dict(A.FINAL, p_up=1, p_side=1))
check("8 이웃(p_up 1 · p_side 1) = n 20 · 28 · persist 2 · 4 · r10m4 · r10m6 · p_up 2 · p_side 2", len(nb) == 8 and ("p_up", 2) in nb and ("p_side", 2) in nb and ("persist", 2) in nb)
b = {"within": True, "annual_raw": 0.34, "loss_months": 40, "worst_full_month_raw": -0.14}
check("9 채택 잣대: 손실 달 −3(연 −0.4%p)은 채택 · 연 −0.6%p는 탈락 · 가장 나쁜 달이 나빠지면 탈락 · 나아진 게 없으면 탈락",
      A.eligible(dict(b, loss_months=37, annual_raw=0.336), b) and not A.eligible(dict(b, loss_months=37, annual_raw=0.334), b)
      and not A.eligible(dict(b, loss_months=36, worst_full_month_raw=-0.141), b) and not A.eligible(dict(b, loss_months=39), b)
      and A.eligible(dict(b, worst_full_month_raw=-0.119), b) and A.eligible(dict(b, annual_raw=0.361), b))
T = Path(tempfile.mkdtemp())
good = A.lock_body(); (T / "ok.json").write_text(json.dumps(good))
check("10 입력 잠금 12개(코드 4 · ETF 4 · 시장 자료 2 · 바탕 장부 · 스냅샷)가 같으면 통과", A.verify_inputs(T / "ok.json") == good and len(good) == 12)
bad = dict(good, **{"etf-data/122630.json": "0" * 64}); (T / "bad.json").write_text(json.dumps(bad))
old = (A.LOCK, A.EVALS); A.LOCK, A.EVALS = T / "bad.json", T / "evals.jsonl"
try:
    A.run(); stopped = False
except SystemExit as e:
    stopped = "122630" in str(e)
A.LOCK, A.EVALS = old
check("11 잠금이 하나라도 다르면 첫 STARTED 전에 멈춤(기록 파일 안 생김)", stopped and not (T / "evals.jsonl").exists())
print(f"모두 {ok}개 통과")
