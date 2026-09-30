"""1시간봉 66회차 — EMA · RNA로 좋은 매매 · 나쁜 매매 가르기(사용자 "EMA RNA로 좋은 거래, 안 좋은 거래를 구별").
RNA(rna.states): EMA 선들의 배열 · 정배열 지속 · 이격도 · 이격밴드(120봉 평균에서 몇 표준편차) · 이격속도(1 · 3 · 5 · 10봉) · 기울기 · 가속도.
세 묶음: ① 1시간봉 A(5 · 20 · 60 · 120 · 180봉) ② 1시간봉 B(5 · 10 · 20 · 60 · 120 · 240봉) ③ 일봉 A(5 · 20 · 60 · 120 · 180일).
값은 1시간봉은 신호 봉(산 봉 바로 앞)까지, 일봉은 전 거래일까지 — 미래 참조 없음(EMA는 앞 값만 씀, hlab.guard_prefix로도 확인).
매매는 64회차 모음(씨앗 16, 앞 287 · 뒤 371건). AUC로 가르는 힘을 재고, 두 반 모두 같은 쪽으로 0.04 넘게 기운 것만
65회차와 같은 방식(달마다 그 달 앞 신호들로만 문턱)으로 거르기를 씌워 계좌 모의."""
import sys, pickle
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
exec(open("research/h065.py", encoding="utf-8").read().split("# ---------- ① 가르는 힘")[0].replace("65회차 (이긴 매매 vs 진 매매 · 거르기)", "66회차 (EMA · RNA로 좋은 매매 · 나쁜 매매 가르기)"))
import rna
for c in list(data)[:3]:
    assert H.guard_prefix(data[c], "A") is None and H.guard_prefix(data[c], "B") is None
DST = {}
for c in data:
    px = D[c]["px"] if c in D else None
    if px: DST[c] = (px[0], rna.states(px[1], rna.SETS["A"]))
def rfeats(c, i):
    s_ = i - 1; f = {}
    for key in ("A", "B"):
        st = H.states(c, data[c], key)
        for nm, arr in st.items():
            v = arr[s_]; f[f"1시간 {key} {nm}"] = float(v) if v == v else np.nan
    day = data[c]["t"][i][:8]
    if c in DST:
        dts, st = DST[c]; k = before(dts, day)
        if k >= 0:
            for nm, arr in st.items():
                v = arr[k]; f[f"일봉 A {nm}"] = float(v) if v == v else np.nan
    return f
for r in ROWS:
    r["g"] = rfeats(r["code"], data[r["code"]]["t"].index(r["산 때"]))
def auc(v, y):
    m = ~np.isnan(v); v, y = v[m], y[m]
    if y.sum() < 10 or (~y).sum() < 10: return np.nan
    r = np.argsort(np.argsort(v)) + 1.0
    _, inv, cnt = np.unique(v, return_inverse=True, return_counts=True)
    r = (np.bincount(inv, weights=r) / cnt)[inv]
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
names = sorted({k for r in ROWS for k in r["g"]})
tab = []
for nm in names:
    row = {"nm": nm}
    for s in ("앞", "뒤"):
        R = [r for r in ROWS if r["반"] == s]
        v = np.array([r["g"].get(nm, np.nan) for r in R], float); p = np.array([r["손익"] for r in R])
        row[s] = (auc(v, p > 0), auc(v, ~(p <= -5)), np.nanmedian(v[p > 0]), np.nanmedian(v[p <= 0]))
    tab.append(row)
def lean(r):
    a, b = r["앞"][0] - 0.5, r["뒤"][0] - 0.5
    if a != a or b != b: return -1
    return min(abs(a), abs(b)) * (1 if a * b > 0 else -1)
tab.sort(key=lean, reverse=True)
print(f"  ① RNA 재료 {len(names)}가지 — AUC(0.5 = 못 가름 · 크면 값이 클수록 이김) · 괄호 = 큰 손해(−5% 이하) AUC · 가운데 값(이긴 / 진)", flush=True)
for r in tab[:30]:
    a, b = r["앞"], r["뒤"]
    print(f"    {r['nm']:24s} 앞 {a[0]:.2f}({a[1]:.2f}) {a[2]:8.2f} / {a[3]:8.2f} · 뒤 {b[0]:.2f}({b[1]:.2f}) {b[2]:8.2f} / {b[3]:8.2f} · 기움 {lean(r):+.3f}", flush=True)
print(f"    … 두 반 같은 쪽으로 0.04 넘게 기운 것 {sum(lean(r) >= 0.04 for r in tab)}가지 · 0.03 넘게 {sum(lean(r) >= 0.03 for r in tab)}가지 · 두 반 거꾸로 {sum(lean(r) < 0 for r in tab)}가지", flush=True)
# 한 반에서만 세게 가르는 것(참고)
one = sorted(tab, key=lambda r: -max(abs(r['앞'][0] - 0.5) if r['앞'][0] == r['앞'][0] else 0, abs(r['뒤'][0] - 0.5) if r['뒤'][0] == r['뒤'][0] else 0))[:10]
print("  (참고) 한 반에서라도 가장 세게 가르는 10가지:", flush=True)
for r in one:
    print(f"    {r['nm']:24s} 앞 {r['앞'][0]:.2f} · 뒤 {r['뒤'][0]:.2f}", flush=True)
pickle.dump(tab, open(SCR / "h066_tab.pkl", "wb"))

# ---------- ② 거르기 ----------
EX = make_exit()
keys = sorted([(c, k) for c in data for k in np.flatnonzero(sigs[c]) if k + 1 < len(data[c]["t"])], key=lambda z: data[z[0]]["t"][z[1]])
G = {z: rfeats(z[0], z[1] + 1) for z in keys}
kday = {z: data[z[0]]["t"][z[1]][:8] for z in keys}
def monthly_block(nm, side, q):
    block = set(); hist = []; cur = None; edge = None
    for z in keys:
        m = kday[z][:6]
        if m != cur:
            cur = m; past = np.array([v for v in hist if v == v])
            edge = np.quantile(past, q if side == "작은" else 1 - q) if len(past) >= 40 else None
        v = G[z].get(nm, np.nan)
        if edge is not None and v == v and ((side == "작은" and v < edge) or (side == "큰" and v > edge)): block.add(z)
        hist.append(v)
    return block
def run(tag, block):
    bl = {c: np.zeros(len(b["t"]), bool) for c, b in data.items()}
    for c, k in block: bl[c][k] = True
    sg = {c: sigs[c] & ~bl[c] for c in data}
    res = H.simulate(data, lambda c, b: sg[c], EX, size, rank=rank, stale_of=stale90, seeds=16)
    tr = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sg, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        tr[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    ft = {(c, data[c]["t"][k + 1]) for c, k in block}
    msg = []
    for s in ("앞", "뒤"):
        L = [r for r in ROWS if r["반"] == s and (r["code"], r["산 때"]) in ft]
        big = sorted([r for r in ROWS if r["반"] == s], key=lambda r: -r["몫"] * r["n씨앗"])[:8]
        msg.append(f"{s} 막힌 매매 {len(L)}건 이긴 {np.mean([r['손익'] > 0 for r in L]) * 100 if L else 0:.0f}% 평균 {np.mean([r['손익'] for r in L]) if L else 0:+.2f}% 계좌 {sum(r['몫'] * r['n씨앗'] for r in L) / 16:+.1f}%p · 큰 8건 중 {sum((r['code'], r['산 때']) in ft for r in big)}건 막힘")
    print(f"  {tag:40s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']} | 막힌 신호 {len(block)} · " + " · ".join(msg), flush=True)
    return res, tr
print("\n  ② RNA 거르기 (지금 = 막는 것 없음)", flush=True)
run("지금", set())
for r in [r for r in tab if lean(r) >= 0.04][:8]:
    side = "작은" if r["앞"][0] > 0.5 else "큰"
    for q in (0.1, 0.2, 0.3):
        run(f"{r['nm']} {side} 쪽 {int(q * 100)}% 막음", monthly_block(r["nm"], side, q))
print("끝", flush=True)
