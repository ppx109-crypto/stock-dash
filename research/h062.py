"""1시간봉 62회차(확인 줄) — 한국투자증권 1시간봉(받은 117종목 · 2025-09-18 ~ 2026-09-29)으로 51회차를 넓혀 다시 확인.
같은 종목 · 같은 기간에서 야후 봉 vs 한국투자증권 봉으로: 지금 규칙 · 최고 규칙(자리 바꾸기 폭<90) · 최고 규칙 + 센 장만 따라가기(59회차, 폭≥70).
이 1년은 센 장(뒤 반의 끝 1년)이라 약한 장 확인은 못 함."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
src = open("research/h051.py", encoding="utf-8").read()
exec(src.split("# 모의: 같은 39종목")[0].replace("== 1시간봉 51회차 (한국투자증권 1시간봉 78종목으로 다시 확인) ==", "== 1시간봉 62회차 (한국투자증권 1시간봉으로 다시 확인) =="))
exec(src.split("# 모의: 같은 39종목")[1].split("def run(D, stale=None):")[0])
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
def run(D, ex, stale):
    setup(D)
    r = H.simulate(D, e_align_or_noon, ex, size, rank=rank, periods=(("1년", (LO, HI)),), seeds=8, slots=10, stale_of=stale)
    sg = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in D.items()}
    vals = {k: [] for k in (0, 1, 3)}
    for seed in range(8):
        o = H._one_run(D, sg, ex, size, LO, HI, 10, seed, None, rank, H.COST, None, None, stale)
        w = sorted((t["손익"] * t["칸"] / 10 for t in o["목록"]), reverse=True)
        for k in vals: vals[k].append(sum(w[k:]))
    return r, {k: round(float(np.median(v)), 1) for k, v in vals.items()}
Y0, K0 = data, ATT
out = {}
for tag, D in (("야후 봉", YW), ("한국투자증권 봉", KW)):
    for name, ex, stf in (("지금 규칙", exit_daily, None), ("최고(자리 바꾸기 폭<90)", exit_daily, st90), ("최고 + 센 장만 따라가기", exit_regime, st90)):
        r, tr = run(D, ex, stf(D) if stf else None)
        out[(tag, name)] = r
        print(f"  {tag:10s} {name:22s} " + H.line(r), flush=True)
        print(f"      큰 매매 뺀 1년(0 · 1 · 3건 뺌): {tr}", flush=True)
for name in ("최고(자리 바꾸기 폭<90)", "최고 + 센 장만 따라가기"):
    ky = {(t["code"], t["산 때"]): t for t in out[("야후 봉", name)]["1년"]["목록"]}
    kk = {(t["code"], t["산 때"]): t for t in out[("한국투자증권 봉", name)]["1년"]["목록"]}
    both = [k for k in ky if k in kk]
    d = [kk[k]["손익"] - ky[k]["손익"] for k in both]
    print(f"  {name} 매매 대조: 야후 {len(ky)} · 한투 {len(kk)} · 같은 매매 {len(both)}건 · 손익 차이(한투−야후) 평균 {np.mean(d) if d else 0:+.2f}%p · 가운데 {np.median(d) if d else 0:+.2f}%p", flush=True)
print("끝", flush=True)
