"""1시간봉 93회차(확인 줄) — 90회차 '같은 봉 후보 순서(외국인+투신 5일 약 + 20일 수익 큼)'를 한국투자증권 1시간봉 1년(야후 봉과 나란히)으로 확인. 71회차 틀을 씀.
원래 71회차 설명: 62회차를 받은 156종목으로 넓히고 공시 거르기(67회차)도 함께 봄. 한국투자증권 1시간봉(받은 종목 · 2025-09-18 ~ 2026-09-29)으로 51회차를 넓혀 다시 확인.
같은 종목 · 같은 기간에서 야후 봉 vs 한국투자증권 봉으로: 지금 규칙 · 최고 규칙(자리 바꾸기 폭<90) · 최고 규칙 + 센 장만 따라가기(59회차, 폭≥70).
이 1년은 센 장(뒤 반의 끝 1년)이라 약한 장 확인은 못 함."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
src = open("research/h051.py", encoding="utf-8").read()
exec(src.split("# 모의: 같은 39종목")[0].replace("== 1시간봉 51회차 (한국투자증권 1시간봉 78종목으로 다시 확인) ==", "== 1시간봉 93회차 (한투 봉 1년 · 같은 봉 후보 순서) =="))
exec("#" + src.split("# 모의: 같은 39종목")[1].split("def run(D, stale=None):")[0])
def exit_regime(c, b, p, k):
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
def st90(D):
    def f(p):
        if not ((p["now"] - p["i"] >= 7) and (D[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4): return False
        x = ATT[p["code"]][p["now"]]
        return (x["시장폭"] if x and x["시장폭"] is not None else 100) < 90
    return f
def setup(D):
    global data, ATT, IN
    data = D
    ATT = {c: H.attach(D[c], CTX[c], sorted(CTX[c])) for c in D}
    IN = {c: np.array([uni.ok(c, t) for t in D[c]["t"]]) for c in D}
    H._ST.clear()
def e_disc(c, b):
    m = np.asarray(e_align_or_noon(c, b), bool).copy(); n = len(b["t"])
    for k in np.flatnonzero(m):
        x = ATT[c][k + 1] if k + 1 < n else ATT[c][k]
        if x and (x["자사주20"] or x["희석20"]): m[k] = False
    return m
ENTRY = [e_align_or_noon]
def run(D, ex, stale):
    setup(D)
    r = H.simulate(D, ENTRY[0], ex, size, rank=RANK[0], periods=(("1년", (LO, HI)),), seeds=8, slots=10, stale_of=stale)
    sg = {c: np.asarray(ENTRY[0](c, b), bool) for c, b in D.items()}
    vals = {k: [] for k in (0, 1, 3)}
    for seed in range(8):
        o = H._one_run(D, sg, ex, size, LO, HI, 10, seed, None, RANK[0], H.COST, None, None, stale)
        w = sorted((t["손익"] * t["칸"] / 10 for t in o["목록"]), reverse=True)
        for k in vals: vals[k].append(sum(w[k:]))
    return r, {k: round(float(np.median(v)), 1) for k, v in vals.items()}
import json as _json, bisect as _bis
import final_group as _fg
RANK = [rank]
DROWS = {}
def _rows(c):
    if c not in DROWS:
        px = _json.loads(open(f"price-data/{c}.json", encoding="utf-8").read())["closes"]
        vv = _json.loads(open(f"volume-data/{c}.json", encoding="utf-8").read())["날"]
        fl = sorted(_fg.flow_rows(c), key=lambda x: x["date"])
        DROWS[c] = ([x[0] for x in px], [float(x[1]) for x in px], [x[0] for x in vv], [float(x[1]) for x in vv], [x["date"] for x in fl], fl)
    return DROWS[c]
def order_rank(D):
    """D 세계의 신호(ENTRY[0])를 같은 봉 시각끼리 견줘 무리 합(0 ~ 4)을 정하고 순서 함수를 돌려줌(90회차와 같음)."""
    sc = {}
    for c, b in D.items():
        pd_, pc, vd, vol, fd, fl = _rows(c)
        for k in np.flatnonzero(np.asarray(ENTRY[0](c, b), bool)):
            day = b["t"][k + 1][:8] if k + 1 < len(b["t"]) else b["t"][k][:8]
            i = _bis.bisect_left(pd_, day) - 1; j = _bis.bisect_left(vd, day) - 1; f = _bis.bisect_left(fd, day) - 1
            r20 = pc[i] / pc[i - 20] - 1 if i >= 20 and pc[i - 20] > 0 else np.nan
            av = np.mean(vol[j - 19:j + 1]) if j >= 20 else np.nan
            s5 = sum((x.get("외국인") or 0) + (x.get("투신") or 0) for x in fl[max(0, f - 4):f + 1]) if f >= 4 else np.nan
            sc[(c, k)] = (s5 / av if av == av and av > 0 else np.nan, r20)
    bybar, T = {}, {}
    for (c, k) in sc: bybar.setdefault(D[c]["t"][k], []).append((c, k))
    for t, L in bybar.items():
        if len(L) == 1: T[L[0]] = 2; continue
        tot = np.zeros(len(L))
        for col, good_high in ((0, False), (1, True)):
            v = np.array([sc[z][col] for z in L], float)
            v = np.where(np.isnan(v), np.nanmedian(v) if np.any(~np.isnan(v)) else 0, v)
            r = np.argsort(np.argsort(v)) / (len(v) - 1)
            if not good_high: r = 1 - r
            tot += np.minimum((r * 3).astype(int), 2)
        for z, x in zip(L, tot): T[z] = int(x)
    def rk(c, b, k):
        x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
        return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, -T.get((c, k), 2))
    return rk
Y0, K0 = data, ATT
out = {}
for tag, D in (("야후 봉", YW), ("한국투자증권 봉", KW)):
    for name, ex, stf, en in (("최고(자리 바꾸기 폭<90)", exit_daily, st90, e_align_or_noon), ("최고 + 같은 봉 후보 순서", exit_daily, st90, "order")):
        ENTRY[0] = e_align_or_noon
        if en == "order":
            setup(D); RANK[0] = order_rank(D)
        else:
            RANK[0] = rank
        r, tr = run(D, ex, stf(D) if stf else None)
        out[(tag, name)] = r
        print(f"  {tag:10s} {name:22s} " + H.line(r), flush=True)
        print(f"      큰 매매 뺀 1년(0 · 1 · 3건 뺌): {tr}", flush=True)
for name in ("최고(자리 바꾸기 폭<90)", "최고 + 같은 봉 후보 순서"):
    ky = {(t["code"], t["산 때"]): t for t in out[("야후 봉", name)]["1년"]["목록"]}
    kk = {(t["code"], t["산 때"]): t for t in out[("한국투자증권 봉", name)]["1년"]["목록"]}
    both = [k for k in ky if k in kk]
    d = [kk[k]["손익"] - ky[k]["손익"] for k in both]
    print(f"  {name} 매매 대조: 야후 {len(ky)} · 한투 {len(kk)} · 같은 매매 {len(both)}건 · 손익 차이(한투−야후) 평균 {np.mean(d) if d else 0:+.2f}%p · 가운데 {np.median(d) if d else 0:+.2f}%p", flush=True)
print("끝", flush=True)
