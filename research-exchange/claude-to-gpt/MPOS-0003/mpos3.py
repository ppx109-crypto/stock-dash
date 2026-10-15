"""MPOS-0003 — 횡보 국면 덧붙임: 인버스 방패를 기본으로 두고 신호 때만 바꾸는 규칙 칸 + 지난 자료로만 배우는 RL 칸(QUESTION.md · 계산 전 잠금).
MPOS-0002 mpos2.py를 이어받되 ETF를 여러 개 동시에 들 수 있게(보유 = {코드: 금액}) 바꿈. 상승 · 하락 갈래 · 비용식 · room · 빚 없음은 그대로.
python3 mpos3.py p0check | synth | run | cut <칸>"""
import json, os, sys, math, hashlib
sys.path.insert(0, "/home/user/stock-dash/research")
os.environ.setdefault("REG_BOX", "MPOS-0003")
import mix54_run as M, regime_dev as Dv
HERE = os.path.dirname(os.path.abspath(__file__))
Dv.BASE_CSV = M.BASES / f"{M.name((0.5, 0.3))}.csv"
CFG = dict(Dv.R0, **M.OVERLAYS["L0.4_S0.4"])
HOLD = 10
INV, CASH, LONG, HALF = {"114800": 0.4}, {}, {"069500": 0.4}, {"069500": 0.2, "114800": 0.2}
ACTS = {"INV": INV, "CASH": CASH, "LONG": LONG, "HALF": HALF}
KS = (1.0, 1.5, 2.0)
RLP = {"Q0": 0.0, "Q1": 1.0}                       # RL 위험 벌점 λ
NMIN = 20
CELLS = ["P0"] + [f"{f}_{k}" for f in ("C1", "G1", "G2") for k in KS] + [f"Q_{n}" for n in RLP]
SWAP = {"C1": LONG, "G1": CASH, "G2": HALF}         # 확인형 롱 신호 때 바꿀 것(나머지 날은 INV)

def sigs(px_days, px):
    """mpos2와 같음: g = 종가/20일 평균 − 1 · σ = 그 앞 60개 g 표본 표준편차 · 추가로 20일 평균 기울기(5일 전 대비)."""
    xs = [px[d] for d in px_days]; g, out = [], {}
    for k, d in enumerate(px_days):
        gk = xs[k] / (sum(xs[k - 19:k + 1]) / 20) - 1 if k >= 19 else None
        g.append(gk); s = None
        prev = [v for v in g[max(0, k - 60):k] if v is not None]
        if gk is not None and k - 60 >= 19 and len(prev) == 60:
            m = sum(prev) / 60; s = math.sqrt(sum((v - m) ** 2 for v in prev) / 59)
        up = (sum(xs[k - 19:k + 1]) > sum(xs[k - 24:k - 4])) if k >= 24 else None
        out[d] = (gk, s if s and s > 0 else None, up)
    return out

def confirm_long(p, pp, S, k):
    """MPOS-0002 RL_k 신호 그대로: g(p−1) ≤ −kσ(p−1) 이고 g(p−1) < g(p) < 0."""
    g, s, _ = S[p]
    if pp is None or g is None: return False
    g0, s0, _ = S[pp]
    return g0 is not None and s0 is not None and g0 <= -k * s0 and g0 < g < 0

def ctx(p, S):
    g, s, up = S[p]
    if g is None or s is None or up is None: return None
    z = g / s; b = 0 if z <= -2 else 1 if z <= -1 else 2 if z <= 0 else 3 if z <= 1 else 4 if z <= 2 else 5
    return (b, up)

def account(cell, log=None):
    base, etf, br, flow = Dv.data()
    if Dv.FEAT is None or Dv.FEAT[0] is not Dv.DATA:
        Dv.FEAT = (Dv.DATA, Dv.features(etf, br, flow, Dv.short_breadth() if br else {}))
    feat = Dv.FEAT[1]; cfg = CFG; st = Dv.states(feat, cfg)
    pdays = sorted(etf["069500"]); S = sigs(pdays, etf["069500"]); pidx = {d: i for i, d in enumerate(pdays)}
    days = [d for d in sorted(base) if Dv.LO <= d <= Dv.HI and all(d in etf[c] for c in Dv.ETF)]
    fam, _, par = cell.partition("_")
    # RL 표본: 정보일 q(횡보 · 문맥 있음) → 행동 a의 보상 = q 다음 날 e 종가 → e 다음 날 종가 몫 수익. p에서 쓸 수 있는 건 그 다음 날이 p 이하인 것만.
    mem = {}; queue = []
    A, vb, cash = 1.0, 1.0, 0.0; hold = {}
    navs, nst = {days[0]: 1.0}, {}
    pending = None; pos = False; age = 0
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        vb *= base[d][0] / base[p][0]
        for c in hold: hold[c] *= etf[c][d] / etf[c][p]
        A = vb + sum(hold.values()) + cash
        s_prev = st.get(p, "횡보")
        if fam == "Q":                                       # p까지 끝난 표본을 기억에 넣음
            while queue and queue[0][0] <= p:
                _, q_ctx, rew = queue.pop(0)
                for a, r in rew.items(): mem.setdefault((q_ctx, a), []).append(r)
        if cell != "P0" and s_prev == "횡보":
            if fam in SWAP:
                k = float(par)
                if pos:
                    age += 1; g = S[p][0]
                    if (g is not None and g >= 0) or age >= HOLD: pos, age, exited = False, 0, True
                    else: exited = False
                else: exited = False
                if not pos and not exited:
                    pi = pidx.get(p); pp = pdays[pi - 1] if pi else None
                    if confirm_long(p, pp, S, k) and base[d][1] > 0: pos, age = True, 0
                want = SWAP[fam] if pos else INV
            else:                                            # Q: 문맥별 지난 표본으로 날마다 고름
                lam = RLP[par]
                c0 = ctx(p, S); want, best = INV, None
                if c0 is not None and all(len(mem.get((c0, a), [])) >= NMIN for a in ACTS):
                    for a in ACTS:
                        v = mem[(c0, a)]; m = sum(v) / len(v); dn = math.sqrt(sum(min(x, 0) ** 2 for x in v) / len(v))
                        sc = m - lam * dn
                        if best is None or sc > best[0] + 1e-15: best = (sc, a)
                    want = ACTS[best[1]]
            tgt = (1.0, want)
        else:
            if s_prev != "횡보": pos, age = False, 0
            fb, c_, fe = Dv.targets(s_prev, cfg, feat.get(p)); tgt = (fb, {c_: fe} if fe > 0 else {})
        if fam == "Q" and s_prev == "횡보":                  # 오늘 정보일 p의 표본을 예약(보상은 d 종가 → 다음 날 종가)
            c0 = ctx(p, S)
            if c0 is not None and j + 1 < len(days):
                n1 = days[j + 1]
                rew = {a: sum(w * (etf[c][n1] / etf[c][d] - 1) for c, w in ACTS[a].items()) for a in ACTS}
                queue.append((n1, c0, rew))
        key = (s_prev, tuple(sorted(tgt[1].items())))
        if pending != key or d[:6] != p[:6]:
            fb, want = tgt
            room = fb * base[d][1] + (1 - fb); tot = sum(want.values()); sc = min(1.0, room / tot) if tot > 0 else 0.0
            te = {c: w * sc * A for c, w in want.items()}
            tb = fb * A
            cost = Dv.COST_BASE_DOWN * max(0, vb - tb) + Dv.COST_BASE_UP * max(0, tb - vb)
            cost += Dv.COST_ETF * sum(abs(te.get(c, 0.0) - hold.get(c, 0.0)) for c in set(te) | set(hold))
            A -= cost
            vb = fb * A; hold = {c: w * sc * A for c, w in want.items() if w * sc > 0}
            cash = A - vb - sum(hold.values()); pending = key
            if pos and fam in SWAP and not any(c in hold for c in SWAP[fam]) and SWAP[fam]: pos, age = False, 0
        elif hold and cash < -vb * base[d][1] - 1e-12:
            ve = sum(hold.values()); need = -vb * base[d][1] - cash; cut = min(ve, need / (1 - Dv.COST_ETF))
            for c in list(hold): hold[c] -= cut * hold[c] / ve
            cash += cut * (1 - Dv.COST_ETF)
            if sum(hold.values()) <= 1e-15:
                hold = {}
                if pos: pos, age, pending = False, 0, None
        if cash < -vb * base[d][1] - 1e-12:
            c = base[d][1]; x = (-c * vb - cash) / (1 - Dv.COST_BASE_DOWN - c); vb -= x; cash += x * (1 - Dv.COST_BASE_DOWN)
        navs[d] = vb + sum(hold.values()) + cash; nst[d] = s_prev
        if log is not None: log[d] = (S[p][0], S[p][1], s_prev, pos, age, tuple(sorted(hold.items())), vb, cash, navs[d])
    return navs, nst

def stats(navs):
    ds = sorted(navs); r = {ds[j]: navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))}
    mo = {}
    for d, x in r.items(): mo[d[:6]] = mo.get(d[:6], 1) * (1 + x)
    full = {m: v - 1 for m, v in mo.items() if "201703" <= m <= "202608"}
    h1 = [m for m in full if m <= "202112"]; h2 = [m for m in full if m >= "202201"]
    pk = mdd = 0
    for d in ds: pk = max(pk, navs[d]); mdd = min(mdd, navs[d] / pk - 1)
    return dict(손실=sum(v < 0 for v in full.values()), 영=sum(v == 0 for v in full.values()), 이익=sum(v > 0 for v in full.values()),
                앞손실=sum(full[m] < 0 for m in h1), 뒤손실=sum(full[m] < 0 for m in h2), 최악달=min(full.values()) * 100,
                최악날=min(r.values()) * 100, 연=(navs[ds[-1]] ** (250 / len(ds)) - 1) * 100, MDD=mdd * 100,
                손실평균=(sum(v for v in full.values() if v < 0) / max(1, sum(v < 0 for v in full.values()))) * 100,
                달=dict(sorted((m, round(v * 100, 4)) for m, v in full.items())))

NEI = {**{f"{f}_1.0": [f"{f}_1.5"] for f in SWAP}, **{f"{f}_2.0": [f"{f}_1.5"] for f in SWAP},
       **{f"{f}_1.5": [f"{f}_1.0", f"{f}_2.0"] for f in SWAP}, "Q_Q0": ["Q_Q1"], "Q_Q1": ["Q_Q0"]}

def judge(R):
    b = R["P0"]
    def ok1(c):
        x = R[c]
        return x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"] and x["연"] >= 30.702
    ok = [c for c in CELLS[1:] if ok1(c) and all(ok1(n) for n in NEI[c])]
    return ok, sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연"], c))

LOCK = {"/home/user/stock-dash/research/regime_dev.py": "9b8c18720c489707ca6fc0ab71e888cc6a5dab5e54bcd4d6eb20265cd58fe0bc",
        "/home/user/stock-dash/research/mix54_run.py": "b77ba1c1a68d7d6e242f30f4a3ed3c6fc654dd57e3a6dc44ab96852faf7bbd6e",
        "/tmp/mix0054-bases/d0.5_b0.3_no15m.csv": "6bacf87ea66e8cde576e7d8b3cd533e2b18ccd78ed8afdb7e79d5ebb72824531",
        "/home/user/stock-dash/etf-data/069500.json": "7b4135e184867729ef4dbbe958bf448a845defed90453aba416a28dfc2940473",
        "/home/user/stock-dash/etf-data/114800.json": "ca62396f67508ff955322f5c393db9882e766128ae791540f2c726316bcccb60",
        "/home/user/stock-dash/etf-data/122630.json": "c4a43c963067809b90302ae0ffe391ca229d3d8424fa06fabeff834ed0973255",
        "/home/user/stock-dash/etf-data/252670.json": "fb616d9f365144106defd63b113ced435fa9082bcaa81d536613eb27b1f5da29",
        "/home/user/stock-dash/market-data/investor_KSP.json": "7d0cd8fb3aab1f91fba6f0ca418a936b98b7ee1785518203bd83e934d8462e03",
        "/home/user/stock-dash/market-data/index_KOSPI.json": "608d6c8cb031a0170c74479a9789f1a0487046f09d2e081d95fc4ee04940aa0d",
        "/tmp/rev-full.pkl": "540114ff96929ceb3e9d6420887e5f5457df4ab65c4457377b9bec13a1fa06a6"}

def verify():
    h = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
    got = {f: h(f) for f in LOCK}; got["mpos3.py"] = h(os.path.join(HERE, "mpos3.py"))
    bad = [f for f, v in LOCK.items() if got[f] != v]
    if Dv.SNAP != "/tmp/rev-full.pkl" or Dv.CUT or str(Dv.BASE_CSV) != "/tmp/mix0054-bases/d0.5_b0.3_no15m.csv": bad.append("경로 · 환경")
    env = {k: os.environ.get(k) for k in ("REG_SNAP", "REG_CUT", "REG_BASE", "MIX_BASES", "REG_BOX")}
    json.dump({"해시": got, "환경": env, "경로": {"BASE_CSV": str(Dv.BASE_CSV), "SNAP": Dv.SNAP, "CUT": Dv.CUT, "ETF": list(Dv.ETF), "LO-HI": [Dv.LO, Dv.HI]}, "불일치": bad},
              open(os.path.join(HERE, "receipt_lock.json"), "w"), ensure_ascii=False, indent=1)
    if bad: sys.exit(f"잠금 불일치 → 중단: {bad}")
    print("잠금 확인 PASS · receipt_lock.json")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd in ("run", "cut"): verify()
    if cmd == "p0check":
        a, _ = Dv.account(CFG); b, _ = account("P0")
        print("P0 vs 원래 account 최대 NAV 차", max(abs(a[d] - b[d]) for d in a), "날", len(a))
    elif cmd == "synth":
        base, etf, br, flow = Dv.data()
        Dv.DATA = ({d: (v[0], 0.0) for d, v in base.items()}, etf, br, flow); Dv.FEAT = None
        lg = {}; account("G2_1.0", lg)
        bad = sum(1 for v in lg.values() if v[2] == "횡보" and v[5])
        print("합성 room 0 · G2_1.0: 횡보 날 ETF 든 날", bad, "· 부품 보유로 남은 날", sum(1 for v in lg.values() if v[3]), "→", "PASS" if bad == 0 and not any(v[3] for v in lg.values()) else "FAIL")
    elif cmd == "run":
        R = {}
        for c in CELLS:
            nv, _ = account(c); R[c] = stats(nv)
            print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False))
        ok, rank = judge(R)
        json.dump({"cells": R, "자격": ok, "순위": rank, "고른 것": rank[0] if rank else None}, open(os.path.join(HERE, "result.json"), "w"), ensure_ascii=False, indent=1)
        print("자격", ok, "순위", rank)
    elif cmd == "cut":
        c = sys.argv[2]; full = {}; account(c, full)
        for cut in ("20211231", "20240628"):
            Dv.CUT, Dv.DATA, Dv.FEAT = cut, None, None
            part = {}; account(c, part)
            Dv.CUT, Dv.DATA, Dv.FEAT = "", None, None
            common = [d for d in sorted(part) if d < cut]; miss = [d for d in sorted(full) if d < cut and d not in part]
            diff = [d for d in common if part[d] != full[d]]
            rec = {"칸": c, "자른 날": cut, "비교 날": len(common), "빠진 날": len(miss), "다른 날": len(diff), "첫 다른 날": diff[:3], "판정": "PASS" if common and not miss and not diff else "FAIL"}
            print(json.dumps(rec, ensure_ascii=False))
            with open(os.path.join(HERE, "receipt_cut.jsonl"), "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
