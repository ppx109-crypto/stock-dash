"""1시간봉 88회차(확인 줄) — 86회차에서 씨앗 16으로 두 반 모두 나은 '외국인+투신 약한 것 먼저'를 잡음 세계 6으로 확인(86회차 틀 그대로, ① 건너뜀).
원래 86회차 설명:  — 85회차 '덜 몰린 것 먼저'가 한 길의 우연인지: 같은 날 신호끼리 점수 순위(0 ~ 1)를 세 무리로 나눠
무리 순서만 정하고 무리 안은 무작위(씨앗마다 달라짐) → 씨앗 16 · 큰 매매 뺀 연 + 봉 값 잡음 세계 6(53회차 방식, 씨앗 4).
추세 문 · 3일 연속 먼저는 그대로. 점수는 모두 전 거래일까지의 일봉 자료(수급 · 프로그램 · 20일 수익)라 1시간봉 잡음과 무관."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
src = open("research/h085.py", encoding="utf-8").read()
exec(src.split("cases = [")[0].replace("== 1시간봉 85회차 (자료 점수로 후보 순서) ==", "== 1시간봉 88회차 (외국인+투신 약한 것 먼저 · 잡음 세계) =="))
def pct_of(fn):
    P = {}
    for day, L in byday.items():
        v = np.array([fn(c, k) for c, k in L], float)
        if np.all(np.isnan(v)): continue
        v = np.where(np.isnan(v), np.nanmedian(v), v)
        r = np.argsort(np.argsort(v)) / max(len(v) - 1, 1)
        for (c, k), x in zip(L, r): P[(c, k)] = x
    return P
PF = pct_of(flow); PP = pct_of(SC["프로그램 5일 세기"]); PR = pct_of(SC["20일 수익"])
MIX = {z: np.mean([1 - PF.get(z, .5), 1 - PP.get(z, .5), PR.get(z, .5)]) for z in F}
SCORES = {"프로그램 약한 것 먼저": {z: 1 - v for z, v in PP.items()}, "수급 약한 것 먼저": {z: 1 - v for z, v in PF.items()},
          "20일 수익 큰 것 먼저": PR, "섞음(수급 약 · 프로그램 약 · 20일 수익 큼)": MIX,
          "거꾸로: 프로그램 센 것 먼저": PP}
def tier_rank(S, n=3):
    def r(c, b, k):
        x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
        s_ = S.get((c, k), 0.5)
        return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, -min(int(s_ * n), n - 1))
    return r
print("  ① 씨앗 16(세 무리 · 무리 안 무작위)", flush=True)
for tag, rk in []:
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
rows = {k: [] for k in ["지금", "수급 약한 것 먼저", "20일 수익 큰 것 먼저"]}
for w in range(1, 7):
    D = noisy(w); data = D; H._ST.clear(); _E.clear()
    sg = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in D.items()}
    st = lambda p, D=D: ((p["now"] - p["i"] >= 7) and (D[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4 and
                         ((ATT[p["code"]][p["now"]] or {}).get("시장폭") or 100) < 90)
    line = []
    for k in rows:
        rk = rank if k == "지금" else tier_rank(SCORES[k])
        r = H.simulate(D, lambda c, b, sg=sg: sg[c], make_exit(), size, rank=rk, stale_of=st, seeds=4)
        rows[k].append((r["앞"]["연"], r["뒤"]["연"])); line.append(f"{k[:10]} {r['앞']['연']}/{r['뒤']['연']}")
    print(f"  잡음 세계 {w}: " + " · ".join(line), flush=True)
for k, v in rows.items():
    v = np.array(v)
    print(f"  {k}: 앞 가운데 {np.median(v[:, 0]):.1f} ({v[:, 0].min():.1f}~{v[:, 0].max():.1f}) · 뒤 가운데 {np.median(v[:, 1]):.1f} ({v[:, 1].min():.1f}~{v[:, 1].max():.1f})", flush=True)
a = np.array(rows["지금"])
for k in list(rows)[1:]:
    b_ = np.array(rows[k]); print(f"  {k}가 지금보다 나은 세계: 앞 {int((b_[:, 0] > a[:, 0]).sum())}/6 · 뒤 {int((b_[:, 1] > a[:, 1]).sum())}/6", flush=True)
print("끝", flush=True)
