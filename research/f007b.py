"""F 7b — 2006 ~ 2016(2008 · 2011 약세장 포함)에 진짜 1일봉 규칙(새 82 · 씨앗 8)을 돌림: 가르침(외+ 투+ 개−)이 있을 때 · 없을 때.
대상: investor-full에 받아진 종목 · 그날 순위 = 전날까지 20일 평균 거래대금 순위(주식수 자료가 2016부터라 시총 대신 · 미래 참조 없음).
일봉 재료는 lab.build로 종목 묶음마다 새로 만듦(4GB 표를 통째로 풀지 않으려고). 수급은 investor-full(전날까지).
'조용함' 문턱은 2017 ~ 표의 것을 그대로(문턱을 이 기간에 다시 맞추지 않음). 목표가 거르기는 이 기간 자료가 거의 없어 사실상 꺼짐."""
import bisect
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import caps
import final_study as FS
import lab
import nrl

rule = nrl.rule
LO_D, HI_D = "20051001", "20170101"
codes = sorted(Path(p).stem for p in glob.glob("investor-full/*.json"))
codes = [c for c in codes if c in nrl.prices]
# 1) 일봉 재료(2005-10 ~ 2016)
rows = []
for k in range(0, len(codes), 25):
    part = {c: nrl.prices[c] for c in codes[k:k + 25]}
    for r in lab.build(part, horizons=(0,)):
        if LO_D <= r["date"] < HI_D:
            rows.append(r)
print(f"재료 줄 {len(rows)} · 종목 {len(codes)}", flush=True)
# 2) 그날 순위 = 전날까지 20일 평균 거래대금
TV = {}
for c in codes:
    v = json.loads(Path(f"volume-data/{c}.json").read_text(encoding="utf-8"))["날"]
    ds = [x[0] for x in v]
    acc = np.concatenate([[0.0], np.cumsum([x[2] if len(x) > 2 and x[2] else 0.0 for x in v])])
    TV[c] = (ds, acc)


def tv20(code, day):
    ds, acc = TV[code]
    k = bisect.bisect_left(ds, day)          # 전날까지
    return (acc[k] - acc[k - 20]) / 20 if k >= 20 else None


by_day = {}
for r in rows:
    v = tv20(r["code"], r["date"])
    if v:
        r["_tv"] = v
        by_day.setdefault(r["date"], []).append(r)
for d, rs in by_day.items():
    rs.sort(key=lambda x: -x["_tv"])
    for place, x in enumerate(rs, 1):
        x[caps.RANK] = place
# 3) 정배열 모양 · 시장 폭 · 수급을 nrl에 더함(2017 ~ 것은 그대로)
new_shape = FS.shapes(nrl.lanes, [c for c in codes if c not in nrl.shape])
nrl.shape.update(new_shape)
for d, v in FS.breadth_by_day(rows, nrl.shape).items():
    nrl.BR.setdefault(d, v)
for c in codes:
    body = json.loads(Path(f"investor-full/{c}.json").read_text(encoding="utf-8"))
    cols = body["cols"]
    fr = [dict(zip(cols, r)) for r in body["rows"] if r[0] < "20170101"]
    fr = [dict(x, date=x["date"]) for x in fr]
    old = nrl.FLOW.get(c)
    if old:   # 2017 ~ 은 지금 표 그대로 이어 붙임(앞쪽만 새로)
        days, acc, ok, closes = old
        tail = [{"date": d, **{col: acc[col][i + 1] - acc[col][i] for col in nrl.COLS}, "종가": closes[i]} for i, d in enumerate(days)]
        fr = fr + [x for x in tail if x["date"] >= "20170101"]
    nrl.FLOW[c] = nrl.flow_entry(fr)
pool = [r for r in rows if caps.inside(r, rule.TOP) and r["date"] >= "20060101"]
print(f"대상 안 줄 {len(pool)} · 하루 평균 {len(pool) / max(1, len({r['date'] for r in pool})):.0f}종목", flush=True)
HOLD_NOW = nrl.BASE_HOLD
HOLD_NO = lambda r: (rule.holds(r) or nrl.aligned(r)) and not nrl.target_cut(r)
HOLD_REV = lambda r: HOLD_NO(r) and not nrl.teacher(r)
SPANS = (("2006 ~ 2010", "20060101", "20110101"), ("2011 ~ 2016", "20110101", "20170101"))
print("== F 7b: 2006 ~ 2016 진짜 1일봉 규칙 ==", flush=True)
for tag, holds in (("지금(새 82 · 가르침 있음)", HOLD_NOW), ("가르침 뺌(문만)", HOLD_NO), ("가르침 아닌 것만", HOLD_REV)):
    out = [f"  {tag:26s}"]
    for name, lo, hi in SPANS:
        sub = [r for r in pool if lo <= r["date"] < hi]
        g = lab.wobble(sub, nrl.prices, holds, nrl.BASE_EXIT, tries=8, slots=nrl.SLOTS, since=lo, apart=nrl.kin,
                       realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE, rank=rule.order)
        out.append(f"{name} " + nrl.line(g, nrl.SLOTS, lo))
    print(" | ".join(out), flush=True)
print("끝", flush=True)
