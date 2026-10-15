"""MPOS-0002 — MIX-0054 고정 칸에서 '횡보' 국면 덧붙임 자리만 부품으로 바꾼 23칸(QUESTION.md §2 · 계산 전 잠금).
regime_dev.account()를 복사해 횡보 갈래에만 부품 상태 기계를 넣음. 상승 · 하락 갈래 · 비용 · room · 빚 없음 처리는 그대로.
python3 mpos2.py run            # 23칸 → evals.jsonl · RESULT 표
python3 mpos2.py p0check        # P0 = 원래 account() NAV와 날마다 같은지
python3 mpos2.py cut <칸>       # 자르기 시험(2021-12-31 · 2024-06-28)"""
import json, os, sys, math, hashlib
sys.path.insert(0, "/home/user/stock-dash/research")
os.environ.setdefault("REG_BOX", "MPOS-0002")
import mix54_run as M, regime_dev as Dv
HERE = os.path.dirname(os.path.abspath(__file__))
Dv.BASE_CSV = M.BASES / f"{M.name((0.5, 0.3))}.csv"
CFG = dict(Dv.R0, **M.OVERLAYS["L0.4_S0.4"])
W, HOLD = 0.4, 10
KS = (1.0, 1.5, 2.0)
CELLS = ["P0", "P1"] + [f"{f}_{k}" for f in ("L", "S", "LS", "RL", "RS", "RLS") for k in KS] + [f"B_{n}" for n in (20, 30, 40)]
SRC = {"P0": "대조", "P1": "대조"} | {c: ("Claude" if c.split("_")[0] in ("L", "S", "LS") else "GPT") for c in CELLS[2:]}

def sigs(px_days, px):
    """날 → (g, σ) · g = 종가/20일 평균 − 1 · σ = 그날 앞 60개 g의 표본 표준편차(n−1 · 그날 g 제외) · 모자라면 None."""
    xs = [px[d] for d in px_days]; g, out = [], {}
    for k, d in enumerate(px_days):
        gk = xs[k] / (sum(xs[k - 19:k + 1]) / 20) - 1 if k >= 19 else None
        g.append(gk); s = None
        prev = [v for v in g[max(0, k - 60):k] if v is not None]
        if gk is not None and k - 60 >= 19 and len(prev) == 60:
            m = sum(prev) / 60; s = math.sqrt(sum((v - m) ** 2 for v in prev) / 59)
        out[d] = (gk, s if s and s > 0 else None, xs[k], xs[max(0, k - 40):k])
    return out

def entry(cell, p, pp, S):
    """미보유 날 신규 진입 판단(전날 p 장 끝까지) → 'L'(069500) · 'S'(114800) · None."""
    fam, _, par = cell.partition("_")
    g, s, c, hist = S[p]
    if fam == "B":
        n = int(par); h = hist[-n:]
        if len(h) < n: return None
        return "L" if c > max(h) else "S" if c < min(h) else None
    k = float(par)
    if g is None or s is None: return None
    if fam in ("L", "S", "LS"):
        if fam in ("L", "LS") and g <= -k * s: return "L"
        if fam in ("S", "LS") and g >= k * s: return "S"
        return None
    g0, s0 = (S[pp][0], S[pp][1]) if pp else (None, None)
    if pp is None or g0 is None or s0 is None: return None
    if fam in ("RL", "RLS") and g0 <= -k * s0 and g0 < g < 0: return "L"
    if fam in ("RS", "RLS") and g0 >= k * s0 and 0 < g < g0: return "S"
    return None

def account(cell, log=None):
    base, etf, br, flow = Dv.data()
    if Dv.FEAT is None or Dv.FEAT[0] is not Dv.DATA:
        Dv.FEAT = (Dv.DATA, Dv.features(etf, br, flow, Dv.short_breadth() if br else {}))
    feat = Dv.FEAT[1]; cfg = CFG; st = Dv.states(feat, cfg)
    pdays = sorted(etf["069500"]); S = sigs(pdays, etf["069500"]); pidx = {d: i for i, d in enumerate(pdays)}
    days = [d for d in sorted(base) if Dv.LO <= d <= Dv.HI and all(d in etf[c] for c in Dv.ETF)]
    A, vb, ve, code, cash = 1.0, 1.0, 0.0, None, 0.0
    navs, nst = {days[0]: 1.0}, {}
    pending = None; pos = None; age = 0          # pos: 'L'/'S' 부품 보유 방향 · age = 체결일부터 센 거래일
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        vb *= base[d][0] / base[p][0]
        if code: ve *= etf[code][d] / etf[code][p]
        A = vb + ve + cash
        s_prev = st.get(p, "횡보")
        if cell != "P0" and s_prev == "횡보":
            if pos:                              # 보유 중: 청산만 봄(신호 사라짐 ≠ 청산)
                age += 1
                g = S[p][0]
                if (pos == "L" and g is not None and g >= 0 and not cell.startswith("B")) or \
                   (pos == "S" and g is not None and g <= 0 and not cell.startswith("B")) or \
                   (cell.startswith("B") and g is not None and ((pos == "L" and g <= 0) or (pos == "S" and g >= 0))) or age >= HOLD:
                    pos, age = None, 0           # 오늘 종가에 팖 · 같은 종가 재진입 없음
                    exited = True
                else:
                    exited = False
            else:
                exited = False
            if not pos and not exited and cell != "P1":
                pi = pidx.get(p); pp = pdays[pi - 1] if pi else None
                e = entry(cell, p, pp, S)
                if e: pos, age = e, 0            # 오늘(d) 종가 체결 · 손익은 d 뒤부터
            tgt = (1.0, {"L": "069500", "S": "114800"}.get(pos, cfg["inv"]), W if pos else 0.0)
        else:
            if s_prev != "횡보": pos, age = None, 0   # 횡보 벗어나면 부품 상태 초기화
            tgt = Dv.targets(s_prev, cfg, feat.get(p))
        key = (s_prev, tgt[1] if tgt[2] > 0 else None, tgt[2])
        if pending != key or d[:6] != p[:6]:
            fb, c_new, fe = tgt
            room = fb * base[d][1] + (1 - fb); fe = min(fe, room)
            tb, te = fb * A, fe * A
            cost = Dv.COST_BASE_DOWN * max(0, vb - tb) + Dv.COST_BASE_UP * max(0, tb - vb)
            cost += Dv.COST_ETF * (abs(te - ve) if c_new == code else ve + te)
            A -= cost
            vb, ve, code = fb * A, fe * A, (c_new if fe > 0 else None)
            if not code: ve = 0.0
            cash = A - vb - ve; pending = key
        elif code and cash < -vb * base[d][1] - 1e-12:
            need = -vb * base[d][1] - cash; cut = min(ve, need / (1 - Dv.COST_ETF))
            ve -= cut; cash += cut * (1 - Dv.COST_ETF)
            if ve <= 1e-15: ve, code = 0.0, None
        if cash < -vb * base[d][1] - 1e-12:
            c = base[d][1]; x = (-c * vb - cash) / (1 - Dv.COST_BASE_DOWN - c); vb -= x; cash += x * (1 - Dv.COST_BASE_DOWN)
        navs[d] = vb + ve + cash; nst[d] = s_prev
        if log is not None: log[d] = (round(S[p][0] or 0, 10), round(S[p][1] or 0, 10), s_prev, pos, age, code, round(ve / A if A else 0, 10), round(navs[d], 12))
    return navs, nst

def stats(navs):
    ds = sorted(navs); r = {ds[j]: navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))}
    mo = {}
    for d, x in r.items(): mo[d[:6]] = mo.get(d[:6], 1) * (1 + x)
    full = {m: v - 1 for m, v in mo.items() if "201703" <= m <= "202608"}
    h1 = [m for m in full if m <= "202112"]; h2 = [m for m in full if m >= "202201"]
    pk = mdd = 0
    for d in ds: pk = max(pk, navs[d]); mdd = min(mdd, navs[d] / pk - 1)
    ann = navs[ds[-1]] ** (250 / len(ds)) - 1
    return dict(손실=sum(v < 0 for v in full.values()), 영=sum(v == 0 for v in full.values()), 이익=sum(v > 0 for v in full.values()),
                앞손실=sum(full[m] < 0 for m in h1), 뒤손실=sum(full[m] < 0 for m in h2), 최악달=min(full.values()) * 100,
                최악날=min(r.values()) * 100, 연=ann * 100, MDD=mdd * 100, 손실평균=(sum(v for v in full.values() if v < 0) / max(1, sum(v < 0 for v in full.values()))) * 100)

NEI = {**{f"{f}_1.0": [f"{f}_1.5"] for f in ("L", "S", "LS", "RL", "RS", "RLS")}, **{f"{f}_2.0": [f"{f}_1.5"] for f in ("L", "S", "LS", "RL", "RS", "RLS")},
       **{f"{f}_1.5": [f"{f}_1.0", f"{f}_2.0"] for f in ("L", "S", "LS", "RL", "RS", "RLS")}, "B_20": ["B_30"], "B_40": ["B_30"], "B_30": ["B_20", "B_40"], "P1": []}

def judge(R):
    b = R["P0"]
    def base_ok(c):
        x = R[c]
        return x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"] and x["연"] >= 30.702
    ok = [c for c in CELLS[1:] if base_ok(c) and all(base_ok(n) for n in NEI[c])]
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연"], c))
    return ok, rank

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "p0check":
        a, _ = Dv.account(CFG); b, _ = account("P0")
        print("P0 vs 원래 account 최대 NAV 차", max(abs(a[d] - b[d]) for d in a), "날", len(a))
    elif cmd == "run":
        R = {}
        for c in CELLS:
            nv, _ = account(c); R[c] = stats(nv); R[c]["출처"] = SRC[c]
            print(c, json.dumps(R[c], ensure_ascii=False))
        ok, rank = judge(R)
        json.dump({"cells": R, "자격": ok, "순위": rank, "고른 것": rank[0] if rank else None}, open(os.path.join(HERE, "result.json"), "w"), ensure_ascii=False, indent=1)
        print("자격", ok, "순위", rank)
    elif cmd == "cut":
        c = sys.argv[2]; full = {}; account(c, full)
        for cut in ("20211231", "20240628"):
            Dv.CUT, Dv.DATA, Dv.FEAT = cut, None, None
            part = {}; account(c, part)
            Dv.CUT, Dv.DATA, Dv.FEAT = "", None, None
            common = [d for d in sorted(part) if d < cut]
            diff = [d for d in common if part[d] != full[d]]
            print(f"자르기 {cut} · {c}: 비교 {len(common)}날(자른 날 전날까지) · 다른 날 {len(diff)}", diff[:3])
