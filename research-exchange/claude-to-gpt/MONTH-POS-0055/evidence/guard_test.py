"""MONTH-POS-0055 시험 — 지킴이 없음 = MIX-0054 최종 그대로 · 지킴이 시각(t 장 끝 판정 → t+1 종가) · 달 바뀌면 풀림 · 빚 없음 · 격자 · 이웃."""
import json, os, sys
os.environ["REG_BOX"] = "MONTH-POS-0055"
sys.path.insert(0, "/home/user/stock-dash/research")
import month_guard as G
import mix54_run as M
import regime_dev as D
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
D.BASE_CSV = M.BASES / f"{M.name(G.BASE)}.csv"; D.DATA, D.FEAT = None, None
n0, s0 = D.account(G.FINAL)
n1, s1 = G.account_guard(dict(G.FINAL, down_inv=0.0), {})
r1 = G.score(n1, s1)
check("1 지킴이 없음 = regime_dev.account(MIX-0054 최종)와 날마다 NAV · 국면 같음 · 연 34.113% · 완료된 114달 가운데 손실 40",
      n0 == n1 and s0 == s1 and r1["annual_pct"] == 34.113 and r1["loss_months"] == 40 and r1["months"] == 114)
check("1b 부분 달(2017-02 · 2026-09)은 공식 셈에서 빠지고 참고표에만", set(r1["partial_months_ref"]) == {"201702", "202609"}
      and "201702" not in r1["neg_list"] and "202609" not in r1["neg_list"] and len(G.months(n1)) == 116)
# 합성 자료: 3달 · 바탕이 1월 둘째 날부터 하루 −1%씩 · ETF는 그대로 · 시장 횡보(덧붙임 인버스)
days = [f"2020{m:02d}{d:02d}" for m in (1, 2, 3) for d in range(1, 21)]
nav, base = 1.0, {}
for i, d in enumerate(days):
    if d[:6] == "202001" and i >= 1:
        nav *= 0.99
    elif d[:6] == "202002":
        nav *= 1.004
    base[d] = (nav, 0.5)
etf = {c: {d: 100.0 for d in days} for c in D.ETF}
saved = (D.DATA, D.FEAT, D.states)
D.DATA = (base, etf, {}, {}); D.FEAT = None
D.states = lambda feat, cfg: {d: "횡보" for d in feat}
cfg = dict(G.FINAL, down_inv=0.0)
na, _ = G.account_guard(cfg, {}, lo="20200101", hi="20200320")
nb, _ = G.account_guard(cfg, {"k": 0.02, "g": None, "fb": 0.0}, lo="20200101", hi="20200320")
# 1월: 둘째 날 누적 −1.02%(ETF 비용 포함) · 셋째 날 −2.01% ≤ −2% → 넷째 날 종가에 바탕 0(비용 0.30%) → 그 뒤 1월은 평평
jan = [d for d in days if d[:6] == "202001"]
check("2 지킴이 판정은 t 장 끝 누적 → t+1 종가 실행: 1월 1 ~ 3째 날은 지킴이 없음과 같고 4째 날 실행 · 그 뒤 1월 평평",
      all(abs(na[d] - nb[d]) < 1e-12 for d in jan[:3]) and nb[jan[3]] != na[jan[3]] and all(abs(nb[d] - nb[jan[3]]) < 1e-12 for d in jan[3:]))
check("3 실행 날 비용: 바탕 평가액 × 0.30% + ETF 0.05% × 덧붙임 평가액이 빠짐", nb[jan[3]] < na[jan[3]] + 1e-12 and nb[jan[3]] > na[jan[3]] - 0.004)
feb = [d for d in days if d[:6] == "202002"]
check("4 다음 달 첫날 원래대로(2월은 바탕 다시 1 · 날마다 약 +0.4%)", all(nb[feb[i]] / nb[feb[i - 1]] > 1.0039 for i in range(1, len(feb))))
nc, _ = G.account_guard(cfg, {"k": None, "g": 0.01, "fb": 0.5}, lo="20200101", hi="20200320")
# 2월: 첫날 +0.4%(비용 조금) · 둘째 날 +0.8% · 셋째 날 +1.2% ≥ +1% → 넷째 날 종가부터 바탕 0.5 → 다섯째 날부터 하루 약 +0.2%
check("5 이익 잠금: 2월 누적 +1% 넘은 다음 날 실행 · 그 뒤 하루 약 +0.2%(바탕 0.5)", all(abs(nc[feb[i]] / nc[feb[i - 1]] - 1.002) < 1e-4 for i in range(4, len(feb)))
      and nc[feb[2]] / nc[feb[1]] > 1.0039)
check("6 빚 없음(min_cash_slack ≥ −1e−12)", D.account.min_slack >= -1e-12)
D.DATA, D.FEAT, D.states = saved
check("7 격자 68 = 기준 · 내림 인버스만 + (손실 멈춤 4 × 이익 잠금 3 − 1) × 행동 3 × 내림 인버스 2", len(G.grid()) == 68)
ns = G.neighbors(G.FINAL, {"k": 0.04, "g": 0.03, "fb": 0.5})
check("8 이웃 = 규칙 6 + 손실 문턱 ±1칸(0.02 · 0.06) + 이익 문턱 ±1칸(0.06 · None 빼고)", len(ns) == 9 and ("guard", "k", 0.02) in ns and ("guard", "k", 0.06) in ns and ("guard", "g", 0.06) in ns)
check("9 채택 잣대: 손실 달 4개 이상 줄고 · 연 ≥ 최종 × 0.9 · 하루 · 달 −15% · 이웃 상한 300", G.LOSS_CUT == 4 and G.ANN_FLOOR == 0.9 and G.DAY_LIM == G.MONTH_LIM == -0.15 and G.NB_CAP == 300)
import tempfile, shutil
from pathlib import Path
T = Path(tempfile.mkdtemp())
good = G.lock_body()
(T / "lock_ok.json").write_text(json.dumps(good))
check("10 잠금이 같으면 verify_inputs 통과(코드 4 · ETF 넷 · 시장 자료 둘 · 바탕 장부 · 스냅샷)", G.verify_inputs(T / "lock_ok.json") == good
      and {"etf-data/114800.json", "etf-data/252670.json", "etf-data/122630.json", "etf-data/069500.json", "research/month_guard.py"} <= set(good) and len(good) == 12)
bad = dict(good); bad["etf-data/122630.json"] = "0" * 64
(T / "lock_bad.json").write_text(json.dumps(bad))
old = (G.LOCK, G.EVALS); G.LOCK, G.EVALS = T / "lock_bad.json", T / "evals.jsonl"
try:
    G.run(); stopped = False
except SystemExit as e:
    stopped = "122630" in str(e)
G.LOCK, G.EVALS = old
check("11 잠금이 하나라도 다르면(122630) run이 첫 STARTED 전에 멈춤(평가 기록 파일이 안 생김)", stopped and not (T / "evals.jsonl").exists())
# round 2 결과 보완(GPT #229): 다시 셈 실행기는 뿌리가 다르거나 잠금 v2가 다르면 평가 전에 멈춤
T3 = Path(tempfile.mkdtemp())
old = (G.ROOT, G.LOCK2, G.BOX)
G.ROOT = T3 / "other-checkout"; G.BOX = T3
try:
    G.rerun(); stopped = False
except SystemExit as e:
    stopped = "뿌리가 서로 다름" in str(e)
G.ROOT = old[0]
check("13 다시 셈: 잠금 checkout과 계산 뿌리(regime_dev.ROOT · mix54_run.ROOT)가 다르면 평가 전에 멈춤", stopped and not (T3 / "evals_rerun.jsonl").exists())
lk2 = G.lock_body_v2()
(T3 / "lock2.json").write_text(json.dumps(dict(lk2, **{"etf-data/114800.json": "0" * 64})))
G.LOCK2 = T3 / "lock2.json"
try:
    G.rerun(); stopped = False
except SystemExit as e:
    stopped = "114800" in str(e)
G.ROOT, G.LOCK2, G.BOX = old
check("14 다시 셈: 잠금 v2(뿌리 · 코드 4 · load가 읽는 ETF 4 · 시장 자료 2 · 바탕 장부 · 스냅샷 = 13칸)가 하나라도 다르면 평가 전에 멈춤",
      stopped and not (T3 / "evals_rerun.jsonl").exists() and len(lk2) == 13 and lk2["root"] == str(D.ROOT))
print(f"모두 {ok}개 통과")
