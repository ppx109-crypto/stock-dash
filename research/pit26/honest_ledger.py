"""1일봉 장부(RECOUNT.md 2절): ntools.once('일봉 새 82회차')의 씨앗 0 판(lab.wobble 첫 판 = lab.run)과 같은 인자로 매매 목록을 만듦.
EX_MODE=BASE  : 옛 NRL 캐시 그대로 → z055_d1_raw(0ec97a14…)와 바이트까지 같아야 함(아니면 종료값 3).
EX_MODE=HONEST: NRL_CACHE = 정직 NRL 캐시 · rule.trend_leg = 정직 달 문턱(EX_FULL의 T).
출력 EX_OUT = [(종목, 산 날, 판 날, 손익%(비용 뺌), 칸)]. cwd = 고정 나무 · tree_run. 성과 요약 출력 없음."""
import hashlib
import json
import os
import pickle
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
HC = os.environ["EX_HC"]
ns = {"__name__": "honest_cache", "__file__": HC}
exec(compile(open(HC, encoding="utf-8").read(), HC, "exec"), ns)
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402

MODE, OUT = os.environ["EX_MODE"], os.environ["EX_OUT"]
if MODE == "HONEST":
    rule.trend_leg = ns["trend_leg_with"](pickle.load(open(os.environ["EX_FULL"], "rb"))["T"])
rows = []
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, rank=rule.order, slots=nrl.SLOTS, since=since, apart=nrl.kin,
                realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE)
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for t in g["매매목록"]]
json.dump(rows, open(OUT, "w"))
sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
print(json.dumps({"모드": MODE, "매매": len(rows), "장부 지문": sha, "FLOW 종목": len(nrl.FLOW), "TARGETS 종목": len(nrl.TARGETS),
                  "inside 행": len(nrl.inside)}, ensure_ascii=False))
if MODE == "BASE" and sha != "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99":
    sys.exit(3)
