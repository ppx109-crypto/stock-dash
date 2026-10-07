"""시험이 헐겁지 않은지 보는 확인: 커널 사본에 일부러 결함을 넣고 골든이 FAIL을 내는지 봄.
사용: python3 -I tests/mutation_check.py <REPLAY-0001 폴더> <결과 json>  (원본 파일은 바꾸지 않음, 임시 폴더 사용)"""
import os, sys, json, shutil, subprocess, tempfile
ROOT = os.path.abspath(sys.argv[1]); OUT = sys.argv[2]
MUT = [
 ("fee_half_even", "rounding=ROUND_HALF_UP)", "rounding=__import__('decimal').ROUND_HALF_EVEN)"),
 ("no_cost_in_sizing", "q = floor_int(limit / (px * (1 + fee)))", "q = floor_int(limit / px)"),
 ("no_cash_check", "if total > self.cash:", "if False:"),
 ("dup_fill_applied", "self.duplicates_ignored += 1\n                return", "self.duplicates_ignored += 1"),
 ("accept_moves_cash", "o[\"state\"], o[\"remaining\"] = \"OPEN\", o[\"qty\"]", "o[\"state\"], o[\"remaining\"] = \"OPEN\", o[\"qty\"]; self.cash -= 1"),
 ("ignore_ambiguous", "    if ambiguous:\n        return None, ambiguous", "    if False:\n        return None, ambiguous"),
 ("stale_ok", "if best[\"as_of\"].date() < d:", "if False:"),
 ("flow_as_pnl", "r = (nav - fe) / (nav_prev + fs) - 1", "r = nav / (nav_prev if nav_prev else fs) - 1"),
 ("limit_le", "if any(v < LIMIT for v in known):", "if any(v <= LIMIT for v in known):"),
 ("no_sell_tax", "won(notional * self.cost[\"sell_tax\"])", "ZERO"),
 ("use_correction", "cand = [p for p in self.prices.get(sec, []) if p[\"avail\"] <= m and p[\"as_of\"] <= m]",
  "cand = [p for p in self.prices.get(sec, []) if p[\"as_of\"] <= m]"),
 # 아래 둘은 1차 확인에서 안 잡힌 두 변형(no_cost_in_sizing: 줄이기 반복문이 같은 결과를 냄, use_correction: 사건을 시간순으로
 # 처리하므로 공개 전 가격은 아직 없음)과 같은 결함을 "같은 결과가 나지 않게" 다시 넣은 것
 ("ignore_cost_in_sizing", "while q > 0 and q * px + won(q * px * fee) > limit:", "q = floor_int(limit / px)\n            while q > 0 and q * px > limit:"),
 ("restate_past_nav", "\"price\": p, \"snapshot_date\": m[\"date\"], \"applied\": False})",
  "\"price\": p, \"snapshot_date\": m[\"date\"], \"applied\": False}); m[\"nav\"] = m[\"cash_td\"] + m[\"positions\"][sec] * p"),
 ("pooled_oversell", "if lot is None or q > lot[\"qty\"]:", "if q > self.held().get(e[\"security_id\"], 0):"),
]
src = open(os.path.join(ROOT, "account_kernel.py"), encoding="utf-8").read()
res = []
for name, a, b in MUT:
    assert src.count(a) >= 1, name
    d = tempfile.mkdtemp()
    shutil.copytree(os.path.join(ROOT, "fixtures"), os.path.join(d, "fixtures"))
    open(os.path.join(d, "account_kernel.py"), "w", encoding="utf-8").write(src.replace(a, b, 1))
    p = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tests", "run_golden.py"), d, os.path.join(d, "r.json")],
                       capture_output=True, text=True, timeout=60)
    try:
        r = json.load(open(os.path.join(d, "r.json")))
        failed = [c["case"] for c in r["cases"] if not c["pass"]]
        v = r["kernel_verdict"]
    except Exception as x:
        failed, v = ["CRASH"], "CRASH:" + p.stderr.strip().splitlines()[-1][:120] if p.stderr.strip() else "CRASH"
    res.append({"mutation": name, "verdict": v, "failed_cases": failed, "caught": v != "VERIFIED_SYNTHETIC"})
    shutil.rmtree(d)
json.dump({"mutations": res, "all_caught": all(x["caught"] for x in res)}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for x in res:
    print(x["mutation"], x["caught"], x["failed_cases"])
