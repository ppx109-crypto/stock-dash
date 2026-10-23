"""1일봉 장부(RECOUNT.md 2절): ntools.once('일봉 새 82회차')의 씨앗 0 판(lab.wobble 첫 판 = lab.run)과 같은 인자로 매매 목록을 만듦.
EX_MODE=BASE  : 옛 NRL 캐시 그대로 → z055_d1_raw(0ec97a14…)와 바이트까지 같아야 함(아니면 종료값 3).
EX_MODE=HONEST: NRL_CACHE = 정직 NRL 캐시 · rule.trend_leg = 정직 달 문턱(EX_FULL의 T).
EX_TEACH(생존 편향 판 · SURVIVOR.md): rate | all — EX_FULL['missing'] 종목(수급 자료 없음) 행의 teacher를 기본률 p(씨앗 해시) 또는 늘 참으로.
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
TEACH = os.environ.get("EX_TEACH", "")
info = {}
if TEACH:
    import hashlib as _h
    side_pk = pickle.load(open(os.environ["EX_FULL"], "rb"))
    MISS = set(side_pk["missing"])
    _teacher = nrl.teacher
    base = [r for r in nrl.inside if r["date"] >= "20200102" and r["code"] not in MISS and (rule.holds(r) or nrl.aligned(r)) and not nrl.target_cut(r)]
    p = sum(1 for r in base if _teacher(r)) / len(base)
    info = {"teacher 기본률 p": round(p, 4), "기본률 모집단 행": len(base), "가정": TEACH}

    def teacher(r, n=5):
        if r["code"] in MISS and r["code"] not in nrl.FLOW:
            if TEACH == "all":
                return True
            u = int(_h.sha256(f"{r['code']}|{r['date']}|20261018".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
            return u < p
        return _teacher(r, n)
    nrl.teacher = teacher
rows = []
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, rank=rule.order, slots=nrl.SLOTS, since=since, apart=nrl.kin,
                realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE)
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for t in g["매매목록"]]
json.dump(rows, open(OUT, "w"))
sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
print(json.dumps({"모드": MODE, "매매": len(rows), "장부 지문": sha, "FLOW 종목": len(nrl.FLOW), "TARGETS 종목": len(nrl.TARGETS),
                  "inside 행": len(nrl.inside), **info,
                  "빠진 종목 매매": sum(1 for t in rows if t[0] in (MISS if TEACH else set()))}, ensure_ascii=False))
if MODE == "BASE" and sha != "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99":
    sys.exit(3)
