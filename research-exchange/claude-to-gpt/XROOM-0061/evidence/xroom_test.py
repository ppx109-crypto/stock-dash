"""XROOM-0061 시험 — 기준 · 대조 재현 · 바탕 바꿔도 셈 같음 · 격자 · 이웃 · 채택 잣대(대조 포함) · 입력 잠금."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "XROOM-0061"
sys.path.insert(0, "/home/user/stock-dash/research")
import xroom as V
import xasset as X
import mix54_run as M
import regime_dev as D
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
rb = X.score(*V.run_cfg({"base": "d0.5"}))
check("1 기준(d0.5 · 새 봇 없음) = MIX-0054 최종 · 연 34.113% · 손실 40 · −14.043%",
      rb["annual_pct"] == 34.113 and rb["loss_months"] == 40 and rb["worst_full_month_pct"] == -14.043)
rc = X.score(*V.run_cfg({"base": "d0.3"}))
check("2 대조(d0.3 · 새 봇 없음) = MIX-0054 all_rows의 d0.3_b0.3_no15m + L0.4_S0.4(연 31.230%) 재현",
      rc["annual_pct"] == 31.23)
n1, _ = V.run_cfg({"base": "d0.5"})
D.BASE_CSV = M.BASES / f"{M.name((0.5, 0.3))}.csv"; D.DATA, D.FEAT = None, None
no, _ = X._ORIG_ACCOUNT(dict(X.FINAL))
check("3 바탕을 d0.3 → d0.5로 다시 바꿔도 원래 셈(regime_dev.account)과 NAV가 하루도 다르지 않음(자료 다시 읽기 확인)", n1 == no)
V._CUR[0] = None
check("4 격자 14 = 기준 + 대조 + d0.3 × 바구니 {U4, U3} × N {6, 10} × w {0.2, 0.3, 0.4}",
      len(V.grid()) == 14 and V.grid()[0][1] == {"base": "d0.5"} and V.grid()[1][1] == {"base": "d0.3"}
      and all(c["base"] == "d0.3" and c["sleeve"]["w"] in (0.2, 0.3, 0.4) for _, c in V.grid()[2:]) and len({V.cname(c) for _, c in V.grid()}) == 14)
check("5 이웃: (U4 · 6 · 0.2) = n 4 · 8 · w 0.3 · U3 = 4개 · (U3 · 10 · 0.3) = n 8 · 12 · w 0.2 · 0.4 · U4 = 5개",
      V.neighbors({"u": "U4", "n": 6, "w": 0.2}) == [("n", 4), ("n", 8), ("w", 0.3), ("u", "U3")]
      and V.neighbors({"u": "U3", "n": 10, "w": 0.3}) == [("n", 8), ("n", 12), ("w", 0.2), ("w", 0.4), ("u", "U4")])
b = {"within": True, "annual_raw": 0.34, "loss_months": 40, "worst_full_month_raw": -0.14}
cc = {"within": True, "annual_raw": 0.31, "loss_months": 42, "worst_full_month_raw": -0.138}
check("6 채택 잣대: 지금 판 +1%p · 달 −1%p 안 · 손실 +2 안 · 대조 +1%p면 채택 · 지금 판 +0.9%p · 대조보다 덜 벎 · 잣대 밖은 탈락",
      V.eligible(dict(b, annual_raw=0.3501, worst_full_month_raw=-0.1499, loss_months=42), b, cc)
      and not V.eligible(dict(b, annual_raw=0.349), b, cc)
      and not V.eligible(dict(b, annual_raw=0.3501), b, dict(cc, annual_raw=0.345))
      and not V.eligible(dict(b, annual_raw=0.40, within=False), b, cc))
T = Path(tempfile.mkdtemp())
good = V.lock_body(); (T / "ok.json").write_text(json.dumps(good))
check("7 입력 잠금 19칸(뿌리 · 코드 5 · regime_dev ETF 4 · 새 봇 ETF 4 · 시장 자료 2 · 바탕 장부 2 · 스냅샷)이 같으면 통과",
      V.verify_inputs(T / "ok.json") == good and len(good) == 19 and good["root"] == str(D.ROOT)
      and set(k for k in good if k.startswith("etf-data/")) == {f"etf-data/{c}.json" for c in D.ETF + tuple(X.SLEEVE_ETF)})
bad = dict(good, **{"etf-data/122630.json": "0" * 64}); (T / "bad.json").write_text(json.dumps(bad))
old = (V.LOCK, V.EVALS); V.LOCK, V.EVALS = T / "bad.json", T / "evals.jsonl"
try:
    V.run(); stopped = False
except SystemExit as e:
    stopped = "122630" in str(e)
V.LOCK, V.EVALS = old
check("8 잠금이 하나라도 다르면 첫 STARTED 전에 멈춤(기록 파일 안 생김)", stopped and not (T / "evals.jsonl").exists())
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
check("9 잠근 checkout과 계산이 읽는 뿌리(regime_dev.ROOT · mix54_run.ROOT)가 다르면 첫 STARTED 전에 멈춤", stopped and not (T / "evals2.jsonl").exists())
# 11 다른 뿌리(임시 checkout)로 셋을 함께 옮기면: 잠금도 계산도 그 뿌리의 같은 파일을 읽음 → 자료 한 줄을 바꾸면 잠금이 달라지고 load도 바뀐 값을 읽음
R2 = T / "root2"
for f in V.CODE_FILES + X.MARKET_FILES + [f"etf-data/{c}.json" for c in D.ETF + tuple(X.SLEEVE_ETF)]:
    (R2 / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy(Path(D.ROOT) / f, R2 / f)
saved = (V.ROOT, X.ROOT, D.ROOT, M.ROOT)
V.ROOT = X.ROOT = D.ROOT = M.ROOT = R2
lk2 = V.lock_body()
same_as_main = {k: v for k, v in lk2.items() if k != "root"} == {k: v for k, v in good.items() if k != "root"}
body = json.loads((R2 / "etf-data/122630.json").read_text()); last = body["closes"][-1]
body["closes"][-1] = [last[0], float(last[1]) + 1.0]; (R2 / "etf-data/122630.json").write_text(json.dumps(body))
lk3 = V.lock_body()
D.DATA, D.FEAT = None, None
etf_loaded = D.load()[1]["122630"][str(last[0])]
V.ROOT, X.ROOT, D.ROOT, M.ROOT = saved
D.DATA, D.FEAT = None, None
check("10 임시 checkout에서도 잠금 = 계산이 읽는 파일: 그대로 옮기면 잠금이 같고 · 122630 한 줄을 바꾸면 잠금이 달라지며 load도 바뀐 값을 읽음",
      same_as_main and lk3["etf-data/122630.json"] != lk2["etf-data/122630.json"] and abs(etf_loaded - (float(last[1]) + 1.0)) < 1e-9)
print(f"모두 {ok}개 통과")
