"""1시간봉 58회차 — 목표 익절(+13%) 대신 고점 따라가기(트레일링): 오르는 힘이 남아 있으면 더 들고 감(사용자 요청 2026-09-30).
바탕: 1시간봉 최고 규칙(자리 바꾸기 · 시장 폭 < 90%일 때만). 판단은 모두 봉 종가(그 봉까지) → 다음 봉 시가.
추세 문 매매(반익 +5% 뒤 남은 칸)에 바꿔 보는 것:
  A) 고점 대비 X% 되밀리면 팜(X = 5 · 8 · 10 · 15) — 고점이 +A%(8 · 13)를 넘은 뒤부터 · 그 전엔 −5% 손절 · 60봉 제한은 따라가기가 켜지기 전에만
  B) 힘 따라가기: +13%를 넘으면 1시간봉 20봉선(또는 60봉선) 아래로 닫힐 때까지 들고 감
  C) +13%에 남은 칸의 절반을 팔고 나머지는 고점 대비 10% 되밀리면
정배열 문 매매에 더해 보는 것: 고점이 +20%를 넘으면 고점 대비 X%(8 · 12 · 15) 되밀릴 때 팜(지금은 정배열이 깨질 때 · 본전 지키기만).
점검: 씨앗 16 · 큰 매매 뺀 연수익 · 반기 · 바뀐 매매 보유 봉."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import rna
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
def stale90(p):
    if not ((p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4): return False
    x = ATT[p["code"]][p["now"]]
    return (x["시장폭"] if x and x["시장폭"] is not None else 100) < 90
_E = {}
def ema(c, n):
    if (c, n) not in _E: _E[(c, n)] = rna.ema(data[c]["c"], n)
    return _E[(c, n)]
def make_exit(trend="지금", act=13, X=10, line=20, align_trail=None):
    def f(c, b, p, k):
        now = (b["c"][k] / p["price"] - 1) * 100
        pk = (p["peak"] / p["price"] - 1) * 100
        kind = door(ATT[c][p["i"]]) or "정배열"
        held = k - p["i"]
        if kind == "추세":
            half_done = p["칸"] < p["처음칸"]
            before = b["c"][p["i"]:k].max() if k > p["i"] else -1
            if trend == "지금":
                if now >= 13 or now <= -5 or held >= 60: return "all"
            else:
                armed = pk >= act
                if not armed and (now <= -5 or held >= 60): return "all"
                if trend == "고점%":
                    if armed and b["c"][k] <= p["peak"] * (1 - X / 100): return "all"
                    if armed and now <= -5: return "all"
                elif trend == "힘":
                    if armed and b["c"][k] < ema(c, line)[k]: return "all"
                elif trend == "반반":
                    if now >= 13 and p.get("c13") is None and p["칸"] > 1:
                        p["c13"] = True
                        return max(1, p["칸"] // 2)
                    if armed and b["c"][k] <= p["peak"] * (1 - X / 100): return "all"
                if held >= 240: return "all"
            if now >= 5 and (before / p["price"] - 1) * 100 < 5 and p["칸"] == p["처음칸"]:
                return max(1, p["처음칸"] // 2)
            return 0
        if now <= -10: return "all"
        if pk >= 8 and now <= 1: return "all"
        if align_trail and pk >= 20 and b["c"][k] <= p["peak"] * (1 - align_trail / 100): return "all"
        if k + 1 < len(b["t"]):
            nx = ATT[c][k + 1]
            if nx is not None and not nx["정배열"]: return "all"
        return 0
    return f
sigs = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in data.items()}
def trimmed(ex):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, ex, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
CASES = [("지금(+13% 전량)", dict())]
for act in (8, 13):
    for X in (5, 8, 10, 15):
        CASES.append((f"고점 {X}% 되밀림(+{act}% 넘은 뒤)", dict(trend="고점%", act=act, X=X)))
CASES += [("힘: +13% 뒤 20봉선 아래면", dict(trend="힘", act=13, line=20)), ("힘: +13% 뒤 60봉선 아래면", dict(trend="힘", act=13, line=60)),
          ("힘: +8% 뒤 60봉선 아래면", dict(trend="힘", act=8, line=60)), ("+13%에 절반 · 나머지 고점 10%", dict(trend="반반", act=13, X=10))]
for X in (8, 12, 15):
    CASES.append((f"정배열도 +20% 뒤 고점 {X}% 되밀림", dict(align_trail=X)))
print("== 1시간봉 58회차 (목표 익절 대신 고점 따라가기) ==", flush=True)
for tag, kw in CASES:
    ex = make_exit(**kw)
    res = H.simulate(data, e_align_or_noon, ex, size, rank=rank, stale_of=stale90, seeds=16)
    tr = trimmed(ex)
    print(f"  {tag:30s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연(가운데): 앞 {tr['앞']} · 뒤 {tr['뒤']} · 반기(씨앗 0) 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
