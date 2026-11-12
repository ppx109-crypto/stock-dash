"""MPOS-0025 A 엔진 연쇄(손익 안 봄): rule.trend_leg의 조용함 문턱을 전체 한 번(G) 대신 그달 첫날 앞 자료만(CALM_MONTH[그달])으로 바꿔
고정 나무 엔진을 한 번 돌리고, 원판 장부와 끝난 매매 줄 · 진입(종목 · 산 날)이 몇 개 다른지만 셈. 손익 · 수익률 출력 없음.
cwd = 고정 나무 · tree_run. 출력: EX_OUT(요약) · EX_OUT.led.json(새 장부 · 손익 칸 포함이나 이 단계에선 집계 안 함)."""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402

RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"
CM = nrl.CALM_MONTH
MODE = os.environ.get("EX_MODE", "MONTH")
_orig = rule.trend_leg


def trend_leg_month(row):
    t = CM[row["date"][:6]]
    if (row.get("변동성") or 99) > t:
        return False
    return (row.get("추세 기울기") or -99) >= rule.SLOPE and (row.get("60일 전 대비") or -99) >= rule.SIXTY


if MODE == "MONTH":
    rule.trend_leg = trend_leg_month


def run():
    rows = []
    for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
        g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=since, apart=nrl.kin, realistic=True, cap=130,
                    detail=True, size=nrl.BASE_SIZE)
        rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in g["매매목록"]]
    return rows


new = run()
sha = hashlib.sha256(json.dumps(new).encode()).hexdigest()
base = [tuple(x) for x in json.load(open(os.environ["EX_LEDGER"]))]
assert hashlib.sha256(json.dumps([list(x) for x in base]).encode()).hexdigest() == RAW_SHA
if MODE == "BASE":
    assert sha == RAW_SHA, "재현 실패"
ent_b = {(r[0], r[1]) for r in base}
ent_n = {(r[0], r[1]) for r in new}
key = lambda r: (r[0], r[1], r[2], r[4])  # noqa: E731  손익 칸 빼고 비교
kb, kn = {key(r) for r in base}, {key(r) for r in new}
first = min([r[1] for r in new if key(r) not in kb] + [r[1] for r in base if key(r) not in kn] or [None], key=lambda x: x or "99999999")
out = {"모드": MODE, "새 장부 지문": sha, "원판과 같음": sha == RAW_SHA, "끝난 매매 줄(원판 · 새)": [len(base), len(new)],
       "진입(종목 · 산 날) 원판만 · 새만 · 같음": [len(ent_b - ent_n), len(ent_n - ent_b), len(ent_b & ent_n)],
       "매매 줄(손익 칸 뺌) 원판만 · 새만": [len(kb - kn), len(kn - kb)], "첫 다른 산 날": first,
       "원판만 진입(앞 10)": sorted(ent_b - ent_n)[:10], "새만 진입(앞 10)": sorted(ent_n - ent_b)[:10]}
json.dump(new, open(os.environ["EX_OUT"] + ".led.json", "w"))
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
