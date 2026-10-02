"""재현 시험 — 15분봉 운영 엔진(m15_live.step · fill)을 지난 15분봉 자료로 그대로 돌려, 연구 엔진(hlab.simulate · 15분봉 22회차 후보 ·
research/q027.py SGF · exit_rule · size · stale90)과 매매가 같은지 봄. 후보 · 크기 재료는 연구와 같은 일봉 재료(ATT)에서 날마다 만들어 넣음.
시장 흐름은 연구 값(MK)을 그대로 넘김(논리 견줌 — 운영의 '그 순간 160종목 현재가' 어림은 따로).
연구 순서의 마지막 흔들기를 운영과 같은 tie(종목 · 봉)로 바꿔 무작위 몫을 없앰. Q_PART=1 앞 반 · 2 뒤 반."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
import hourly_a as A
import m15_live as L

part = os.environ.get("Q_PART", "2")
(side, (LO, HI)), = [p for p in M.periods() if p[0] == ("앞" if part == "1" else "뒤")]


# ── 연구: 한 판(흔들기는 tie로)
def rank_tie(c, b, k):
    return tuple(RKF(c, b, k)) + (A.tie(c, b["t"][k]),)


res = M.simulate(data, lambda c, b: SGF[c], exit_rule, size, rank=rank_tie, stale_of=stale90, seeds=1, periods=((side, (LO, HI)),))
research = res[side]["목록"]

# ── 운영 엔진으로 같은 날들을 돎
ALIGN = {}


class C(list):
    code = None


_orig = A.aligned_series


def aligned_cached(closes):
    code = getattr(closes, "code", None)
    if code is None:
        return _orig(closes)
    if code not in ALIGN:
        ALIGN[code] = _orig(list(data[code]["c"]))
    return ALIGN[code][:len(closes)]


A.aligned_series = aligned_cached
MKD = MK


def plan_of(day):
    cands, br = [], None
    for c, b in data.items():
        ks = [k for k in range(len(b["t"])) if b["t"][k][:8] == day] if False else None
    return cands, br


BYDAY = {}
for c, b in data.items():
    for k, t in enumerate(b["t"]):
        if LO <= t < HI:
            BYDAY.setdefault(t[:8], {}).setdefault(c, []).append(k)
state = {"positions": {}, "pending": []}
logs = []
for day in sorted(BYDAY):
    cands, br = [], None
    for c, ks in BYDAY[day].items():
        k = ks[0]
        x = ATT[c][k]
        if x is not None and br is None and x.get("시장폭") is not None:
            br = x["시장폭"]
        if x is not None and ok(x) and IN[c][k]:
            f5, r20 = raw(c, k - 1 if k > 0 else k)
            cands.append({"code": c, "name": c, "추세문": bool(x["추세문"]), "3일연속": bool(x["3일연속"]),
                          "flow5": None if f5 != f5 else float(f5), "r20": None if r20 != r20 else float(r20)})
    plan = {"candidates": cands, "breadth": br}
    # 그날 첫 봉 전: 들고 있는 정배열 매매의 일봉 정배열 깨짐(연구 ATT[k+1])
    for code, p in list(state["positions"].items()):
        ks = BYDAY[day].get(code)
        if p["kind"] != "정배열" or not ks or any(x["code"] == code and x["type"] == "sell" for x in state["pending"]):
            continue
        x = ATT[code][ks[0]]
        if x is not None and not x["정배열"]:
            state["pending"].append({"type": "sell", "code": code, "칸": p["칸"], "why": "일봉 정배열 깨짐", "decided": day + "0000"})
    for hm in L.BARS:
        bar_id = day + hm
        codes = {c for c in BYDAY[day]}
        opens, bars = {}, {}
        for c in codes:
            b = data[c]
            k = next((k for k in BYDAY[day][c] if b["t"][k] == bar_id), None)
            if k is None:
                continue
            opens[c] = float(b["o"][k])
            cl = C(b["c"][:k + 1]); cl.code = c
            bars[c] = {"t": b["t"][:k + 1], "o": list(b["o"][:k + 1]), "c": cl}
        L.fill(state, bar_id, opens)
        nxt = L.BARS[L.BARS.index(hm) + 1] if hm != "1515" else None
        next_open = {}
        L.step(state, plan, bars, bar_id, next_open, lambda kind, text, extra: logs.append((bar_id, kind, text)), market=MKD.get(bar_id))
key_r = {(t["code"], t["산 때"]) for t in research}
key_l = {(t["code"], t["산 때"]) for t in state["closed"]}
sw = lambda rows: round(sum(t["칸"] * t["손익"] / 10 for t in rows), 1)
print(f"== 재현 시험 x009(15분봉 · {side} {LO[:8]} ~ {HI[:8]}): 연구 엔진 vs 운영 엔진 ==", flush=True)
print(f"  연구: 끝난 매매 조각 {len(research)} · 계좌 몫 합 {sw(research)}% | 운영: 끝난 매매 조각 {len(state['closed'])} · 계좌 몫 합 {sw(state['closed'])}%", flush=True)
print(f"  같은 (종목 · 산 때): {len(key_r & key_l)} · 연구에만 {len(key_r - key_l)} · 운영에만 {len(key_l - key_r)}", flush=True)
print("  연구에만(앞 6): " + " · ".join(f"{c} {t}" for c, t in sorted(key_r - key_l, key=lambda x: x[1])[:6]), flush=True)
print("  운영에만(앞 6): " + " · ".join(f"{c} {t}" for c, t in sorted(key_l - key_r, key=lambda x: x[1])[:6]), flush=True)
print("끝", flush=True)
