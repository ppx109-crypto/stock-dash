"""hguard.py가 부르는 '한 세계' 실행 — 환경(HLAB_CUT · HLAB_POISON)에 따라 잘리거나 더럽혀진 자료로 같은 규칙들을 돌려
신호 · 매매 목록을 pickle로 남김. 규칙: 지금 1시간봉 규칙 · 자리 바꾸기 후보 · 짧은 판 B · 엿보기(일부러 미래를 보는 규칙 = 검사 눈 확인용)."""
import os, sys, pickle
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h021.py", encoding="utf-8").read().split('print("== 1시간봉 21회차')[0])

def stale(n, x):
    return lambda p: (p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x
IN_W = {c: np.where(np.array([bool(x) and (x["시장폭"] if x["시장폭"] is not None else 100) < 70 for x in ATT[c]]), IN150[c], IN[c]) for c in data}
def e_wide(c, b):          # 42회차 후보: 전날 시장 폭 < 70%인 날만 종목 모음을 150위로
    global IN
    keep = IN
    IN = IN_W
    try:
        return e_align_or_noon(c, b)
    finally:
        IN = keep
def stale90(p):             # 53회차 후보: 비킬 매매의 전 거래일 시장 폭 < 90%일 때만 자리 바꾸기
    if not stale(7, 4)(p): return False
    x = ATT[p["code"]][p["now"]]
    return (x["시장폭"] if x and x["시장폭"] is not None else 100) < 90
def exit_regime(c, b, p, k):   # 59회차 후보: 추세 문 매매가 센 장(판단 봉의 전 거래일 시장 폭 ≥ 70%)이면 +13%에 팔지 않고 고점 15% 되밀림까지
    x = ATT[c][k]
    strong = x is not None and (x["시장폭"] if x["시장폭"] is not None else 0) >= 70
    if (door(ATT[c][p["i"]]) or "정배열") != "추세" or not strong:
        return exit_daily(c, b, p, k)
    now = (b["c"][k] / p["price"] - 1) * 100
    armed = (p["peak"] / p["price"] - 1) * 100 >= 13
    held = k - p["i"]
    if not armed and (now <= -5 or held >= 60): return "all"
    if armed and (b["c"][k] <= p["peak"] * 0.85 or now <= -5): return "all"
    if held >= 240: return "all"
    before = b["c"][p["i"]:k].max() if k > p["i"] else -1
    if now >= 5 and (before / p["price"] - 1) * 100 < 5 and p["칸"] == p["처음칸"]:
        return max(1, p["처음칸"] // 2)
    return 0
def e_disc(c, b):          # 67회차 후보: 20일 안 자사주 · 희석 공시가 있으면 사지 않음(산 봉에 붙는 전 거래일 재료)
    m = e_align_or_noon(c, b).copy()
    n = len(b["t"])
    for k in np.flatnonzero(m):
        x = ATT[c][k + 1] if k + 1 < n else ATT[c][k]
        if x and (x["자사주20"] or x["희석20"]): m[k] = False
    return m
def e_peek(c, b):          # 일부러 다음 봉 종가를 봄(미래 참조) — 검사가 이것을 잡아야 함
    m = e_align_or_noon(c, b).copy()
    nxt = np.r_[b["c"][1:], b["c"][-1]]
    return m | (ctx_now(c, b) & (nxt > b["c"] * 1.02))
def e_peek_far(c, b):      # 일부러 30봉 뒤 종가를 봄(멀리 엿보기) — 잘라내기 · 더럽히기가 잡아야 함
    m = e_align_or_noon(c, b).copy()
    far = np.r_[b["c"][30:], np.full(min(30, len(b["c"])), b["c"][-1])]
    return m & (far > b["c"] * 1.05)
def exit_peek(c, b, p, k):   # 일부러 다음 봉 종가를 보고 팜 — 검사가 잡아야 함
    if k + 1 < len(b["c"]) and b["c"][k + 1] < b["c"][k] * 0.98: return "all"
    return exit_daily(c, b, p, k)
RULES = {
    "지금": dict(entry=e_align_or_noon, exit_rule=exit_daily, size=size, rank=rank),
    "자리 바꾸기": dict(entry=e_align_or_noon, exit_rule=exit_daily, size=size, rank=rank, stale_of=stale(7, 4)),
    "자리 바꾸기(폭<90일 때만)": dict(entry=e_align_or_noon, exit_rule=exit_daily, size=size, rank=rank, stale_of=stale90),
    "공시 거르기 + 자리 바꾸기(폭<90)": dict(entry=e_disc, exit_rule=exit_daily, size=size, rank=rank, stale_of=stale90),
    "센 장만 따라가기(폭≥70)": dict(entry=e_align_or_noon, exit_rule=exit_regime, size=size, rank=rank, stale_of=stale90),
    "폭<70 150위 + 자리 바꾸기": dict(entry=e_wide, exit_rule=exit_daily, size=size, rank=rank, stale_of=stale(7, 4)),
    "짧은 판 B": dict(entry=entry(), exit_rule=exit_trail, size=four, rank=rank, take_of=take_half, stop_of=stop5),
    "엿보기(검사 눈)": dict(entry=e_peek, exit_rule=exit_daily, size=size, rank=rank),
    "엿보기 팔기(검사 눈)": dict(entry=e_align_or_noon, exit_rule=exit_peek, size=size, rank=rank),
    "멀리 엿보기(검사 눈)": dict(entry=e_peek_far, exit_rule=exit_daily, size=size, rank=rank),
}
out = {"max_bar": max(b["t"][-1] for b in data.values()), "max_rank_day": max(ranks), "rules": {}, "dates": []}
# 날짜 짚기: 봉마다 붙은 일봉 재료의 날 · 수급 마지막 날이 그 봉의 날보다 앞인가
bad = 0
for c in data:
    for k in range(0, len(data[c]["t"]), 7):
        x = ATT[c][k]; day = data[c]["t"][k][:8]
        if x and (x["날"] >= day or (x["수급끝"] and x["수급끝"] >= day)):
            bad += 1
            if len(out["dates"]) < 5: out["dates"].append((c, data[c]["t"][k], x["날"], x["수급끝"]))
out["dates_bad"] = bad
def poisoned(b, k, rng):
    """k봉 뒤를 엉뚱한 값으로 바꾼 같은 길이의 봉 묶음."""
    n = len(b["c"]) - k - 1
    if n <= 0: return b
    walk = b["c"][k] * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    o = walk * np.exp(rng.normal(0, 0.01, n))
    nb = {"t": b["t"], **{x: b[x].copy() for x in "ohlcv"}}
    nb["o"][k + 1:] = o; nb["c"][k + 1:] = walk
    nb["h"][k + 1:] = np.maximum(o, walk) * 1.01; nb["l"][k + 1:] = np.minimum(o, walk) * 0.99
    nb["v"][k + 1:] = rng.uniform(0.2, 5, n) * max(b["v"][:k + 1].mean(), 1)
    return nb
def clear_memos():
    H._ST.clear()
    for m in ("_E20",):
        if m in globals(): globals()[m].clear()
# 3b 봉마다 더럽히기: 종목 · 봉 수백 곳에서 그 봉 뒤만 엉뚱하게 바꿔 신호(그 봉까지) · 파는 판단(그 봉) · 묵음 판단이 그대로인지
rng = np.random.default_rng(11)
codes = sorted(data)
pick = [codes[i] for i in rng.choice(len(codes), min(40, len(codes)), replace=False)]
bar_poison = {name: [0, 0] for name in RULES}      # [어긋난 수, 짚은 수]
base_sig = {}
for name, kw in (RULES.items() if not (os.environ.get("HLAB_CUT") or os.environ.get("HLAB_POISON")) else []):
    clear_memos()
    base_sig[name] = {c: np.asarray(kw["entry"](c, data[c]), bool) for c in pick}
for c in (pick if not (os.environ.get("HLAB_CUT") or os.environ.get("HLAB_POISON")) else []):
    b = data[c]; n = len(b["t"])
    hot = np.flatnonzero(ctx_now(c, b))
    ks = list(rng.choice(np.arange(200, n - 2), 8, replace=False)) + (list(rng.choice(hot[(hot > 200) & (hot < n - 2)], min(8, int(((hot > 200) & (hot < n - 2)).sum())), replace=False)) if len(hot) else [])
    for k in ks:
        bp = poisoned(b, int(k), rng)
        for name, kw in RULES.items():
            clear_memos()
            real = data[c]; data[c] = bp
            try:
                sp = np.asarray(kw["entry"](c, bp), bool)
                p = {"i": max(int(k) - 5, 0), "price": b["o"][max(int(k) - 5, 0)], "칸": 4, "처음칸": 4, "peak": b["c"][max(int(k) - 5, 0)],
                     "now": int(k), "day": b["t"][int(k)][:8], "code": c}
                ep = kw["exit_rule"](c, bp, dict(p), int(k))
                stp = kw.get("stale_of")(dict(p)) if kw.get("stale_of") else None
            finally:
                data[c] = real
            clear_memos()
            e0 = kw["exit_rule"](c, b, dict(p), int(k))
            st0 = kw.get("stale_of")(dict(p)) if kw.get("stale_of") else None
            same = np.array_equal(sp[: int(k) + 1], base_sig[name][c][: int(k) + 1]) and ep == e0 and stp == st0
            bar_poison[name][0] += 0 if same else 1
            bar_poison[name][1] += 1
out["bar_poison"] = bar_poison
clear_memos()
for name, kw in RULES.items():
    e = kw.pop("entry")
    sigs = {c: [t for t, v in zip(b["t"], np.asarray(e(c, b), bool)) if v] for c, b in data.items()}
    res = H.simulate(data, e, periods=(("전체", ("2023100100", H.HOLDOUT)),), seeds=1, **kw)
    L = res["전체"]["목록"] if res["전체"] else []
    out["rules"][name] = {"sigs": sigs, "trades": [(t["code"], t["산 때"], t["판 때"], t["칸"], t["손익"]) for t in L]}
pickle.dump(out, open(sys.argv[1], "wb"))
print("세계 끝", os.environ.get("HLAB_CUT"), os.environ.get("HLAB_POISON"), {k: len(v["trades"]) for k, v in out["rules"].items()}, flush=True)
