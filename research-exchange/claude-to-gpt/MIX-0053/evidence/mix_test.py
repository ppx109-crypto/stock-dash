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
print(f"모두 {ok}개 통과")
