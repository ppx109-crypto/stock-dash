"""MIX-0053 합성 시험 — 격자 · 실행 설정 · 지금 조합 재현 · 덧붙임 설정 · 잣대 · 바탕 장부 바꾸기."""
import csv, json, os, sys
from pathlib import Path
os.environ["REG_BOX"] = "MIX-0053"
sys.path.insert(0, "/home/user/stock-dash/research")
import mix_run as M
import regime_dev as D
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
check("1 격자 = 4 × 2 × 3 × 3 = 72 · 지금 조합(0.5 · 0.5 · 0.5 · 둘 다)이 격자 안", len(M.grid()) == 72 and M.NOW in M.grid())
e = M.base_cmd((0.7, 1.0, 0.0, "engine,inverse"))
check("2 바구니 0이면 Z_DROP에 basket · 엔진 · 인버스 뺌도 함께 · 몫 칸 · 흔들림 상한 m1", e["Z_DROP"] == "engine,inverse,basket" and e["Z_SHARE_1D"] == "0.7" and e["Z_SHARE_15M"] == "1.0" and e["Z_ACC_VOL"] == "0.010911")
e2 = M.base_cmd(M.NOW)
check("3 지금 조합은 아무것도 안 뺌", e2["Z_DROP"] == "" and e2["Z_SHARE_BASKET"] == "0.5")
SCR = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/s44/z100_default.csv")
a = list(csv.DictReader(open(SCR))); b = list(csv.DictReader(open("/home/user/stock-dash/research-exchange/claude-to-gpt/REGIME-SW-0048/base_m1.csv")))
check("4 z100 기본값(지금 조합) = 지금 장부 base_m1.csv와 2,360줄 모두 같음(NAV 원 단위)", len(a) == len(b) == 2360 and all(x["날"] == y["날"] and abs(float(x["NAV"]) - float(y["NAV"])) <= 0.5 for x, y in zip(a, b)))
import tempfile, shutil
TMP = Path(tempfile.mkdtemp()); M.BASES = TMP; M.EVALS_LOG = TMP / "evals.jsonl"; M.BASES_LOG = TMP / "bases.jsonl"
shutil.copy(SCR, TMP / f"{M.name(M.NOW)}.csv")
check("5 덧붙임 넷 = 없음 · 0050 · 0051 · 0052 설정 그대로", M.OVERLAYS["none"] is None and M.OVERLAYS["0050"]["n"] == 30 and M.OVERLAYS["0050"]["up_lev"] == 0.3
      and M.OVERLAYS["0051"]["up_lev"] == 0.2 and M.OVERLAYS["0052"]["side_inv"] == 0.3 and all(M.OVERLAYS[k]["confirm"] == "r10m5" for k in ("0050", "0051", "0052")))
r = M.evaluate(M.NOW, M.OVERLAYS["0052"], D)
check("6 바탕 장부를 바꿔 끼우는 셈: 지금 조합 + 0052 = 28.633%(앞 결과 그대로)", abs(r["annual_pct"] - 28.633) < 1e-9)
fake = {"by_kind": {"상승": {"worst_day_raw": -0.15, "worst_month_raw": -0.10}, "하락": {"worst_day_raw": -0.01, "worst_month_raw": -0.01}, "횡보": {"worst_day_raw": -0.01, "worst_month_raw": -0.1000001}}}
check("7 잣대는 반올림 전 · 세 장 모두(횡보 −0.1000001 → 밖)", not M.within(fake))
src = Path("/home/user/stock-dash/research/z100.py").read_text()
check("8 z100: 얼린 봇 판(research/mix0053)이 먼저 · 몫 칸 셋", 'ROOT / "research" / "mix0053"' in src and "SHARE_15M * s / 10" in src and "SHARE_BASKET - d1v" in src)
# round 2(GPT #221 무결성)
ok1, info = M.check_csv(TMP / f"{M.name(M.NOW)}.csv")
check("9 장부 점검: 2,360줄 · 첫날 20170201 · 마지막 20260916 · 날짜 고유 · 정렬 → 통과", ok1 and info["rows"] == 2360)
bad = TMP / "bad.csv"; bad.write_text("\n".join(open(TMP / f"{M.name(M.NOW)}.csv").read().splitlines()[:1000]))
check("10 잘린 장부(999줄)는 점검 실패", not M.check_csv(bad)[0])
recs = [json.loads(l) for l in M.EVALS_LOG.read_text().splitlines()]
check("11 평가마다 EVALS_LOG에 STARTED → DONE(바탕 · 덧붙임 열쇠)", [x["status"] for x in recs] == ["STARTED", "DONE"] and "d0.5_m0.5_b0.5_xnone" in recs[0]["key"])
lk = M.lock()
M.log(M.BASES_LOG, {"status": "DONE", "cell": M.name(M.NOW), "lock": lk, "sha256": M.sha(TMP / f"{M.name(M.NOW)}.csv")})
check("12 같은 잠금의 DONE만 끝난 칸으로 셈 · 잠금이 다르면 아님", M.name(M.NOW) in M.done_bases(lk) and M.name(M.NOW) not in M.done_bases(dict(lk, x="다름")))
try:
    M.verify_all(); stopped = False
except SystemExit as e:
    stopped = "71개" in str(e)
check("13 72개 가운데 하나라도 DONE · 파일 sha가 없으면 고르기 전에 멈춤(지금 71개 모자람)", stopped)
check("14 잠금에 z100 · 얼린 봇 둘 · perf2 · idle_signal · nrl · 캐시 해시", {"research/z100.py", "research/mix0053/basket_live.py", "research/mix0053/idle_live.py", "nrl.py", M.CACHE} <= set(lk))
# round 3(GPT #221 · 환경 · 외부 장부 잠금)
pe = M.base_cmd(M.NOW, parent={"PATH": "/usr/bin", "Z_PARK": "1", "Z_STOCK_SIDE": "x", "Z_ATTR": "/tmp/a.csv", "Z_ACC_VOL": "0", "PYTHONPATH": "/evil", "Z_FROM": "20200101"})
check("15 부모 환경(Z_PARK=1 · Z_STOCK_SIDE · Z_ATTR · Z_ACC_VOL=0 · PYTHONPATH · Z_FROM)은 물려받지 않고 등록값으로 고정",
      pe["Z_PARK"] == "0" and "Z_STOCK_SIDE" not in pe and "Z_ATTR" not in pe and pe["Z_ACC_VOL"] == "0.010911" and "PYTHONPATH" not in pe
      and pe["Z_FROM"] == "20170201" and pe["PATH"] == "/usr/bin" and set(M.research_env(pe)) == set(M.ENV_CONTRACT) | set(M.CELL_KEYS) | {"Z_OUT", "PYTHONHASHSEED"})
old_c = dict(M.ENV_CONTRACT); M.ENV_CONTRACT["Z_LOOK"] = "21"; lk_env = M.lock(); M.ENV_CONTRACT.clear(); M.ENV_CONTRACT.update(old_c)
check("16 환경 계약 값 하나(Z_LOOK 20 → 21)가 바뀌면 잠금이 달라져 옛 DONE을 다시 쓰지 않음",
      lk_env["env_contract"] != lk["env_contract"] and M.name(M.NOW) not in M.done_bases(lk_env) and M.lock() == lk)
SP2 = TMP / "sp"; SP2.mkdir()
for f in M.SP_FILES:
    shutil.copy(M.SP / f, SP2 / f)
old_sp = M.SP; M.SP = SP2
same = M.lock() == lk
with open(SP2 / "x004_m15_final.json", "a") as fh:
    fh.write(" ")
lk_led = M.lock(); M.SP = old_sp
check("17 외부 장부(x004_m15_final.json) 한 바이트가 바뀌면 잠금이 달라져 옛 DONE을 다시 쓰지 않음(같은 내용 복사본은 같은 잠금)",
      same and lk_led["SP/x004_m15_final.json"] != lk["SP/x004_m15_final.json"] and M.name(M.NOW) not in M.done_bases(lk_led))
import subprocess as sp
G = TMP / "repo"; (G / "price-data").mkdir(parents=True); (G / "price-data/005930.json").write_text("{}")
sp.run(["git", "init", "-q", str(G)]); sp.run(["git", "-C", str(G), "add", "."]); sp.run(["git", "-C", str(G), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "a"])
old_dirs = M.DATA_DIRS; M.DATA_DIRS = ["price-data"]
t1 = M.data_trees(G)["price-data"]
(G / "price-data/005930.json").write_text('{"x":1}')
try:
    M.data_trees(G); dirty_stop = False
except SystemExit as e:
    dirty_stop = "커밋 안 된" in str(e)
sp.run(["git", "-C", str(G), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "b"])
t2 = M.data_trees(G)["price-data"]; M.DATA_DIRS = old_dirs
check("18 자료 폴더: 커밋 안 된 바뀜이 있으면 멈춤 · 커밋하면 나무 해시가 달라짐(→ 잠금이 달라짐)", dirty_stop and t1 and t2 and t1 != t2)
check("19 잠금 = 코드(루트 *.py · z100 · z001 · perf2 · idle_signal · 얼린 봇) + 캐시 + 장부 둘 + 자료 폴더 나무 + 환경 계약",
      {"research/z001.py", "lab.py", "caps.py", "SP/z055_d1_raw.json", "SP/x004_m15_final.json", "tree:price-data", "tree:etf-data", "tree:market-data", "env_contract"} <= set(lk))
print(f"모두 {ok}개 통과")
