"""REGIME-SW-0051 합성 시험 — 격자 · 고정 틀 · 이웃 · 손실 고원 고르기 순서 · 상한."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "REGIME-SW-0051"
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D
import regime_rules4 as R
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
check("1 기록 칸 0051", D.BOX.name == "REGIME-SW-0051")
check("2 격자 = 7 × 3 × 5 × 2 = 210 · 레버리지 0.10 ~ 0.30", len(R.NS) * len(R.PS) * len(R.LEVS) * len(R.SIDES) == 210 and R.LEVS == [0.10, 0.15, 0.20, 0.25, 0.30])
check("3 고정 틀 = 0050 규칙(r10m5 · above_only · band None · lev_vt None · 하락 1일봉만)", R.FIXED["confirm"] == "r10m5" and R.FIXED["lev_vt"] is None and R.FIXED["down_inv"] == 0.0)
nb = R.neighbors({"n": 30, "persist": 2})
check("4 이웃: n 26 · 34 · 버팀 1 · 3 · r10m4 · r10m6(몫 축 없음)", nb == [("n", 26), ("n", 34), ("persist", 1), ("persist", 3), ("confirm", "r10m4"), ("confirm", "r10m6")])
check("5 버팀 1이면 버팀 0 이웃 없음", ("persist", 0) not in R.neighbors({"n": 20, "persist": 1}))
# 고르기 순서: 가짜 평가로 main을 돌려, 연수익 높은 칸부터 보며 이웃이 하나라도 잣대 밖이면 다음 칸으로
tmp = Path(tempfile.mkdtemp()); D.EVALS = tmp / "e.jsonl"; R.LOG = tmp / "LOG.md"
def mk(ann, month=-0.05):
    return {"annual_raw": ann, "annual_pct": round(ann * 100, 3), "worst_day_pct": -3.0, "worst_month_pct": round(month * 100, 3),
            "by_kind": {k: {"worst_day_raw": -0.03, "worst_month_raw": month} for k in ("상승", "하락", "횡보")}}
calls = []
def fake_eval(cfg, note=""):
    calls.append(note)
    if cfg.get("up_lev", 0) == 0:
        return mk(0.20)
    a = 0.20 + cfg["up_lev"] * 0.4 + cfg["n"] / 1000
    month = -0.05
    if cfg["n"] == 40 and cfg["persist"] == 3 and cfg["up_lev"] == 0.30 and cfg["side_inv"] == 0.2:
        a = 0.40                                   # 격자 최고
    if cfg.get("confirm") == "r10m4" and cfg["n"] == 40:
        month = -0.12                              # 최고 칸의 이웃 하나가 −10% 밖 → 다음 칸으로
    return mk(a, month)
D.evaluate = fake_eval
D._started = lambda: len(calls)
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    R.main()
out = json.loads(buf.getvalue().strip().splitlines()[-1])
check("6 최고 칸(n 40 · 버팀 3 · lev 0.30)의 이웃 r10m4가 달 −12% → 탈락 · 다음 칸으로 넘어가 ROBUST_CANDIDATE",
      out["verdict"] == "ROBUST_CANDIDATE" and out["checked"][0]["cfg"]["n"] == 40 and not out["checked"][0]["robust"] and out["checked"][-1]["robust"])
check("7 살펴본 칸 기록에 이웃마다 within · half_gain 칸", all({"within", "half_gain"} <= set(v) for v in out["checked"][0]["neighbors"].values()))
print(f"모두 {ok}개 통과")
