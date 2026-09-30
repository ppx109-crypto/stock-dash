"""1시간봉 65회차 — 이긴 매매 vs 진 매매의 차이를 재료마다 분해하고(사용자 "양수 거래와 음수 거래의 차이를 분해해 음수 거래 거르기"),
두 반 모두 같은 쪽으로 가르는 재료로 거르기를 씌워 계좌 모의.
① 가르는 힘: 재료마다 AUC(이긴 매매가 진 매매보다 그 재료 값이 클 확률, 0.5 = 못 가름) · 이긴/진 매매의 가운데 값. 큰 손해(−5% 이하)도 따로.
② 거르기: 두 반 모두 AUC가 같은 쪽으로 0.04 넘게 기운 재료의 '진 매매 쪽 끝' 10 · 20 · 30%를 막음.
   문턱은 **달마다 그 달 앞의 신호들만으로** 정함(앞선 신호 40개 미만이면 거르지 않음) — 미래 참조 없음.
   재료 값은 64회차와 같음(사는 봉 시가 전에 아는 것만). 막힌 매매의 손익 · 큰 매매를 잃는지 직접 봄.
조심: 재료 고르기에 두 반을 다 봤으므로 이 회차의 결과는 '맞춘 것'일 수 있음 → 살아남는 것은 hguard와 시험지로 확인."""
import sys, pickle
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
src = open("research/h064.py", encoding="utf-8").read()
head = src.split("# ---------- 1. 매매 모으기")[0].replace("== 1시간봉 64회차 (약한 장 진 매매 샅샅이 분해) ==", "== 1시간봉 65회차 (이긴 매매 vs 진 매매 · 거르기) ==")
body = src.split("# ---------- 2. 자료 읽기 ----------")[1].split("ROWS = []")[0].replace("CODES = sorted({c for c, _ in trades})", "CODES = sorted(data)")
exec(head)
exec(body)
ROWS = pickle.load(open(SCR / "h064_rows.pkl", "rb"))

# ---------- ① 가르는 힘 ----------
def auc(v, y):
    m = ~np.isnan(v); v, y = v[m], y[m]
    if y.sum() < 10 or (~y).sum() < 10: return np.nan, 0
    r = np.argsort(np.argsort(v)) + 1.0
    # 같은 값은 평균 순위
    _, inv, cnt = np.unique(v, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=r); r = (sums / cnt)[inv]
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0), int(m.sum())
names = sorted({k for r in ROWS for k in r["f"]})
tab = []
for nm in names:
    row = {"nm": nm}
    for s in ("앞", "뒤"):
        R = [r for r in ROWS if r["반"] == s]
        v = np.array([r["f"].get(nm, np.nan) if r["f"].get(nm) is not None else np.nan for r in R], float)
        p = np.array([r["손익"] for r in R])
        a, n = auc(v, p > 0); a5, _ = auc(v, ~(p <= -5))
        mw = np.nanmedian(v[p > 0]) if np.any(~np.isnan(v[p > 0])) else np.nan
        ml = np.nanmedian(v[p <= 0]) if np.any(~np.isnan(v[p <= 0])) else np.nan
        row[s] = (a, a5, mw, ml, n)
    tab.append(row)
def lean(r):
    a, b = r["앞"][0] - 0.5, r["뒤"][0] - 0.5
    return min(abs(a), abs(b)) * (1 if a * b > 0 else -1)
tab.sort(key=lean, reverse=True)
print("  ① 이긴 매매 vs 진 매매 — AUC(0.5 = 못 가름 · 0.5보다 크면 값이 클수록 이김) · 큰 손해 AUC · 가운데 값(이긴 / 진)", flush=True)
for r in tab:
    a, b = r["앞"], r["뒤"]
    print(f"    {r['nm']:24s} 앞 {a[0]:.2f}({a[1]:.2f}) 이긴 {a[2]:9.2f} / 진 {a[3]:9.2f} · 뒤 {b[0]:.2f}({b[1]:.2f}) 이긴 {b[2]:9.2f} / 진 {b[3]:9.2f} · 같은 쪽 {'예' if lean(r) > 0 else '아니오'}", flush=True)

# ---------- ② 거르기 ----------
EX = make_exit()
FEAT = {}
for c, b in data.items():
    ks = np.flatnonzero(sigs[c])
    for k in ks:
        if k + 1 < len(b["t"]): FEAT[(c, k)] = feats(c, k + 1)
print(f"\n  신호 {len(FEAT)}개의 재료 계산 끝", flush=True)
keys = sorted(FEAT, key=lambda z: data[z[0]]["t"][z[1]])
kday = {z: data[z[0]]["t"][z[1]][:8] for z in keys}
def monthly_block(nm, side, q):
    """side = '작은' 이면 그 달 앞 신호들의 q 분위 아래를 막음, '큰'이면 1−q 분위 위를 막음."""
    block = set(); hist = []; cur = None; edge = None
    for z in keys:
        m = kday[z][:6]
        if m != cur:
            cur = m
            past = np.array([v for v in hist if v == v])
            edge = (np.quantile(past, q if side == "작은" else 1 - q) if len(past) >= 40 else None)
        v = FEAT[z].get(nm, np.nan)
        v = np.nan if v is None else v
        if edge is not None and v == v and ((side == "작은" and v < edge) or (side == "큰" and v > edge)):
            block.add(z)
        hist.append(v)
    return block
def flag_block(nm, bad):
    return {z for z in keys if FEAT[z].get(nm) is not None and FEAT[z][nm] == bad}
def run(tag, block):
    bl = {c: np.zeros(len(b["t"]), bool) for c, b in data.items()}
    for c, k in block: bl[c][k] = True
    ent = lambda c, b: sigs[c] & ~bl[c]
    res = H.simulate(data, ent, EX, size, rank=rank, stale_of=stale90, seeds=16)
    sg = {c: sigs[c] & ~bl[c] for c in data}
    tr = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sg, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        tr[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    # 막힌 매매(64회차 모음에서, 산 봉 = 신호 봉 + 1)
    ft = {(c, data[c]["t"][k + 1]) for c, k in block if k + 1 < len(data[c]["t"])}
    msg = []
    for s in ("앞", "뒤"):
        L = [r for r in ROWS if r["반"] == s and (r["code"], r["산 때"]) in ft]
        big = sorted([r for r in ROWS if r["반"] == s], key=lambda r: -r["몫"] * r["n씨앗"])[:8]
        lost = sum((r["code"], r["산 때"]) in ft for r in big)
        msg.append(f"{s} 막힌 매매 {len(L)}건 이긴 {np.mean([r['손익'] > 0 for r in L]) * 100 if L else 0:.0f}% 평균 {np.mean([r['손익'] for r in L]) if L else 0:+.2f}% 계좌 {sum(r['몫'] * r['n씨앗'] for r in L) / 16:+.1f}%p · 큰 8건 중 {lost}건 막힘")
    print(f"  {tag:34s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']} | 막힌 신호 {len(block)} · " + " · ".join(msg), flush=True)
print("  ② 거르기 (지금 = 막는 것 없음)", flush=True)
run("지금", set())
cands = [r for r in tab if lean(r) >= 0.04 and not r["nm"].startswith("같은 종목")]
for r in cands:
    nm = r["nm"]; vals = {FEAT[z].get(nm) for z in keys[:500]} - {None}
    if len(vals) <= 2:
        continue
    side = "작은" if r["앞"][0] > 0.5 else "큰"     # 값이 클수록 이기면 작은 쪽을 막음
    for q in (0.1, 0.2, 0.3):
        run(f"{nm} {side} 쪽 {int(q * 100)}% 막음", monthly_block(nm, side, q))
for nm in ("자사주20", "희석20"):
    run(f"{nm} 켜진 신호 막음", flag_block(nm, 1.0))
run("흑자 아님(영업이익≤0) 막음", flag_block("흑자(영업이익>0)", 0.0))
print("끝", flush=True)
