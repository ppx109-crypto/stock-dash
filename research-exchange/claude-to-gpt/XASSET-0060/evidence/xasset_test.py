"""XASSET-0060 시험 — 추세 고르기 · 지금 판 재현 · 새 봇 없으면 원래 셈과 같음 · 빚 없음 · 격자 · 이웃 · 채택 잣대 · 입력 잠금."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "XASSET-0060"
sys.path.insert(0, "/home/user/stock-dash/research")
import xasset as V
import mix54_run as M
import regime_dev as D
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
px = {"A": {"20200131": 10, "20200228": 11, "20200331": 12, "20200415": 13},
      "B": {"20200131": 13, "20200228": 12, "20200331": 11, "20200415": 10},
      "C": {"20200331": 5, "20200415": 6}}
check("1 추세 고르기: p일까지 달 끝 값(그달은 p 값)으로 마지막 > n달 평균 · 오르는 A만 · 내리는 B 빠짐 · 자료 n달 안 되는 C 빠짐",
      V.trend_pick(px, "20200415", 3, ("A", "B", "C")) == ["A"])
check("2 미래 안 봄: p 뒤 값은 안 씀(p=03-31이면 04-15 값 무시 · 3달 평균 11 < 12 → A 고름)",
      V.trend_pick(px, "20200331", 3, ("A",)) == ["A"] and V.trend_pick({"A": dict(px["A"], **{"20200401": 1})}, "20200331", 3, ("A",)) == ["A"])
D.BASE_CSV = M.BASES / f"{M.name(V.BASE)}.csv"; D.DATA, D.FEAT = None, None
n0, s0 = V.account_x(dict(V.FINAL))
no, so = V._ORIG_ACCOUNT(dict(V.FINAL))
check("3 새 봇 없으면 regime_dev.account(원래 셈)와 NAV · 국면이 하루도 다르지 않음", n0 == no and s0 == so)
r0 = V.score(n0, s0)
check("4 지금 판 = MIX-0054 최종 · 연 34.113% · 완료 114달 중 손실 40 · 가장 나쁜 완료 달 −14.043%",
      r0["annual_pct"] == 34.113 and r0["loss_months"] == 40 and r0["months"] == 114 and r0["worst_full_month_pct"] == -14.043)
V.account_x(dict(V.FINAL, sleeve={"u": "U4", "n": 6, "w": 0.3}))
check("5 새 봇(가장 큰 몫 w 0.3)에서도 빚 없음(현금 + 1일봉 몫 안 현금 ≥ 0 · 성과 값은 보지 않음)", V.account_x.min_slack >= -1e-12)
check("6 격자 13 = 기준 + 바구니 {U4, U3} × n {6, 10} × w {0.1, 0.2, 0.3}",
      len(V.grid()) == 13 and "sleeve" not in V.grid()[0][1] and len({V.cname(g["sleeve"]) for _, g in V.grid()[1:]}) == 12)
nb = V.neighbors({"u": "U4", "n": 6, "w": 0.1}); nb2 = V.neighbors({"u": "U3", "n": 10, "w": 0.2})
check("7 이웃: (U4 · 6 · 0.1) = n 4 · 8 · w 0.2 · U3 = 4개 · (U3 · 10 · 0.2) = n 8 · 12 · w 0.1 · 0.3 · U4 = 5개",
      nb == [("n", 4), ("n", 8), ("w", 0.2), ("u", "U3")] and nb2 == [("n", 8), ("n", 12), ("w", 0.1), ("w", 0.3), ("u", "U4")])
b = {"within": True, "annual_raw": 0.34, "loss_months": 40, "worst_full_month_raw": -0.14}
check("8 채택 잣대: 연 +1%p · 달 −1%p 안 · 손실 달 +2 안이면 채택 · 연 +0.9%p · 달 −1.1%p · 손실 달 +3 · 잣대 밖은 탈락",
      V.eligible(dict(b, annual_raw=0.3501, worst_full_month_raw=-0.1499, loss_months=42), b) and not V.eligible(dict(b, annual_raw=0.349), b)
      and not V.eligible(dict(b, annual_raw=0.36, worst_full_month_raw=-0.1511), b) and not V.eligible(dict(b, annual_raw=0.36, loss_months=43), b)
      and not V.eligible(dict(b, annual_raw=0.40, within=False), b))
T = Path(tempfile.mkdtemp())
good = V.lock_body(); (T / "ok.json").write_text(json.dumps(good))
check("9 입력 잠금 17칸(뿌리 · 코드 4 · regime_dev.load가 읽는 ETF 4 · 새 봇 ETF 4 · 시장 자료 2 · 바탕 장부 · 스냅샷)이 같으면 통과",
      V.verify_inputs(T / "ok.json") == good and len(good) == 17 and good["root"] == str(D.ROOT)
      and set(k for k in good if k.startswith("etf-data/")) == {f"etf-data/{c}.json" for c in D.ETF + tuple(V.SLEEVE_ETF)})
bad = dict(good, **{"etf-data/122630.json": "0" * 64}); (T / "bad.json").write_text(json.dumps(bad))
old = (V.LOCK, V.EVALS); V.LOCK, V.EVALS = T / "bad.json", T / "evals.jsonl"
try:
    V.run(); stopped = False
except SystemExit as e:
    stopped = "122630" in str(e)
V.LOCK, V.EVALS = old
check("10 잠금이 하나라도 다르면 첫 STARTED 전에 멈춤(기록 파일 안 생김)", stopped and not (T / "evals.jsonl").exists())
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
check("11 잠근 checkout과 계산이 읽는 뿌리(regime_dev.ROOT · mix54_run.ROOT)가 다르면 첫 STARTED 전에 멈춤", stopped and not (T / "evals2.jsonl").exists())
# 11 다른 뿌리(임시 checkout)로 셋을 함께 옮기면: 잠금도 계산도 그 뿌리의 같은 파일을 읽음 → 자료 한 줄을 바꾸면 잠금이 달라지고 load도 바뀐 값을 읽음
R2 = T / "root2"
for f in V.CODE_FILES + V.MARKET_FILES + [f"etf-data/{c}.json" for c in D.ETF + tuple(V.SLEEVE_ETF)]:
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
check("12 임시 checkout에서도 잠금 = 계산이 읽는 파일: 그대로 옮기면 잠금이 같고 · 122630 한 줄을 바꾸면 잠금이 달라지며 load도 바뀐 값을 읽음",
      same_as_main and lk3["etf-data/122630.json"] != lk2["etf-data/122630.json"] and abs(etf_loaded - (float(last[1]) + 1.0)) < 1e-9)
print(f"모두 {ok}개 통과")
