"""FLOW-GATE-0059 시험 — 수급 문 셈 · 지금 판 재현 · 격자 · 이웃 · 채택 잣대 · 입력 잠금."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "FLOW-GATE-0059"
sys.path.insert(0, "/home/user/stock-dash/research")
import flow_gate as V
import mix54_run as M
import regime_dev as D
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
c = dict(V.FINAL, f_thr=-0.15, gate_k=0.0, up_lev=0.5)
check("1 수급 문: 상승 · F20 −0.2(< −0.15)면 레버리지 0.5 × 0 = 0 · F20 −0.1이면 0.5 · F20 −0.15(같음)은 줄이지 않음 · F20 없으면 0.5",
      D.targets("상승", c, {"F20": -0.2})[2] == 0.0 and D.targets("상승", c, {"F20": -0.1})[2] == 0.5
      and D.targets("상승", c, {"F20": -0.15})[2] == 0.5 and D.targets("상승", c, {})[2] == 0.5)
c2 = dict(c, gate_k=0.5)
check("2 k 0.5면 절반(0.25) · 횡보 인버스 0.4 · 하락 0은 F20과 무관하게 그대로 · 1일봉 몫(fb)도 그대로",
      D.targets("상승", c2, {"F20": -0.3})[2] == 0.25 and D.targets("횡보", c2, {"F20": -0.9})[2] == 0.4
      and D.targets("하락", c2, {"F20": -0.9})[2] == 0.0 and D.targets("상승", c2, {"F20": -0.3})[0] == 1.0)
D.BASE_CSV = M.BASES / f"{M.name(V.BASE)}.csv"; D.DATA, D.FEAT = None, None
n0, s0 = D.account(dict(V.FINAL))
r0 = V.score(n0, s0)
check("3 지금 판 그대로(f_thr 없음) = MIX-0054 최종 · 연 34.113% · 완료 114달 중 손실 40 · 가장 나쁜 완료 달 −14.043%",
      r0["annual_pct"] == 34.113 and r0["loss_months"] == 40 and r0["months"] == 114 and r0["worst_full_month_pct"] == -14.043)
n1, s1 = D.account(dict(V.FINAL, f_thr=-99.0, gate_k=0.0))
check("4 문턱이 아주 낮으면(−99 · 걸리는 날 없음) 지금 판과 NAV · 국면이 하루도 다르지 않음", n1 == n0 and s1 == s0)
check("5 격자 13 = 기준 + 문턱 {−0.20, −0.15, −0.10} × k {0, 0.5} × up_lev {0.4, 0.5}",
      len(V.grid()) == 13 and V.grid()[0][1].get("f_thr") is None and len({V.cname(g) for _, g in V.grid()[1:]}) == 12)
nb = V.neighbors(dict(V.FINAL, f_thr=-0.20, gate_k=0.0, up_lev=0.4))
nb2 = V.neighbors(dict(V.FINAL, f_thr=-0.15, gate_k=0.5, up_lev=0.5))
check("6 이웃: (−0.20 · 0 · 0.4) = 규칙 6 + 문턱 −0.15 + k 0.5 + up_lev 0.5 = 9 · (−0.15 · 0.5 · 0.5) = 6 + 문턱 둘 + k 0 + up_lev 0.4 = 10",
      len(nb) == 9 and ("f_thr", -0.15) in nb and ("gate_k", 0.5) in nb and ("up_lev", 0.5) in nb
      and len(nb2) == 10 and ("f_thr", -0.20) in nb2 and ("f_thr", -0.10) in nb2 and ("gate_k", 0.0) in nb2 and ("up_lev", 0.4) in nb2)
b = {"within": True, "annual_raw": 0.34, "loss_months": 40, "worst_full_month_raw": -0.14}
check("7 채택 잣대: 손실 달 −3(연 −0.4%p)은 채택 · 연 −0.6%p는 탈락 · 가장 나쁜 달이 나빠지면 탈락 · 나아진 게 없으면 탈락 · 잣대 밖이면 탈락",
      V.eligible(dict(b, loss_months=37, annual_raw=0.336), b) and not V.eligible(dict(b, loss_months=37, annual_raw=0.334), b)
      and not V.eligible(dict(b, loss_months=36, worst_full_month_raw=-0.141), b) and not V.eligible(dict(b, loss_months=39), b)
      and V.eligible(dict(b, worst_full_month_raw=-0.119), b) and V.eligible(dict(b, annual_raw=0.361), b)
      and not V.eligible(dict(b, within=False, annual_raw=0.40), b))
T = Path(tempfile.mkdtemp())
good = V.lock_body(); (T / "ok.json").write_text(json.dumps(good))
check("8 입력 잠금 13칸(뿌리 · 코드 4 · regime_dev.load가 읽는 ETF 4 · 시장 자료 2 · 바탕 장부 · 스냅샷)이 같으면 통과",
      V.verify_inputs(T / "ok.json") == good and len(good) == 13 and good["root"] == str(D.ROOT)
      and set(k for k in good if k.startswith("etf-data/")) == {f"etf-data/{c}.json" for c in D.ETF})
bad = dict(good, **{"etf-data/122630.json": "0" * 64}); (T / "bad.json").write_text(json.dumps(bad))
old = (V.LOCK, V.EVALS); V.LOCK, V.EVALS = T / "bad.json", T / "evals.jsonl"
try:
    V.run(); stopped = False
except SystemExit as e:
    stopped = "122630" in str(e)
V.LOCK, V.EVALS = old
check("9 잠금이 하나라도 다르면 첫 STARTED 전에 멈춤(기록 파일 안 생김)", stopped and not (T / "evals.jsonl").exists())
# 10 뿌리가 서로 다르면(잠근 checkout ≠ 계산이 읽는 곳) 첫 STARTED 전에 멈춤
import shutil
old_root = V.ROOT
V.ROOT = T / "other-checkout"
old = (V.LOCK, V.EVALS); V.LOCK, V.EVALS = T / "ok.json", T / "evals2.jsonl"
try:
    V.run(); stopped = False
except SystemExit as e:
    stopped = "뿌리가 서로 다름" in str(e)
V.ROOT = old_root; V.LOCK, V.EVALS = old
check("10 잠근 checkout과 계산이 읽는 뿌리(regime_dev.ROOT · mix54_run.ROOT)가 다르면 첫 STARTED 전에 멈춤", stopped and not (T / "evals2.jsonl").exists())
# 11 다른 뿌리(임시 checkout)로 셋을 함께 옮기면: 잠금도 계산도 그 뿌리의 같은 파일을 읽음 → 자료 한 줄을 바꾸면 잠금이 달라지고 load도 바뀐 값을 읽음
R2 = T / "root2"
for f in V.CODE_FILES + V.MARKET_FILES + [f"etf-data/{c}.json" for c in D.ETF]:
    (R2 / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy(Path(D.ROOT) / f, R2 / f)
saved = (V.ROOT, D.ROOT, M.ROOT)
V.ROOT = D.ROOT = M.ROOT = R2
lk2 = V.lock_body()
same_as_main = {k: v for k, v in lk2.items() if k != "root"} == {k: v for k, v in good.items() if k != "root"}
body = json.loads((R2 / "etf-data/122630.json").read_text()); last = body["closes"][-1]
body["closes"][-1] = [last[0], float(last[1]) + 1.0]; (R2 / "etf-data/122630.json").write_text(json.dumps(body))
lk3 = V.lock_body()
D.DATA, D.FEAT = None, None
etf_loaded = D.load()[1]["122630"][str(last[0])]
V.ROOT, D.ROOT, M.ROOT = saved
D.DATA, D.FEAT = None, None
check("11 임시 checkout에서도 잠금 = 계산이 읽는 파일: 그대로 옮기면 잠금이 같고 · 122630 한 줄을 바꾸면 잠금이 달라지며 load도 바뀐 값을 읽음",
      same_as_main and lk3["etf-data/122630.json"] != lk2["etf-data/122630.json"] and abs(etf_loaded - (float(last[1]) + 1.0)) < 1e-9)
print(f"모두 {ok}개 통과")
