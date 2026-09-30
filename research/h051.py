"""1시간봉 51회차(확인 줄) — 한국투자증권 1시간봉으로 야후 결과 다시 확인(받은 78종목 · 2025-09-18 ~ 2026-09-29).
① 봉 값 차이: 시가 · 종가 · 고가 · 저가(특히 09시 봉 시가 — 우리 모의는 '다음 봉 시가'에 사므로 가장 중요)
② 한국투자증권 14 · 15시 봉을 합쳐 야후처럼 6봉으로(14시 봉 종가 = 진짜 마감 종가, 동시호가 포함)
③ 같은 39종목 · 같은 기간 · 같은 규칙(지금 규칙 · 자리 바꾸기)으로 야후 봉 vs 한국투자증권 봉 모의 → 매매 · 연수익 차이."""
import sys, glob, os
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
KD = "hourly-kis"
LO, HI = "2025091800", H.HOLDOUT
def load_kis(code):
    rows = []
    for f in sorted(glob.glob(f"{KD}/{code}/*.csv")):
        rows += [ln.split(",") for ln in open(f, encoding="utf-8").read().splitlines() if ln.count(",") == 5]
    by = {}
    for p in rows:
        if not (LO <= p[0] < HI): continue
        hh = p[0][8:]; d = p[0][:8]; v = [float(x) for x in p[1:]]
        key = d + ("14" if hh == "15" else hh)
        if key in by and hh == "15":                     # 14 · 15시 합침
            o, h, l, c, vol = by[key]
            by[key] = [o, max(h, v[1]), min(l, v[2]), v[3], vol + v[4]]
        elif hh == "15":
            by[key] = v
        else:
            by[key] = v if key not in by else [v[0], max(by[key][1], v[1]), min(by[key][2], v[2]), by[key][3], by[key][4] + v[4]]
    ts = sorted(by)
    a = np.array([by[t] for t in ts])
    return {"t": ts, "o": a[:, 0], "h": a[:, 1], "l": a[:, 2], "c": a[:, 3], "v": a[:, 4]}
codes = sorted(c for c in os.listdir(KD) if c in data)
print("== 1시간봉 51회차 (한국투자증권 1시간봉 78종목으로 다시 확인) ==", flush=True)
print(f"  종목 {len(codes)}개 (받은 {len(os.listdir(KD))}개 가운데 모의 종목에 있는 것)", flush=True)
diff = {k: [] for k in ("09시 시가", "다른 시각 시가", "종가(09~13시)", "14시 종가(마감)", "고가", "저가")}
KIS = {}
for c in codes:
    kb = load_kis(c); KIS[c] = kb
    yb = data[c]; yi = {t: i for i, t in enumerate(yb["t"])}
    for j, t in enumerate(kb["t"]):
        i = yi.get(t)
        if i is None: continue
        r = lambda a, b: abs(a / b - 1) * 100 if b else 0
        diff["09시 시가" if t[8:] == "09" else "다른 시각 시가"].append(r(yb["o"][i], kb["o"][j]))
        diff["14시 종가(마감)" if t[8:] == "14" else "종가(09~13시)"].append(r(yb["c"][i], kb["c"][j]))
        diff["고가"].append(r(yb["h"][i], kb["h"][j])); diff["저가"].append(r(yb["l"][i], kb["l"][j]))
for k, v in diff.items():
    v = np.array(v)
    print(f"  {k:14s} 봉 {len(v):>6} · 차이 가운데 {np.median(v):.3f}% · 평균 {v.mean():.3f}% · 0.5% 넘는 몫 {np.mean(v > 0.5) * 100:.1f}% · 1% 넘는 몫 {np.mean(v > 1) * 100:.1f}%", flush=True)
# 모의: 같은 39종목 · 같은 기간
def world(src):
    D = {}
    for c in codes:
        b = src[c]
        k0 = [i for i, t in enumerate(b["t"]) if LO <= t < HI]
        if not k0: continue
        D[c] = {"t": [b["t"][i] for i in k0], **{x: b[x][k0] for x in "ohlcv"}}
    return D
YW, KW = world(data), world(KIS)
def run(D, stale=None):
    global data, ATT, IN
    save = (data, ATT, IN)
    data = D
    ATT = {c: H.attach(D[c], CTX[c], sorted(CTX[c])) for c in D}
    IN = {c: np.array([uni.ok(c, t) for t in D[c]["t"]]) for c in D}
    H._ST.clear()
    try:
        return H.simulate(D, e_align_or_noon, exit_daily, size, rank=rank, periods=(("1년", (LO, HI)),), seeds=8, slots=10, stale_of=stale)
    finally:
        data, ATT, IN = save
        H._ST.clear()
st = lambda D: (lambda p: (p["now"] - p["i"] >= 7) and (D[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4)
for tag, D in (("야후 봉", YW), ("한국투자증권 봉", KW)):
    a = run(D); b = run(D, st(D))
    print(f"  {tag:14s} 지금 규칙   " + H.line(a), flush=True)
    print(f"  {tag:14s} 자리 바꾸기 " + H.line(b), flush=True)
    if tag == "야후 봉": ya = a
ka = a
ky = {(t["code"], t["산 때"]): t for t in ya["1년"]["목록"]}
kk = {(t["code"], t["산 때"]): t for t in ka["1년"]["목록"]}
both = [k for k in ky if k in kk]
d = [kk[k]["손익"] - ky[k]["손익"] for k in both]
print(f"  지금 규칙 매매 대조: 야후 {len(ky)} · 한투 {len(kk)} · 같은 매매 {len(both)}건 · 손익 차이(한투−야후) 평균 {np.mean(d) if d else 0:+.2f}%p · 가운데 {np.median(d) if d else 0:+.2f}%p", flush=True)
print("끝", flush=True)
# 큰 매매 뺀 연수익(씨앗 8 가운데) — 야후 봉 vs 한투 봉 · 지금 규칙 vs 자리 바꾸기
def trimmed(D, stale):
    global data, ATT, IN
    save = (data, ATT, IN)
    data = D
    ATT = {c: H.attach(D[c], CTX[c], sorted(CTX[c])) for c in D}
    IN = {c: np.array([uni.ok(c, t) for t in D[c]["t"]]) for c in D}
    H._ST.clear()
    try:
        sigs = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in D.items()}
        vals = {k: [] for k in (0, 1, 3)}
        for seed in range(8):
            r = H._one_run(D, sigs, exit_daily, size, LO, HI, 10, seed, None, rank, H.COST, None, None, stale)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for k in vals: vals[k].append(sum(w[k:]))
        return {k: round(float(np.median(v)), 1) for k, v in vals.items()}
    finally:
        data, ATT, IN = save
        H._ST.clear()
for tag, D in (("야후 봉", YW), ("한국투자증권 봉", KW)):
    print(f"  {tag} 큰 매매 뺀 1년 수익(가운데): 지금 규칙 {trimmed(D, None)} · 자리 바꾸기 {trimmed(D, st(D))}", flush=True)
print("끝2", flush=True)
