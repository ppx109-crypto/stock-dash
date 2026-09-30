"""1시간봉 64회차 — 약한 장(앞)에서 진 매매를 샅샅이 분해(사용자 2026-09-30 "가볍게가 아닌 샅샅이 분해해줘").
바탕: 1시간봉 최고 규칙(정배열 다음 · 없으면 12시 · 자리 바꾸기 폭<90 · 일봉 파는 법). 씨앗 16의 매매를 모아 (종목, 산 봉)마다 한 건.
재료는 모두 '사는 봉 시가 전에 알 수 있는 것'만: 일봉 · 수급 · 공매도 · 프로그램 · 체결 쪽은 전 거래일까지, 신용 · 대차는 2거래일 전까지
(늦게 공개되는 것 조심), 분기 실적은 접수일이 사는 날 전인 것, 1시간봉은 신호 봉(산 봉 바로 앞)까지.
나누는 법: 각 반 안에서 다섯 칸(분위)으로 나눠 이긴 몫 · 평균 손익 · 계좌 몫. 두 반에서 같은 쪽이 나쁜 재료만 믿음.
이 회차는 '설명'만 함 — 거르기 규칙으로 쓰려면 문턱을 달마다 지난 자료로만 정하고 hguard를 통과해야 함(다음 회차)."""
import sys, json, bisect, pickle, os
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
import hlab as H
import final_group
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
SCR = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
EX = make_exit()
print("== 1시간봉 64회차 (약한 장 진 매매 샅샅이 분해) ==", flush=True)

# ---------- 1. 매매 모으기(씨앗 16) ----------
trades = {}
for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
    for seed in range(16):
        r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90)
        one = {}
        for t in r["목록"]:
            k = (t["code"], t["산 때"])
            g = one.setdefault(k, {"칸": 0, "몫": 0.0, "판 때": t["판 때"], "비킴": False})
            g["칸"] += t["칸"]; g["몫"] += t["손익"] * t["칸"] / 10
            g["판 때"] = max(g["판 때"], t["판 때"]); g["비킴"] |= t["비킴"]
        for k, g in one.items():
            T = trades.setdefault(k, {"반": s, "손익": [], "몫": [], "판 때": g["판 때"], "비킴": g["비킴"], "칸": g["칸"]})
            T["손익"].append(g["몫"] * 10 / g["칸"]); T["몫"].append(g["몫"])
for T in trades.values():
    T["n씨앗"] = len(T["손익"]); T["손익"] = float(np.mean(T["손익"])); T["몫"] = float(np.mean(T["몫"]))
print(f"  모은 매매: 앞 {sum(T['반'] == '앞' for T in trades.values())} · 뒤 {sum(T['반'] == '뒤' for T in trades.values())} (씨앗 16에 한 번이라도 나온 것)", flush=True)

# ---------- 2. 자료 읽기 ----------
def jl(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return None
def series(rows, key):
    rows = [r for r in rows if r.get(key) is not None]
    return [r["date"] for r in rows], np.array([float(r[key]) for r in rows])
CODES = sorted({c for c, _ in trades})
D = {}
for c in CODES:
    d = {}
    p = jl(f"price-data/{c}.json"); d["px"] = ([x[0] for x in p["closes"]], np.array([x[1] for x in p["closes"]], float)) if p else None
    v = jl(f"volume-data/{c}.json"); d["vol"] = ([x[0] for x in v["날"]], np.array([x[1:5] for x in v["날"]], float)) if v else None
    d["flow"] = sorted(final_group.flow_rows(c), key=lambda x: x["date"])
    x = jl(f"short-data/{c}.json"); d["short"] = ([r[0] for r in x["rows"]], np.array([r[1:3] for r in x["rows"]], float)) if x else None
    x = jl(f"credit-data/{c}.json"); d["credit"] = ([r[0] for r in x["rows"]], np.array([r[1:3] for r in x["rows"]], float)) if x else None
    x = jl(f"loan-data/{c}.json"); d["loan"] = series(x["rows"], "잔고주수") if x else None
    x = jl(f"program-data/{c}.json"); d["prog"] = series(x["rows"], "순매수량") if x else None
    x = jl(f"side-data/{c}.json")
    d["side"] = ([r["date"] for r in x["rows"]], np.array([[r.get("매수체결량") or 0, r.get("매도체결량") or 0] for r in x["rows"]], float)) if x else None
    x = jl(f"opinion-data/{c}.json"); d["op"] = sorted([r for r in x["rows"] if r.get("target")], key=lambda r: r["date"]) if x else []
    x = jl(f"quarter-data/{c}.json")
    q = []
    for lab, r in ((x or {}).get("rows") or {}).items():
        if not isinstance(r, dict) or not str(r.get("접수번호", ""))[:8].isdigit(): continue
        def num(k):
            try: return float(str(r.get(k)).replace(",", ""))
            except Exception: return None
        q.append((str(r["접수번호"])[:8], lab, num("영업이익"), num("매출"), num("부채"), num("자본")))
    d["q"] = sorted(q)
    D[c] = d
MK = {n: sorted(jl(f"market-data/{n}.json")["rows"], key=lambda r: r["date"]) for n in ("index_KOSPI", "index_KOSDAQ", "investor_KSP", "funds", "program_K")}
IDX = H.load(["KOSPI"]).get("KOSPI")

def before(dates, day, lag=1):
    """day보다 앞선 날 가운데 lag번째 뒤(1 = 바로 전 거래일)의 자리. 없으면 −1."""
    return bisect.bisect_left(dates, day) - lag
def ret(arr, k, n):
    return (arr[k] / arr[k - n] - 1) * 100 if k - n >= 0 and arr[k - n] > 0 else np.nan

# ---------- 3. 재료 ----------
DAYSIG = {}
for c in data:
    for k, t in enumerate(data[c]["t"]):
        if IN[c][k] and ok(ATT[c][k]):
            DAYSIG.setdefault(t[:8], set()).add(c)
last_exit = {}
def feats(c, i):
    b = data[c]; day = b["t"][i][:8]; x = ATT[c][i]; f = {}
    f["문(추세=1)"] = 1.0 if door(x) == "추세" else 0.0
    f["간격(3일선/200일선)"] = x["간격"]; f["시장폭"] = x["시장폭"] if x["시장폭"] is not None else np.nan
    f["3일연속"] = float(x["3일연속"]); f["자사주20"] = float(x["자사주20"]); f["희석20"] = float(x["희석20"])
    rk = ranks.get(x["날"], {}); f["시총 순위"] = rk.get(c, np.nan)
    f["같은 날 후보 수"] = len(DAYSIG.get(day, ()))
    f["요일"] = float(__import__("datetime").date(int(day[:4]), int(day[4:6]), int(day[6:])).weekday())
    # 신호가 켜진 지 며칠째(일봉 재료 기준, 전 거래일까지 이어진 날 수)
    cd = sorted(d_ for d_ in CTX[c] if d_ < day); n = 0
    for d_ in reversed(cd[-60:]):
        if ok(CTX[c][d_]): n += 1
        else: break
    f["신호 이어진 날"] = n
    # 일봉 값
    px = D[c]["px"]
    if px:
        k = before(px[0], day); a = px[1]
        for n_ in (1, 3, 5, 10, 20, 60, 120):
            f[f"{n_}일 수익"] = ret(a, k, n_)
        r_ = np.diff(np.log(a[max(0, k - 20):k + 1])); f["20일 변동성"] = float(np.std(r_) * 100) if len(r_) > 5 else np.nan
        hi20 = a[max(0, k - 19):k + 1].max(); hi250 = a[max(0, k - 249):k + 1].max(); lo250 = a[max(0, k - 249):k + 1].min()
        f["20일 고점 거리"] = (a[k] / hi20 - 1) * 100; f["1년 고점 거리"] = (a[k] / hi250 - 1) * 100
        f["1년 자리(0~1)"] = (a[k] - lo250) / (hi250 - lo250) if hi250 > lo250 else np.nan
        f["20일선 거리"] = (a[k] / a[max(0, k - 19):k + 1].mean() - 1) * 100
        f["60일선 거리"] = (a[k] / a[max(0, k - 59):k + 1].mean() - 1) * 100
        up = np.diff(a[max(0, k - 14):k + 1]); f["14일 RSI"] = 100 * up[up > 0].sum() / (np.abs(up).sum() or 1)
    vv = D[c]["vol"]
    if vv:
        k = before(vv[0], day); a = vv[1]
        if k >= 60:
            f["거래량 5/60일"] = a[k - 4:k + 1, 0].mean() / max(a[k - 59:k + 1, 0].mean(), 1)
            f["전날 거래량/20일"] = a[k, 0] / max(a[k - 19:k + 1, 0].mean(), 1)
            f["거래대금 20일(억)"] = a[k - 19:k + 1, 1].mean() / 1e8
            f["10일 하루 폭"] = float(np.mean((a[k - 9:k + 1, 2] - a[k - 9:k + 1, 3]) / np.maximum(a[k - 9:k + 1, 3], 1)) * 100)
    fl = D[c]["flow"]
    if fl:
        dts = [r["date"] for r in fl]; k = before(dts, day)
        vol20 = f.get("거래대금 20일(억)")
        vk = before(vv[0], day) if vv else -1
        av = max(vv[1][vk - 19:vk + 1, 0].mean(), 1) if vv and vk >= 20 else np.nan
        for col in ("외국인", "투신", "기관", "연기금", "사모", "개인"):
            s5 = sum((r.get(col) or 0) for r in fl[max(0, k - 4):k + 1]); s20 = sum((r.get(col) or 0) for r in fl[max(0, k - 19):k + 1])
            f[f"{col} 5일/거래량"] = s5 / av if av == av else np.nan
            f[f"{col} 20일/거래량"] = s20 / av if av == av else np.nan
        n = 0
        for r in reversed(fl[:k + 1]):
            if (r.get("외국인") or 0) > 0: n += 1
            else: break
        f["외국인 연속 순매수일"] = n
    for key, name, col, lag in (("short", "공매도 비중 5일", 1, 1), ("credit", "신용 잔고율", 0, 2)):
        s = D[c][key]
        if s:
            k = before(s[0], day, lag)
            if k >= 5: f[name] = float(s[1][k - 4:k + 1, col].mean()) if key == "short" else float(s[1][k, col])
            if key == "credit" and k >= 20 and s[1][k - 20, 1] > 0: f["신용 잔고 20일 변화"] = (s[1][k, 1] / s[1][k - 20, 1] - 1) * 100
    s = D[c]["loan"]
    if s:
        k = before(s[0], day, 2)
        if k >= 20 and s[1][k - 20] > 0: f["대차 잔고 20일 변화"] = (s[1][k] / s[1][k - 20] - 1) * 100
    s = D[c]["prog"]
    if s and vv:
        k = before(s[0], day); vk = before(vv[0], day)
        if k >= 5 and vk >= 20: f["프로그램 5일/거래량"] = s[1][k - 4:k + 1].sum() / max(vv[1][vk - 19:vk + 1, 0].mean(), 1)
    s = D[c]["side"]
    if s:
        k = before(s[0], day)
        if k >= 5: f["매수체결/매도체결 5일"] = s[1][k - 4:k + 1, 0].sum() / max(s[1][k - 4:k + 1, 1].sum(), 1)
    op = [r for r in D[c]["op"] if r["date"] < day]
    d90 = str(np.datetime64(f"{day[:4]}-{day[4:6]}-{day[6:]}") - np.timedelta64(90, "D")).replace("-", "")
    last90 = [r for r in op if r["date"] >= d90]
    if last90 and px:
        tg = np.median([r["target"] for r in last90]); f["목표가 여유(%)"] = (tg / px[1][before(px[0], day)] - 1) * 100
    f["90일 목표가 수"] = len(last90)
    q = [r for r in D[c]["q"] if r[0] < day]
    if q:
        rcpt, lab, op_, sales, debt, eq = q[-1]
        f["흑자(영업이익>0)"] = float(op_ > 0) if op_ is not None else np.nan
        prev = [r for r in D[c]["q"] if r[1] == f"{int(lab[:4]) - 1}{lab[4:]}"]
        if prev and prev[0][2] and op_ is not None and prev[0][2] > 0: f["영업이익 1년 증가(%)"] = (op_ / prev[0][2] - 1) * 100
        if debt and eq and eq > 0: f["부채/자본"] = debt / eq * 100
        f["실적 발표 뒤 날수"] = (np.datetime64(f"{day[:4]}-{day[4:6]}-{day[6:]}") - np.datetime64(f"{rcpt[:4]}-{rcpt[4:6]}-{rcpt[6:]}")).astype(int)
    # 시장
    for n_, key in (("코스피", "index_KOSPI"), ("코스닥", "index_KOSDAQ")):
        rows = MK[key]; dts = [r["date"] for r in rows]; a = np.array([r["종가"] for r in rows], float); k = before(dts, day)
        f[f"{n_} 5일"] = ret(a, k, 5); f[f"{n_} 20일"] = ret(a, k, 20)
        if n_ == "코스피": f["코스피 60일선 거리"] = (a[k] / a[k - 59:k + 1].mean() - 1) * 100
    rows = MK["investor_KSP"]; dts = [r["date"] for r in rows]; k = before(dts, day)
    f["시장 외국인 5일"] = sum((r.get("외국인") or 0) for r in rows[k - 4:k + 1])
    rows = MK["funds"]; dts = [r["date"] for r in rows]; k = before(dts, day, 2)
    if k >= 20 and rows[k - 20].get("고객예탁금"):
        f["고객예탁금 20일 변화"] = (rows[k]["고객예탁금"] / rows[k - 20]["고객예탁금"] - 1) * 100
        f["신용융자 20일 변화"] = (rows[k]["신용융자잔고"] / rows[k - 20]["신용융자잔고"] - 1) * 100
    # 1시간봉(신호 봉 = i−1까지)
    s_ = i - 1
    d0 = next(j for j in range(i, -1, -1) if j == 0 or b["t"][j - 1][:8] != day)
    if s_ >= d0:
        f["오늘 아침 흐름(시가→신호 봉)"] = (b["c"][s_] / b["o"][d0] - 1) * 100
        lo_, hi_ = b["l"][d0:s_ + 1].min(), b["h"][d0:s_ + 1].max()
        f["오늘 범위 안 자리"] = (b["c"][s_] - lo_) / (hi_ - lo_) if hi_ > lo_ else np.nan
        # 같은 시각까지 거래량 / 20일 같은 시각까지 평균
        hours = {b["t"][j][8:] for j in range(d0, s_ + 1)}
        past = [j for j in range(max(0, d0 - 200), d0) if b["t"][j][8:] in hours]
        f["오늘 거래량(같은 시각까지)/평소"] = b["v"][d0:s_ + 1].sum() / max(np.sum(b["v"][past]) / max(len({b['t'][j][:8] for j in past}), 1), 1)
    if d0 > 0: f["오늘 시가 틈"] = (b["o"][d0] / b["c"][d0 - 1] - 1) * 100
    f["1시간봉 7봉 수익"] = ret(b["c"], s_, 7); f["1시간봉 35봉 수익"] = ret(b["c"], s_, 35)
    e20, e60 = ema(c, 20)[s_], ema(c, 60)[s_]
    f["1시간봉 20봉선 거리"] = (b["c"][s_] / e20 - 1) * 100; f["1시간봉 60봉선 거리"] = (b["c"][s_] / e60 - 1) * 100
    if IDX is not None:
        ti = {t: j for j, t in enumerate(IDX["t"])}; j = ti.get(b["t"][s_])
        if j is not None:
            j0 = next(q_ for q_ in range(j, -1, -1) if q_ == 0 or IDX["t"][q_ - 1][:8] != day)
            f["지수 아침 흐름"] = (IDX["c"][j] / IDX["o"][j0] - 1) * 100 if IDX["t"][j][:8] == day else np.nan
            f["지수 1시간봉 7봉"] = ret(IDX["c"], j, 7)
    f["산 칸"] = 0.0
    return f

ROWS = []
for (c, t0), T in sorted(trades.items(), key=lambda z: z[0][1]):
    i = data[c]["t"].index(t0)
    f = feats(c, i)
    f["산 칸"] = float(size(c, data[c], i - 1))
    # 같은 종목을 최근 판 지 며칠(씨앗 모음 기준, 산 날 전에 판 것)
    prev = [u for (cc, tt), u in trades.items() if cc == c and u["판 때"] < t0 and tt < t0]
    if prev:
        lp = max(prev, key=lambda u: u["판 때"]); f["같은 종목 지난 매매 손익"] = lp["손익"]
        f["같은 종목 판 지 봉"] = float(i - data[c]["t"].index(lp["판 때"][1:] if lp["판 때"].startswith("끝") else lp["판 때"]))
    # 파는 까닭(씨앗 모음의 마지막 판 때 기준)
    k = data[c]["t"].index(T["판 때"][1:] if T["판 때"].startswith("끝") else T["판 때"])
    dk = max(k - 1, i); nowp = (data[c]["c"][dk] / data[c]["o"][i] - 1) * 100
    pk = (data[c]["c"][i:dk + 1].max() / data[c]["o"][i] - 1) * 100
    if T["비킴"]: why = "자리 바꾸기로 비킴"
    elif T["판 때"].startswith("끝"): why = "기간 끝"
    elif door(ATT[c][i]) == "추세":
        why = "익절 +13%" if nowp >= 12 else "손절 −5%" if nowp <= -4.5 else "60봉 끝" if k - i >= 60 else "추세 기타"
    else:
        why = "손절 −10%" if nowp <= -9.5 else "본전 지키기" if pk >= 8 and nowp <= 1.5 else "정배열 깨짐"
    ROWS.append({"code": c, "산 때": t0, **T, "까닭": why, "최고": pk, "f": f})
pickle.dump(ROWS, open(SCR / "h064_rows.pkl", "wb"))

# ---------- 4. 파는 까닭별 ----------
for s in ("앞", "뒤"):
    R = [r for r in ROWS if r["반"] == s]
    print(f"\n  [{s}] 매매 {len(R)} · 이긴 몫 {np.mean([r['손익'] > 0 for r in R]) * 100:.0f}% · 계좌 몫 합(씨앗 평균) {sum(r['몫'] * r['n씨앗'] for r in R) / 16:+.1f}%p", flush=True)
    by = {}
    for r in R: by.setdefault(r["까닭"], []).append(r)
    for why, L in sorted(by.items(), key=lambda z: sum(r["몫"] * r["n씨앗"] for r in z[1])):
        print(f"    파는 까닭 {why:10s} {len(L):4d}건 · 평균 {np.mean([r['손익'] for r in L]):+6.2f}% · 한때 최고 평균 {np.mean([r['최고'] for r in L]):+5.1f}% · 계좌 몫 {sum(r['몫'] * r['n씨앗'] for r in L) / 16:+6.1f}%p", flush=True)

# ---------- 5. 재료마다 다섯 칸 ----------
names = sorted({k for r in ROWS for k in r["f"]})
res = {}
for nm in names:
    res[nm] = {}
    for s in ("앞", "뒤"):
        R = [r for r in ROWS if r["반"] == s and r["f"].get(nm) is not None and r["f"][nm] == r["f"][nm]]
        if len(R) < 40: continue
        v = np.array([r["f"][nm] for r in R], float); p = np.array([r["손익"] for r in R]); w = np.array([r["몫"] * r["n씨앗"] / 16 for r in R])
        uniq = np.unique(v)
        if len(uniq) <= 2:
            cuts = [(v == u) for u in uniq]; labels = [f"={u:g}" for u in uniq]
        else:
            qs = np.quantile(v, [0.2, 0.4, 0.6, 0.8]); idx = np.searchsorted(qs, v, side="right")
            cuts = [idx == j for j in range(5)]; labels = [f"칸{j + 1}" for j in range(5)]
        cells = [(lab, int(m.sum()), float(np.mean(p[m] > 0) * 100) if m.sum() else np.nan, float(p[m].mean()) if m.sum() else np.nan, float(w[m].sum())) for lab, m in zip(labels, cuts)]
        rho = float(np.corrcoef(np.argsort(np.argsort(v)), np.argsort(np.argsort(p)))[0, 1])
        res[nm][s] = {"cells": cells, "rho": rho, "edges": (np.quantile(v, [0.2, 0.4, 0.6, 0.8]).round(2).tolist() if len(uniq) > 2 else None)}
print("\n  재료마다(칸1 = 작은 값 … 칸5 = 큰 값 · 칸마다 [건수 · 이긴 몫 · 평균 손익 · 계좌 몫 %p] · ρ = 순위 상관)", flush=True)
score = []
for nm in names:
    if set(res[nm]) != {"앞", "뒤"}: continue
    a, b_ = res[nm]["앞"], res[nm]["뒤"]
    print(f"  ● {nm}  (앞 ρ {a['rho']:+.2f} · 뒤 ρ {b_['rho']:+.2f} · 앞 칸 경계 {a['edges']})", flush=True)
    for s, r_ in (("앞", a), ("뒤", b_)):
        print(f"      {s}: " + " | ".join(f"{lab} {n}건 {wn:.0f}% {m:+.1f}% {w:+.1f}" for lab, n, wn, m, w in r_["cells"]), flush=True)
    # 두 반 모두 같은 쪽 끝 칸이 나머지보다 나쁜가
    for end in (0, -1):
        ca, cb = a["cells"][end], b_["cells"][end]
        ra = np.mean([x[3] for x in a["cells"] if x is not ca]); rb = np.mean([x[3] for x in b_["cells"] if x is not cb])
        if ca[3] < ra - 1 and cb[3] < rb - 1:
            score.append((nm, "작은 쪽" if end == 0 else "큰 쪽", ca, cb))
print("\n  두 반 모두 한쪽 끝 칸이 나머지 평균보다 1%p 넘게 나쁜 재료:", flush=True)
for nm, side, ca, cb in score:
    print(f"    {nm} {side}: 앞 {ca[1]}건 평균 {ca[3]:+.1f}% 계좌 {ca[4]:+.1f}%p · 뒤 {cb[1]}건 평균 {cb[3]:+.1f}% 계좌 {cb[4]:+.1f}%p", flush=True)

# ---------- 6. 큰 매매는 어디에 있었나(거르면 잃는 것) ----------
for s in ("앞", "뒤"):
    R = sorted([r for r in ROWS if r["반"] == s], key=lambda r: -r["몫"] * r["n씨앗"])[:8]
    print(f"\n  [{s}] 계좌 몫이 가장 큰 8건:", flush=True)
    for r in R:
        f = r["f"]
        print(f"    {r['code']} {r['산 때']} 손익 {r['손익']:+.1f}% ({r['까닭']}) · 간격 {f.get('간격(3일선/200일선)', np.nan):.0f} · 폭 {f.get('시장폭', np.nan):.0f} · 20일 {f.get('20일 수익', np.nan):+.0f}% · 변동성 {f.get('20일 변동성', np.nan):.1f} · 아침 {f.get('오늘 아침 흐름(시가→신호 봉)', np.nan):+.1f}% · 순위 {f.get('시총 순위', np.nan):.0f} · 신호 {f.get('신호 이어진 날')}일", flush=True)
print("끝", flush=True)
