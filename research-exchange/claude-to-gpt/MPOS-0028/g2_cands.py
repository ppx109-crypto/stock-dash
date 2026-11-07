"""G2_TURNOVER.md 1절: 연속 장부(honest_ledger.py · EX_MODE=HONEST · EX_CONT=1)를 같은 프로세스로 다시 돌려 장부 지문을 확인한 뒤,
lab.run의 경쟁 후보 전체(BASE_HOLD 참 · 날 ≥ SINCE)를 (종목, 날, 순위 열쇠)로 내보냄. 가격 수익 · 손익은 내보내지 않음.
cwd = 고정 나무 · tree_run. 환경: honest_ledger.py와 같음 + G2_OUT."""
import hashlib
import json
import os
import runpy

HERE = os.path.dirname(os.path.realpath(__file__))
g = runpy.run_path(os.path.join(HERE, "honest_ledger.py"), run_name="honest_ledger")
sha = hashlib.sha256(open(os.environ["EX_OUT"], "rb").read()).hexdigest()
assert sha == "c97b1b9a4c7674c29081b1176006e31df5704ce74951735ac2a07691575e8f1a", sha
nrl, rule = g["nrl"], g["rule"]
seen, cands = set(), []
for r in nrl.inside:
    if r["date"] >= rule.SINCE and nrl.BASE_HOLD(r):
        k = (r["code"], r["date"])
        if k in seen:
            continue
        seen.add(k)
        cands.append([r["code"], r["date"], float(rule.order(r))])
bought = sorted({(t[0], t[1]) for t in g["rows"]})
json.dump({"후보": sorted(cands), "산 것": bought, "장부 지문": sha}, open(os.environ["G2_OUT"], "w"), ensure_ascii=False)
print(json.dumps({"후보": len(cands), "산 (종목, 날)": len(bought), "장부 지문": sha}, ensure_ascii=False))
