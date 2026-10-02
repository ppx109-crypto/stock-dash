"""F 3회차 — 수급을 추세와 함께: 1일봉 후보 문(추세 문 또는 정배열 문 · 목표가 내림 아님) 안에서 수급 조합이 뒤 성적을 바꾸나.
Q_PART=1: 문 안 행(그날 시총 100위)의 수급 조합별 앞으로 5 · 20 · 60일 시장 넘는 수익(ftools 표 · 전날까지 5일 순매수).
Q_PART=2 · 3: 1일봉 엔진(ntools.once · 씨앗 8 · 새 82 그대로)에서 수급 조건(가르침 = 외+ 투+ 개−)만 바꿔 매매."""
import bisect
import json
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl

rule = nrl.rule
door = lambda r: (rule.holds(r) or nrl.aligned(r)) and not nrl.target_cut(r)

PG = {}
for code in nrl.lanes:
    try:
        rows = json.load(open(f"program-data/{code}.json", encoding="utf-8"))["rows"]
    except (OSError, ValueError, KeyError):
        continue
    ds = [r["date"] for r in rows if r.get("순매수량") is not None]
    acc = np.concatenate([[0.0], np.cumsum([r["순매수량"] for r in rows if r.get("순매수량") is not None])])
    PG[code] = (ds, acc)


def prog(r, n=5):
    got = PG.get(r["code"])
    if not got:
        return None
    ds, acc = got
    k = bisect.bisect_left(ds, r["date"])
    return acc[k] - acc[k - n] if k >= n else None


fs = lambda r, c, n=5: nrl.flow_sum(r, n, c)


def sign(v):
    return None if v is None else (1 if v > 0 else -1)


CONDS = {
    "조건 없음(문만)": lambda r: True,
    "가르침(외+ 투+ 개−) = 지금": lambda r: nrl.teacher(r),
    "외+": lambda r: sign(fs(r, "외국인")) == 1,
    "투+": lambda r: sign(fs(r, "투신")) == 1,
    "개−": lambda r: sign(fs(r, "개인")) == -1,
    "외+ 투+": lambda r: sign(fs(r, "외국인")) == 1 and sign(fs(r, "투신")) == 1,
    "외+ 개−": lambda r: sign(fs(r, "외국인")) == 1 and sign(fs(r, "개인")) == -1,
    "기관+ 개−": lambda r: sign(fs(r, "기관")) == 1 and sign(fs(r, "개인")) == -1,
    "외+ 기관+": lambda r: sign(fs(r, "외국인")) == 1 and sign(fs(r, "기관")) == 1,
    "연기금+": lambda r: sign(fs(r, "연기금")) == 1,
    "사모+": lambda r: sign(fs(r, "사모")) == 1,
    "프로그램+": lambda r: sign(prog(r)) == 1,
    "가르침 + 프로그램+": lambda r: nrl.teacher(r) and sign(prog(r)) == 1,
    "가르침 + 연기금+": lambda r: nrl.teacher(r) and sign(fs(r, "연기금")) == 1,
    "가르침 + 사모+": lambda r: nrl.teacher(r) and sign(fs(r, "사모")) == 1,
    "가르침 3일": lambda r: nrl.teacher(r, 3),
    "가르침 10일": lambda r: nrl.teacher(r, 10),
    "가르침 20일": lambda r: nrl.teacher(r, 20),
    "가르침 아님": lambda r: not nrl.teacher(r),
    "외− 개+(반대)": lambda r: sign(fs(r, "외국인")) == -1 and sign(fs(r, "개인")) == 1,
}
part = os.environ.get("Q_PART", "1")
print(f"== F 3회차({part}): 1일봉 후보 문 안에서 수급 조합 ==", flush=True)
if part == "1":
    import ftools as F
    tab = F.pit(F.build(5))
    key = {(c, d): i for i, (c, d) in enumerate(zip(tab["code"], tab["day"]))}
    rows = [r for r in nrl.inside if door(r) and (r["code"], r["date"]) in key]
    print(f"  문 안 행 {len(rows)} (그날 시총 100위 · 2017 ~ )", flush=True)
    for name, cond in CONDS.items():
        idx = [key[(r["code"], r["date"])] for r in rows if cond(r)]
        m = np.zeros(len(tab["day"]), bool)
        m[idx] = True
        F.show(tab, m, name, 30)
else:
    import ntools as T
    names = list(CONDS)
    pick = names[:10] if part == "2" else names[10:]
    for name in pick:
        cond = CONDS[name]
        T.once(name, holds=lambda r, cond=cond: door(r) and cond(r))
print("끝", flush=True)
