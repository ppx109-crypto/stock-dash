"""1시간봉 89회차 — 85 · 86 · 88회차 '덜 몰린 것 먼저'의 미래 참조를 없앤 판: 같은 날 신호끼리 순위(그날 뒤 신호까지 봄) 대신
**그달 앞의 모든 신호로 정한 세 무리 문턱**(hlab.calm_by_month처럼 지난 자료로만, 앞선 신호 40개 미만이면 가운데 무리)으로 무리를 정함.
무리 안은 무작위(씨앗마다 다름). 추세 문 · 3일 연속 먼저는 그대로. 점수: 외국인+투신 5일 세기(약할수록 먼저) · 20일 수익(클수록 먼저) · 둘 합.
씨앗 16 · 큰 매매 뺀 연 · 잡음 세계 6."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
src = open("research/h085.py", encoding="utf-8").read()
exec(src.split("cases = [")[0].replace("== 1시간봉 85회차 (자료 점수로 후보 순서) ==", "== 1시간봉 89회차 (그달 앞 신호로 정한 무리 순서) =="))
keys = sorted(F, key=lambda z: data[z[0]]["t"][z[1]])
def monthly_tier(fn, good_high):
    """점수를 그달 앞 신호들의 1/3 · 2/3 분위와 견줘 0(나쁨) · 1 · 2(좋음)."""
    T = {}; hist = []; cur = None; qs = None
    for z in keys:
        m = data[z[0]]["t"][z[1]][:6]
        if m != cur:
            cur = m; past = np.array([v for v in hist if v == v])
            qs = np.quantile(past, [1 / 3, 2 / 3]) if len(past) >= 40 else None
        v = fn(*z)
        if qs is None or v != v: T[z] = 1
        else:
            t = int(v > qs[0]) + int(v > qs[1])
            T[z] = t if good_high else 2 - t
        hist.append(v)
    return T
TF = monthly_tier(flow, False); TR = monthly_tier(SC["20일 수익"], True)
TB = {z: TF[z] + TR[z] for z in F}
def tier_rank(T):
    def r(c, b, k):
        x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
        return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, -T.get((c, k), 1))
    return r
CASES = {"지금": rank, "수급 약한 무리 먼저(그달 앞 문턱)": tier_rank(TF), "20일 수익 큰 무리 먼저(그달 앞 문턱)": tier_rank(TR),
         "둘 합(수급 약 + 20일 수익 큼)": tier_rank(TB)}
print("  ① 씨앗 16", flush=True)
for tag, rk in CASES.items():
    res = H.simulate(data, e_align_or_noon, EX, size, rank=rk, stale_of=stale90, seeds=16)
    tr = trim(rk)
    print(f"  {tag:34s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("  ② 잡음 세계 6(씨앗 4)", flush=True)
REAL = data
def noisy(seed):
    rng = np.random.default_rng(seed); out = {}
    for c, b in REAL.items():
        n = len(b["t"]); first = np.array([t[8:] == "09" for t in b["t"]])
        o = b["o"] * np.exp(rng.normal(0, np.where(first, 0.008, 0.003), n)); cc = b["c"] * np.exp(rng.normal(0, 0.003, n))
        out[c] = {"t": b["t"], "o": np.clip(o, b["l"], b["h"]), "c": np.clip(cc, b["l"], b["h"]), "h": b["h"], "l": b["l"], "v": b["v"]}
    return out
rows = {k: [] for k in CASES}
for w in range(1, 7):
    D = noisy(w); data = D; H._ST.clear(); _E.clear()
    sg = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in D.items()}
    st = lambda p, D=D: ((p["now"] - p["i"] >= 7) and (D[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4 and
                         ((ATT[p["code"]][p["now"]] or {}).get("시장폭") or 100) < 90)
    line = []
    for k, rk in CASES.items():
        r = H.simulate(D, lambda c, b, sg=sg: sg[c], make_exit(), size, rank=rk, stale_of=st, seeds=4)
        rows[k].append((r["앞"]["연"], r["뒤"]["연"])); line.append(f"{k[:8]} {r['앞']['연']}/{r['뒤']['연']}")
    print(f"  잡음 세계 {w}: " + " · ".join(line), flush=True)
a = np.array(rows["지금"])
for k, v in rows.items():
    v = np.array(v)
    print(f"  {k}: 앞 가운데 {np.median(v[:, 0]):.1f} ({v[:, 0].min():.1f}~{v[:, 0].max():.1f}) · 뒤 가운데 {np.median(v[:, 1]):.1f} ({v[:, 1].min():.1f}~{v[:, 1].max():.1f}) · 나은 세계 앞 {int((v[:, 0] > a[:, 0]).sum())}/6 · 뒤 {int((v[:, 1] > a[:, 1]).sum())}/6", flush=True)
print("끝", flush=True)
