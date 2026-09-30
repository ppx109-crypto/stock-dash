"""1시간봉 95회차(실시간 모듈 검증) — hourly_a.py의 step · fill을 과거 봉에 한 봉씩 흘려 넣어(되감기) 연구 엔진(90회차 규칙: 자리 바꾸기 폭<90 +
같은 봉 후보 순서)과 같은 매매를 하는지 견줌. 날마다 후보(plan)는 연구의 전 거래일 재료(ATT)로 만들고, 정배열 깨짐은 그날 마지막 봉 뒤에 다음 날 재료로 봄.
견줌: 같은 매매(종목 · 산 봉)의 몫 · 연수익. 연구 엔진은 같은 무리 안을 무작위로, 실시간은 해시로 흔들어 완전히 같지는 않음."""
import sys, json, bisect
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import final_group as FG
import hourly_a as A
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
LO, HI = sys.argv[1] if len(sys.argv) > 1 else "2024010100", sys.argv[2] if len(sys.argv) > 2 else "2024070100"
ROWS = {}
def rows(c):
    if c not in ROWS:
        px = json.load(open(f"price-data/{c}.json", encoding="utf-8"))["closes"]
        vv = json.load(open(f"volume-data/{c}.json", encoding="utf-8"))["날"]
        fl = sorted(FG.flow_rows(c), key=lambda x: x["date"])
        ROWS[c] = ([x[0] for x in px], [float(x[1]) for x in px], [x[0] for x in vv], [float(x[1]) for x in vv], [x["date"] for x in fl], fl)
    return ROWS[c]
def feat(c, day):
    pd_, pc, vd, vol, fd, fl = rows(c)
    i = bisect.bisect_left(pd_, day) - 1; j = bisect.bisect_left(vd, day) - 1; f = bisect.bisect_left(fd, day) - 1
    r20 = pc[i] / pc[i - 20] - 1 if i >= 20 and pc[i - 20] > 0 else None
    av = np.mean(vol[j - 19:j + 1]) if j >= 20 else None
    s5 = sum((x.get("외국인") or 0) + (x.get("투신") or 0) for x in fl[max(0, f - 4):f + 1]) if f >= 4 else None
    return (s5 / av if (s5 is not None and av) else None), r20
# 연구 엔진(90회차 순서)
KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
sc = {}
for c, k in KEYS:
    b = data[c]; day = b["t"][k + 1][:8] if k + 1 < len(b["t"]) else b["t"][k][:8]
    sc[(c, k)] = feat(c, day)
T = {}
bybar = {}
for z in sc: bybar.setdefault(data[z[0]]["t"][z[1]], []).append(z)
for t, L in bybar.items():
    got = A.order_tiers({z[0]: {"flow5": sc[z][0], "r20": sc[z][1]} for z in L})
    for z in L: T[z] = got[z[0]]
def rk(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, -T.get((c, k), 2))
res = H.simulate(data, e_align_or_noon, EX, size, rank=rk, stale_of=stale90, seeds=8, periods=(("구간", (LO, HI)),))
eng = res["구간"]
print(f"== 95회차 (실시간 모듈 되감기 검증 {LO[:8]} ~ {HI[:8]}) ==", flush=True)
print("  연구 엔진(씨앗 8 가운데): " + H.line(res), flush=True)
# 되감기
times = sorted({t for b in data.values() for t in b["t"] if LO <= t < HI})
days = sorted({t[:8] for t in times})
idx = {c: {t: i for i, t in enumerate(b["t"])} for c, b in data.items()}
state = {"positions": {}, "pending": []}
logs = []
for d in days:
    # 그날 후보: 그날 첫 봉에 붙은 전 거래일 재료가 조건을 채운 종목 · 100위 안
    cands, br = [], None
    for c, b in data.items():
        k0 = idx[c].get(d + "09")
        if k0 is None: continue
        x = ATT[c][k0]
        if x and br is None: br = x["시장폭"]
        if IN[c][k0] and ok(x):
            f5, r20 = feat(c, d)
            cands.append({"code": c, "name": c, "추세문": bool(x["추세문"]), "3일연속": bool(x["3일연속"]), "flow5": f5, "r20": r20})
    plan = {"base": "", "breadth": br, "candidates": cands}
    for hh in A.HOURS:
        bid = d + hh
        opens = {c: data[c]["o"][idx[c][bid]] for c in data if bid in idx[c]}
        A.fill(state, bid, opens)
        codes = {x["code"] for x in cands} | set(state["positions"]) | {x["code"] for x in state["pending"]}
        bars = {}
        for c in codes:
            if bid not in idx[c]: continue
            k = idx[c][bid]
            bars[c] = {"t": data[c]["t"][:k + 1], "c": list(data[c]["c"][:k + 1])}
        A.step(state, plan, bars, bid, {}, lambda kind, text, extra: logs.append((bid, kind, text)))
    # 그날 마지막 봉 뒤: 들고 있는 정배열 매매 — 다음 날 재료로 정배열이 깨졌으면 다음 날 09 시가에 팜
    for c, p in list(state["positions"].items()):
        if p["kind"] != "정배열" or any(x["code"] == c and x["type"] == "sell" for x in state["pending"]): continue
        k = idx[c].get(d + "14")
        if k is None or k + 1 >= len(data[c]["t"]): continue
        nx = ATT[c][k + 1]
        if nx is not None and not nx["정배열"]:
            state["pending"].append({"type": "sell", "code": c, "칸": p["칸"], "why": "일봉 정배열 깨짐", "decided": d + "14"})
closed = state.get("closed", [])
years = max(len(days) / 245, 0.25)
tot = sum(t["손익"] * t["칸"] / 10 for t in closed)
print(f"  실시간 모듈 되감기: 매매 조각 {len(closed)} · 연 {tot / years:.2f}(끝에 들고 있는 것 {len(state['positions'])}종목 뺌) · 승률 {np.mean([t['손익'] > 0 for t in closed]) * 100:.1f}%", flush=True)
ek = {(t["code"], t["산 때"]) for t in eng["목록"]}; lk = {(t["code"], t["산 때"]) for t in closed}
print(f"  같은 매매(종목 · 산 봉): 엔진 {len(ek)} · 되감기 {len(lk)} · 겹침 {len(ek & lk)} ({len(ek & lk) / max(len(ek), 1) * 100:.0f}%)", flush=True)
from collections import Counter
print("  알림 종류:", dict(Counter(k for _, k, _ in logs)), flush=True)
for row in logs[:12]: print("   ", row, flush=True)
print("끝", flush=True)
