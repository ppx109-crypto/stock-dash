"""MIX-0054 합성 시험 — 15분봉 뺌 · 격자 · 덧붙임 설정 · 잣대 · 잠금 · 기록."""
import csv, json, os, shutil, subprocess as sp, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "MIX-0054"
sys.path.insert(0, "/home/user/stock-dash/research")
import mix54_run as M
import regime_dev as D
import regime_rules4  # noqa: F401  (고르기 시험에서 가짜 계좌 셈으로 바꾸기 전에 먼저 불러 둠)
ROOT = Path("/home/user/stock-dash")
SPD = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
check("1 격자 = 1일봉 4 × 바구니 4 = 16 · 15분봉만 뺀 지금 몫(0.5 · 0.5)이 격자 안", len(M.grid()) == 16 and M.NOW in M.grid())
envs = [M.base_cmd(g) for g in M.grid()]
check("2 모든 칸 Z_DROP = 15m(빈칸 엔진 · 인버스 · 바구니 켬) · 흔들림 상한 m1 · 몫 칸", all(e["Z_DROP"] == "15m" and e["Z_ACC_VOL"] == "0.010911" for e in envs)
      and M.base_cmd((0.7, 1.0))["Z_SHARE_1D"] == "0.7" and M.base_cmd((0.7, 1.0))["Z_SHARE_BASKET"] == "1.0")
l15 = json.load(open(SPD / "x004_m15_final.json")); b15 = sorted(x[1] for x in l15)
check("3 빼는 까닭: 15분봉 장부 104건 · 2025-09-18 ~ 2026-08-03뿐", len(l15) == 104 and b15[0] == "20250918" and b15[-1] == "20260803")
src = (ROOT / "research/z100.py").read_text()
check("4 z100: '15m'이 Z_DROP에 있으면 15분봉 장부를 읽지 않음(빈 목록)", 'led15 = [] if "15m" in DROP else' in src)
cand = {c["id"]: c["config"] for c in json.loads(sp.run(["git", "-C", str(ROOT), "show", "origin/claude/inspiring-newton-afr321:paper-candidates/candidates.json"], capture_output=True, text=True).stdout)["candidates"]}
def same(a, b):
    return all(a.get(k) == b.get(k) for k in set(a) | set(b))
check("5 덧붙임 18가지: 없음 · 0049 · 0050(후보 목록 설정 그대로) · 0051 규칙 몫 격자 15(0051 = L0.2_S0.2 · 0052 = L0.25_S0.3)",
      len(M.OVERLAYS) == 18 and M.OVERLAYS["none"] is None and same(M.OVERLAYS["0049"], cand["REGIME-SW-0049"]) and same(M.OVERLAYS["0050"], cand["REGIME-SW-0050"])
      and same(M.OVERLAYS["L0.2_S0.2"], cand["REGIME-SW-0051"]) and same(M.OVERLAYS["L0.25_S0.3"], cand["REGIME-SW-0052"]))
TMP = Path(tempfile.mkdtemp()); M.BASES = TMP; M.EVALS_LOG = TMP / "evals.jsonl"; M.BASES_LOG = TMP / "bases.jsonl"
shutil.copy("/tmp/mix0053-bases/d0.5_m0.5_b0.5_xnone.csv", TMP / f"{M.name(M.NOW)}.csv")
r = M.evaluate(M.NOW, M.OVERLAYS["L0.25_S0.3"], D)
check("6 바탕 장부를 바꿔 끼우는 셈: MIX-0053 지금 조합 장부 + 0052 = 28.633%(앞 결과 그대로)", abs(r["annual_pct"] - 28.633) < 1e-9)
fake = {"by_kind": {"상승": {"worst_day_raw": -0.15, "worst_month_raw": -0.10}, "하락": {"worst_day_raw": -0.01, "worst_month_raw": -0.01}, "횡보": {"worst_day_raw": -0.01, "worst_month_raw": -0.1000001}}}
check("7 잣대는 반올림 전 · 세 장 모두(횡보 −0.1000001 → 밖)", not M.within(fake))
smoke = SPD / "smoke54.csv"
check("8 15분봉 뺀 바탕 한 판(z100 · 1일봉 0.5 · 바구니 0.5)이 끝까지 돌고 장부 점검 통과(성적은 보지 않음)", M.check_csv(smoke)[0])
syn = TMP / "syn.csv"; syn.write_text("날,NAV,현금\n20170201,100,40\n20170202,100,20\n")
shutil.copy(syn, TMP / "d9_b9_no15m.csv")
check("9 돈 쓰임(보고) = 평균(1 − 현금 ÷ NAV): 0.6 · 0.8 → 0.7", abs(M.money_use((9, 9)) - 0.7) < 1e-12)
recs = [json.loads(l) for l in M.EVALS_LOG.read_text().splitlines()]
check("10 평가마다 EVALS_LOG에 STARTED → DONE(바탕 · 덧붙임 열쇠)", [x["status"] for x in recs] == ["STARTED", "DONE"] and M.name(M.NOW) in recs[0]["key"])
lk = M.lock()
M.log(M.BASES_LOG, {"status": "DONE", "cell": M.name(M.NOW), "lock": lk, "sha256": M.sha(TMP / f"{M.name(M.NOW)}.csv")})
try:
    M.verify_all(); stopped = False
except SystemExit as e:
    stopped = "15개" in str(e)
check("11 16개 가운데 하나라도 DONE · 파일 sha가 없으면 고르기 전에 멈춤(지금 15개 모자람)", stopped)
pe = M.base_cmd(M.NOW, parent={"PATH": "/usr/bin", "Z_PARK": "1", "Z_STOCK_SIDE": "x", "Z_ATTR": "/tmp/a.csv", "Z_ACC_VOL": "0", "PYTHONPATH": "/evil", "Z_DROP": ""})
check("12 부모 환경(Z_PARK=1 · Z_STOCK_SIDE · Z_ATTR · Z_ACC_VOL=0 · PYTHONPATH · Z_DROP 빈 값)을 물려받지 않음",
      pe["Z_PARK"] == "0" and "Z_STOCK_SIDE" not in pe and "Z_ATTR" not in pe and pe["Z_ACC_VOL"] == "0.010911" and "PYTHONPATH" not in pe and pe["Z_DROP"] == "15m")
old_c = dict(M.ENV_CONTRACT); M.ENV_CONTRACT["Z_LOOK"] = "21"; lk_env = M.lock(); M.ENV_CONTRACT.clear(); M.ENV_CONTRACT.update(old_c)
check("13 환경 계약 값 하나가 바뀌면 잠금이 달라져 옛 DONE을 다시 쓰지 않음", lk_env["env_contract"] != lk["env_contract"] and M.name(M.NOW) not in M.done_bases(lk_env) and M.lock() == lk)
SP2 = TMP / "sp"; SP2.mkdir()
for f in M.SP_FILES:
    shutil.copy(M.SP / f, SP2 / f)
old_sp = M.SP; M.SP = SP2
with open(SP2 / "z055_d1_raw.json", "a") as fh:
    fh.write(" ")
lk_led = M.lock(); M.SP = old_sp
check("14 1일봉 장부(z055_d1_raw.json) 한 바이트가 바뀌면 옛 DONE을 다시 쓰지 않음", M.name(M.NOW) not in M.done_bases(lk_led))
G = TMP / "repo"; (G / "price-data").mkdir(parents=True); (G / "price-data/005930.json").write_text("{}")
sp.run(["git", "init", "-q", str(G)]); sp.run(["git", "-C", str(G), "add", "."]); sp.run(["git", "-C", str(G), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "a"])
old_dirs = M.DATA_DIRS; M.DATA_DIRS = ["price-data"]
(G / "price-data/005930.json").write_text('{"x":1}')
try:
    M.data_trees(G); dirty_stop = False
except SystemExit as e:
    dirty_stop = "커밋 안 된" in str(e)
M.DATA_DIRS = old_dirs
check("15 자료 폴더에 커밋 안 된 바뀜이 있으면 멈춤", dirty_stop)
s54 = (ROOT / "research/mix54_run.py").read_text()
check("16 더 번 몫의 기준 = 15분봉만 뺀 지금 몫 · 덧붙임 없음 · 이웃 상한 갈래마다 300 · 하루 −15 · 달 두 갈래 T10 −10 / T15 −15",
      'tuple(x["g"]) == NOW and x["overlay"] == "none"' in s54 and M.NB_CAP == 300 and M.DAY_LIM == -0.15 and M.TRACKS == {"T10": -0.10, "T15": -0.15})
fk = {"by_kind": {"상승": {"worst_day_raw": -0.05, "worst_month_raw": -0.12}, "하락": {"worst_day_raw": -0.01, "worst_month_raw": -0.01}, "횡보": {"worst_day_raw": -0.151, "worst_month_raw": -0.02}}}
fk2 = {"by_kind": {"상승": {"worst_day_raw": -0.05, "worst_month_raw": -0.12}}}
check("17 달 −12%는 T10 밖 · T15 안 · 하루 −15.1%는 두 갈래 모두 밖", not M.within(fk2, -0.10) and M.within(fk2, -0.15) and not M.within(fk, -0.15))
# 18 고르기 전체(가짜 계좌 셈): C(연 45 · 달 −9.5 · persist 이웃 달 −13) · B(연 40 · 달 −12) · A(연 30 · 달 −9) · 없음(연 20 · 달 −5)
import types
F = types.ModuleType("regime_dev"); F.R0 = {"n": 0}; F.DATA = None; F.FEAT = None
TAB = {None: (0.20, -0.05), 0.2: (0.30, -0.09), 0.4: (0.40, -0.12), 0.3: (0.45, -0.095)}
calls = []
def _acc(cfg):
    calls.append(json.dumps(cfg, sort_keys=True))
    return (cfg,)
def _stats(cfg):
    a, m = TAB[cfg.get("up_lev")]
    if cfg.get("up_lev") == 0.3 and cfg.get("persist") != 3:
        m = -0.13
    return {"annual_raw": a, "annual_pct": a * 100, "worst_day_pct": -3.0, "worst_month_pct": m * 100, "mdd_report_pct": -20.0, "years_pct": {}, "halves_report": {},
            "by_kind": {"상승": {"worst_day_raw": -0.03, "worst_month_raw": m}}}
F.account, F.stats = _acc, _stats
T2 = Path(tempfile.mkdtemp()); M.BASES = T2; M.EVALS_LOG = T2 / "evals.jsonl"; M.BOX = T2
(T2 / f"{M.name(M.NOW)}.csv").write_text("날,NAV,현금\n20170201,100,50\n")
old = (M.grid, M.OVERLAYS, M.verify_all, sys.modules["regime_dev"])
M.grid = lambda: [M.NOW]
M.OVERLAYS = {"none": None, "A": dict(M.RULE, up_lev=0.2, side_inv=0.2), "B": dict(M.RULE, up_lev=0.4, side_inv=0.2), "C": dict(M.RULE, up_lev=0.3, side_inv=0.2)}
M.verify_all = lambda: ({}, {})
sys.modules["regime_dev"] = F
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    M.select()
M.grid, M.OVERLAYS, M.verify_all, sys.modules["regime_dev"] = old
o = json.loads(buf.getvalue())
t10, t15 = o["tracks"]["T10"], o["tracks"]["T15"]
check("18 고르기(가짜 셈): T10은 C(이웃 달 −13 → 탈락) 다음 A가 최종 · T15는 C가 최종 · 같은 이웃은 한 번만 셈(고유 이웃 12 · T10 확인 12 · T15 확인 6)",
      t10["final"]["overlay"] == "A" and t15["final"]["overlay"] == "C" and t10["checked"][0]["robust"] is False and o["neighbor_evals_unique"] == 12
      and t10["neighbor_checks"] == 12 and t15["neighbor_checks"] == 6 and len(calls) == 4 + 12 and t10["within_count"] == 3 and t15["within_count"] == 4)
print(f"모두 {ok}개 통과")
