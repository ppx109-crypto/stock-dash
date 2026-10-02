"""K 2회차(K7) — 대상 넓히기: 코스닥 상장 전체(kosdaq-data · 한투 마스터 1,708종목 · 2015~)에서 **그날의 코스닥 거래대금 상위 100**.
K1(지금 큰 코스닥 101종목)은 '그동안 오른 종목만' 모인 치우침이 컸음 → 그때그때 거래가 많던 종목(지금은 작아진 종목 포함)으로 다시.
순위 = 전날까지 20거래일 평균 거래대금(그날 값 안 씀). 시장 폭 = 그 100종목 안 50일선 > 200일선 몫(코스닥 안).
남은 치우침: 한투 마스터는 지금 상장 종목만 → 그사이 상장폐지된 종목은 없음(K8 · KRX Open API로 메울 것).
판: ① 지금 규칙 그대로(수급 가르침 포함 — 수급 자료 없는 종목은 못 삼) ② 가르침 뺌 ③ 가르침 뺌 · 조용함 문턱 코스닥 줄 ④ 정배열 문만 · 가르침 뺌.
씨앗 8 · 두 반 · 비용은 엔진 기본(realistic)."""
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import caps
import final_group
import final_study as FS
import lab
import nrl

rule = nrl.rule
ROOT = Path("/home/user/stock-dash")
TOP = 100

# ── 코스닥 일봉 · 거래대금 ──
prices, value = {}, {}
for p in sorted((ROOT / "kosdaq-data").glob("*.json")):
    try:
        b = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        continue
    cols = b.get("cols") or []
    if "종가" not in cols or "거래대금" not in cols:
        continue
    ic, iv = cols.index("종가"), cols.index("거래대금")
    rows = [(str(r[0]), float(r[ic]), float(r[iv] or 0)) for r in b.get("rows") or [] if r[ic]]
    if len(rows) < 250:
        continue
    prices[b["code"]] = {"name": b.get("name") or b["code"], "rows": [(d, c) for d, c, _ in rows]}
    value[b["code"]] = rows
print(f"== K 2회차(K7): 코스닥 일봉 {len(prices)}종목(받은 만큼) ==", flush=True)

# 날마다 '전날까지 20일 평균 거래대금' 상위 100
days = sorted({d for v in value.values() for d, _, _ in v})
dix = {d: i for i, d in enumerate(days)}
avg = {}
for code, rows in value.items():
    v = np.array([x for _, _, x in rows])
    cs = np.concatenate([[0.0], np.cumsum(v)])
    for k in range(21, len(rows)):
        avg.setdefault(rows[k][0], []).append(((cs[k] - cs[k - 20]) / 20, code))   # k 앞 20일(전날까지)
top = {}
for d, lst in avg.items():
    lst.sort(reverse=True)
    top[d] = {c: n + 1 for n, (_, c) in enumerate(lst[:TOP])}
ever = sorted({c for v in top.values() for c in v if v and True})
ever = [c for c in ever if any(c in top.get(d, {}) for d in days if d >= "20161001")]
print(f"  2016-10 뒤 하루라도 상위 {TOP}에 든 종목 {len(ever)}", flush=True)

# ── 엔진 판을 코스닥으로 바꿔 끼움 ──
kq_prices = {c: prices[c] for c in ever}
nrl.prices.clear()
nrl.prices.update(kq_prices)
nrl.lanes.clear()
nrl.lanes.update(lab.lanes(kq_prices))
nrl.kin = rule.apart(kq_prices)
pool = []
for k in range(0, len(ever), 20):
    part = {c: kq_prices[c] for c in ever[k:k + 20]}
    for r in lab.build(part, horizons=(0,)):
        if r["date"] < "20161001":
            continue
        n = top.get(r["date"], {}).get(r["code"])
        if n is None:
            continue
        r[caps.RANK] = n
        pool.append(r)
print(f"  그날 상위 {TOP} 줄 {len(pool)}", flush=True)
nrl.shape.clear()
nrl.shape.update(FS.shapes(nrl.lanes, ever))
nrl.BR.clear()
nrl.BR.update(FS.breadth_by_day(pool, nrl.shape))
have_flow = 0
for c in ever:
    if c not in nrl.FLOW:
        fr = final_group.flow_rows(c)
        if fr:
            nrl.FLOW[c] = nrl.flow_entry(fr)
    have_flow += c in nrl.FLOW
print(f"  수급 자료 있는 종목 {have_flow}/{len(ever)}", flush=True)
nrl.target_cut = lambda r, back_days=45: False       # 코스닥 목표가 자료 없음


def run(tag, holds, seeds=8):
    out = [f"  {tag:30s}"]
    for side, lo, hi in (("앞", "20170101", rule.MID), ("뒤", rule.MID, "20991231")):
        sub = [r for r in pool if lo <= r["date"] < hi]
        g = lab.wobble(sub, nrl.prices, holds, nrl.BASE_EXIT, tries=seeds, slots=nrl.SLOTS, since=lo, apart=nrl.kin,
                       realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE, rank=rule.order)
        out.append(f"{side} " + nrl.line(g, nrl.SLOTS, lo))
    print(" | ".join(out), flush=True)


door = lambda r: rule.holds(r) or nrl.aligned(r)
run("① 지금 규칙(가르침 포함)", lambda r: door(r) and nrl.teacher(r))
run("② 가르침 뺌", door)
vals = sorted(r["변동성"] for r in pool if r.get("변동성") is not None)
calm_kq = vals[int(len(vals) * rule.CALM)]
old = rule._calm
rule._calm = calm_kq
run(f"③ 가르침 뺌 · 조용함 코스닥 줄({old:.2f}→{calm_kq:.2f})", door)
rule._calm = old
run("④ 정배열 문만 · 가르침 뺌", nrl.aligned)
print("끝", flush=True)
