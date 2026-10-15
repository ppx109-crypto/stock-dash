"""MPOS-0004 — (MPOS-0003 mpos3.py를 이어받음) C2 상승 과열 때 레버리지 반 · ZP 0선 회복 뒤 첫 눌림 · Q_ACCT1 계좌 반사실 보상 선택기.
MPOS-0003 — 횡보 국면 덧붙임: 인버스 방패를 기본으로 두고 신호 때만 바꾸는 규칙 칸 + 지난 자료로만 배우는 RL 칸(QUESTION.md · 계산 전 잠금).
MPOS-0002 mpos2.py를 이어받되 ETF를 여러 개 동시에 들 수 있게(보유 = {코드: 금액}) 바꿈. 상승 · 하락 갈래 · 비용식 · room · 빚 없음은 그대로.
python3 mpos4.py p0check | synth | cons | run | cut <칸|all>"""
import json, os, sys, math, hashlib
sys.path.insert(0, "/home/user/stock-dash/research")
os.environ.setdefault("REG_BOX", "MPOS-0004")
import mix54_run as M, regime_dev as Dv
HERE = os.path.dirname(os.path.abspath(__file__))
Dv.BASE_CSV = M.BASES / f"{M.name((0.5, 0.3))}.csv"
CFG = dict(Dv.R0, **M.OVERLAYS["L0.4_S0.4"])
HOLD = 10
INV, CASH, LONG, HALF = {"114800": 0.4}, {}, {"069500": 0.4}, {"069500": 0.2, "114800": 0.2}
ACTS = {"INV": INV, "CASH": CASH, "LONG": LONG, "HALF": HALF}
KS = (1.0, 1.5, 2.0)
RLP = {"ACCT1": 1.0}                                   # GPT A: 계좌 반사실 보상 · λ 1(Q_Q1과 같음)
NMIN = 20
CELLS = ["P0"] + [f"C2_{k}" for k in KS] + ["ZP", "Q_ACCT1"]          # 6칸 · 후보 5
CUTS = ["P0", "C2_1.0", "ZP", "Q_ACCT1"]                                # 자르기 고정 목록(+ 고른 칸이 밖이면 더함)
UP_HALF = 0.2                                                           # C2: 과열 때 레버리지 몫(0.4의 반)
SWAP = {"ZP": LONG}                                 # ZP 신호 때 069500 0.4(나머지 횡보 날은 INV)

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

def zero_pullback(p, pp, ppp, S):
    """GPT B: g(t−2) ≤ 0 < g(t−1) 이고 0 < g(t) < g(t−1) (t = p)."""
    if pp is None or ppp is None: return False
    g, g1, g2 = S[p][0], S[pp][0], S[ppp][0]
    return None not in (g, g1, g2) and g2 <= 0 < g1 and 0 < g < g1

def ctx(p, S, coarse=False):
    g, s, up = S[p]
    if g is None or s is None or (up is None and not coarse): return None
    z = g / s; b = 0 if z <= -2 else 1 if z <= -1 else 2 if z <= 0 else 3 if z <= 1 else 4 if z <= 2 else 5
    return (b,) if coarse else (b, up)

def execute(vb, hold, cash, pending, key, tgt, d, p, base):
    """d 종가 실행 규칙(실제 계좌와 반사실 보상이 같이 씀): key가 바뀌거나 달이 바뀌면 전면 재조정 · 아니면 room 넘침만 ETF에서 덜고 · 그래도 빚이면 1일봉 몫을 줄임."""
    hold = dict(hold); A = vb + sum(hold.values()) + cash; full = False
    if pending != key or d[:6] != p[:6]:
        fb, want = tgt
        room = fb * base[d][1] + (1 - fb); tot = sum(want.values()); sc = min(1.0, room / tot) if tot > 0 else 0.0
        te = {c: w * sc * A for c, w in want.items()}
        tb = fb * A
        cost = Dv.COST_BASE_DOWN * max(0, vb - tb) + Dv.COST_BASE_UP * max(0, tb - vb)
        cost += Dv.COST_ETF * sum(abs(te.get(c, 0.0) - hold.get(c, 0.0)) for c in set(te) | set(hold))
        A -= cost
        vb = fb * A; hold = {c: w * sc * A for c, w in want.items() if w * sc > 0}
        cash = A - vb - sum(hold.values()); pending = key; full = True
    elif hold and cash < -vb * base[d][1] - 1e-12:
        ve = sum(hold.values()); need = -vb * base[d][1] - cash; cut = min(ve, need / (1 - Dv.COST_ETF))
        for c in list(hold): hold[c] -= cut * hold[c] / ve
        cash += cut * (1 - Dv.COST_ETF)
        if sum(hold.values()) <= 1e-15: hold = {}; full = None      # None = 전량 덜어냄
    if cash < -vb * base[d][1] - 1e-12:
        c = base[d][1]; x = (-c * vb - cash) / (1 - Dv.COST_BASE_DOWN - c); vb -= x; cash += x * (1 - Dv.COST_BASE_DOWN)
    return vb, hold, cash, pending, full

CONS = []

def account(cell, log=None):
    base, etf, br, flow = Dv.data()
    if Dv.FEAT is None or Dv.FEAT[0] is not Dv.DATA:
        Dv.FEAT = (Dv.DATA, Dv.features(etf, br, flow, Dv.short_breadth() if br else {}))
    feat = Dv.FEAT[1]; cfg = CFG; st = Dv.states(feat, cfg)
    pdays = sorted(etf["069500"]); S = sigs(pdays, etf["069500"]); pidx = {d: i for i, d in enumerate(pdays)}
    days = [d for d in sorted(base) if Dv.LO <= d <= Dv.HI and all(d in etf[c] for c in Dv.ETF)]
    fam, _, par = cell.partition("_")
    # RL 표본: 정보일 q(횡보 · 문맥 있음) → 행동 a의 보상 = q 다음 날 e 종가 → e 다음 날 종가 몫 수익. p에서 쓸 수 있는 건 그 다음 날이 p 이하인 것만.
    mem = {}; queue = []; last_av = None; nmem = 0; smem = 0.0; h_prev = {}; pend_chk = None
    A, vb, cash = 1.0, 1.0, 0.0; hold = {}
    navs, nst = {days[0]: 1.0}, {}
    pending = None; pos = False; age = 0
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        vb *= base[d][0] / base[p][0]
        for c in hold: hold[c] *= etf[c][d] / etf[c][p]
        A = vb + sum(hold.values()) + cash
        s_prev = st.get(p, "횡보")
        qlog = None; qrew = None
        if fam == "Q":                                       # p 종가까지 보상이 끝난 표본만 기억에 넣음(국면과 상관없이 날마다)
            while queue and queue[0][0] <= p:
                av, q_ctx, rew = queue.pop(0); last_av = av
                for a, r in rew.items(): mem.setdefault((q_ctx, a), []).append(r); nmem += 1; smem += r
        if cell != "P0" and s_prev == "횡보":
            if fam == "ZP":
                if pos:
                    age += 1; g = S[p][0]
                    if (g is not None and g <= 0) or age >= HOLD: pos, age, exited = False, 0, True   # ZP 청산: 롱 g ≤ 0(C1과 다름)
                    else: exited = False
                else: exited = False
                if not pos and not exited:
                    pi = pidx.get(p); pp = pdays[pi - 1] if pi else None; ppp = pdays[pi - 2] if pi and pi >= 2 else None
                    if zero_pullback(p, pp, ppp, S) and base[d][1] > 0: pos, age = True, 0
                want = SWAP[fam] if pos else INV
            elif fam == "C2":
                pos, age = False, 0; want = INV                 # C2는 횡보 날 그대로(P0)
            else:                                            # Q: 문맥별 지난 완료 표본으로 날마다 고름(완전정보 순차 선택기)
                lam = RLP[par]; coarse = par == "COARSE1"
                c0 = ctx(p, S, coarse); want, best, why, scs = INV, None, "문맥 없음", {}
                if c0 is not None and all(len(mem.get((c0, a), [])) >= NMIN for a in ACTS):
                    room_p = base[p][1]
                    for a in ACTS:                           # 동률이면 INV → CASH → LONG → HALF(허용차 1e-15)
                        v = mem[(c0, a)]; m = sum(v) / len(v); dn = math.sqrt(sum(min(x, 0) ** 2 for x in v) / len(v))
                        sc = m - lam * dn
                        if par == "COST1":                   # GPT A: p 종가 실제 보유 h(p)와 room으로 줄인 목표 u_a(p)의 전환 비용 대용
                            tot = sum(ACTS[a].values()); scl = min(1.0, room_p / tot) if tot > 0 else 0.0
                            u = {c: w * scl for c, w in ACTS[a].items()}
                            sc = scl * sc - Dv.COST_ETF * sum(abs(u.get(c, 0.0) - h_prev.get(c, 0.0)) for c in set(u) | set(h_prev))
                        scs[a] = sc
                        if best is None or sc > best[0] + 1e-15: best = (sc, a)
                    want, why = ACTS[best[1]], best[1]
                elif c0 is not None: why = "표본 모자람"
                qlog = (c0, tuple(len(mem.get((c0, a), [])) for a in ACTS), last_av, nmem, round(smem, 15), tuple(sorted(scs.items())), why)
            tgt = (1.0, want)
        elif fam == "C2" and s_prev == "상승":                 # 클로드 C2: 상승 국면 과열(g ≥ +kσ)이면 레버리지 0.2 · g ≤ 0 · 10일 · 국면 이탈로 끝
            k = float(par)
            if pos:
                age += 1; g = S[p][0]
                if (g is not None and g <= 0) or age >= HOLD: pos, age, exited = False, 0, True
                else: exited = False
            else: exited = False
            g, s_, _ = S[p]
            if not pos and not exited and g is not None and s_ is not None and g >= k * s_: pos, age = True, 0
            fb, c_, fe = Dv.targets(s_prev, cfg, feat.get(p)); fe = UP_HALF if pos else fe
            tgt = (fb, {c_: fe} if fe > 0 else {})
        else:
            if s_prev != "횡보" and not (fam == "C2" and s_prev == "상승"): pos, age = False, 0
            fb, c_, fe = Dv.targets(s_prev, cfg, feat.get(p)); tgt = (fb, {c_: fe} if fe > 0 else {})
        if fam == "Q" and s_prev == "횡보":                  # 오늘 정보일 p의 표본을 예약(보상은 d 종가 → 다음 날 종가 · 그날 뒤에만 씀)
            c0 = ctx(p, S, par == "COARSE1")
            if c0 is not None and j + 1 < len(days):
                n1 = days[j + 1]
                if par == "ACCT1":                          # GPT A(#413 보완): d 종가 실행 전 같은 상태(pending · 달 포함)에서 행동 a를 실제 실행 규칙(execute)대로 → n1 종가 MTM(다음 결정 전)
                    A0 = vb + sum(hold.values()) + cash; rew = {}
                    for a, w_ in ACTS.items():
                        v1, h1, c1, _, _ = execute(vb, hold, cash, pending, ("횡보", tuple(sorted(w_.items()))), (1.0, w_), d, p, base)
                        An = v1 * base[n1][0] / base[d][0] + sum(v * etf[c][n1] / etf[c][d] for c, v in h1.items()) + c1
                        rew[a] = An / A0 - 1
                    qrew = rew
                else:
                    rew = {a: sum(w * (etf[c][n1] / etf[c][d] - 1) for c, w in ACTS[a].items()) for a in ACTS}
                queue.append((n1, c0, rew))
        key = (s_prev, tuple(sorted(tgt[1].items())))
        if fam == "Q" and par == "ACCT1" and pend_chk is not None:     # 보존 시험: 어제 고른 행동의 반사실 보상 = 실제 한 단계 손익(오늘 재조정 전)
            CONS.append((d, pend_chk[1], (vb + sum(hold.values()) + cash) / pend_chk[0] - 1)); pend_chk = None
        A_pre = vb + sum(hold.values()) + cash
        vb, hold, cash, pending, full = execute(vb, hold, cash, pending, key, tgt, d, p, base)
        if full is True and pos and fam == "ZP" and not any(c in hold for c in SWAP[fam]): pos, age = False, 0   # ZP: 실제 체결 없으면 개입 끝
        if full is None and pos and fam == "ZP": pos, age, pending = False, 0, None                        # 전량 덜어냄 → 개입 끝
        if fam == "Q" and par == "ACCT1" and s_prev == "횡보" and qrew is not None:
            pend_chk = (A_pre, qrew.get(qlog[6]) if qlog and qlog[6] in ACTS else qrew.get("INV"))
        navs[d] = vb + sum(hold.values()) + cash; nst[d] = s_prev
        h_prev = {c: v / navs[d] for c, v in hold.items()} if navs[d] > 0 else {}
        if log is not None: log[d] = (S[p][0], S[p][1], s_prev, pos, age, tuple(sorted(hold.items())), vb, cash, navs[d], qlog)
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

NEI = {"C2_1.0": ["C2_1.5"], "C2_2.0": ["C2_1.5"], "C2_1.5": ["C2_1.0", "C2_2.0"], "ZP": [], "Q_ACCT1": []}

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
    got = {f: h(f) for f in LOCK}; got["mpos4.py"] = h(os.path.abspath(__file__))
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
        mx = max(abs(a[d] - b[d]) for d in a); print("P0 vs 원래 account 최대 NAV 차", mx, "날", len(a), "→", "PASS(허용 1e-12)" if mx <= 1e-12 else "FAIL")
    elif cmd == "cons":   # 보존 시험(GPT #413): 고른 행동의 반사실 보상 = 실제 다음 날 재조정 전 손익(유지 · 변경 · 달 교체 · room 축소 모두)
        CONS.clear(); account("Q_ACCT1")
        mx = max(abs(r - a) for _, r, a in CONS); print("보존 시험 Q_ACCT1:", len(CONS), "날 · 최대 차", mx, "→", "PASS(허용 1e-12)" if CONS and mx <= 1e-12 else "FAIL")
    elif cmd == "synth":
        base, etf, br, flow = Dv.data()
        Dv.DATA = ({d: (v[0], 0.0) for d, v in base.items()}, etf, br, flow); Dv.FEAT = None
        lg = {}; account("ZP", lg)
        bad = sum(1 for v in lg.values() if v[2] == "횡보" and v[5]); act = sum(1 for v in lg.values() if v[3])
        print("합성 room 0 · ZP: 횡보 날 ETF 든 날", bad, "· 개입 날", act, "→", "PASS" if bad == 0 and act == 0 else "FAIL")
        lg = {}; account("C2_1.0", lg)
        up = sum(1 for v in lg.values() if v[2] == "상승" and v[5])
        print("합성 room 0 · C2_1.0: 상승 날 ETF 든 날", up, "→", "PASS" if up == 0 else "FAIL")
    elif cmd == "run":
        R = {}
        for c in CELLS:
            nv, _ = account(c); R[c] = stats(nv)
            print(c, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[c].items() if k != "달"}, ensure_ascii=False))
        ok, rank = judge(R)
        json.dump({"cells": R, "자격": ok, "순위": rank, "고른 것": rank[0] if rank else None}, open(os.path.join(HERE, "result.json"), "w"), ensure_ascii=False, indent=1)
        print("자격", ok, "순위", rank)
    elif cmd == "cut":
      for c in (CUTS if sys.argv[2] == "all" else sys.argv[2:]):
        full = {}; account(c, full)
        for cut in ("20211231", "20240628"):
            Dv.CUT, Dv.DATA, Dv.FEAT = cut, None, None
            part = {}; account(c, part)
            Dv.CUT, Dv.DATA, Dv.FEAT = "", None, None
            common = [d for d in sorted(part) if d < cut]; miss = [d for d in sorted(full) if d < cut and d not in part]
            diff = [d for d in common if part[d] != full[d]]                 # Q는 문맥 · 표본 수 · 최대 완료일 · 기억 합 · 점수 · 선택 이유까지 원값 비교
            rec = {"칸": c, "자른 날": cut, "비교 날": len(common), "빠진 날": len(miss), "다른 날": len(diff), "첫 다른 날": diff[:3], "판정": "PASS" if common and not miss and not diff else "FAIL"}
            print(json.dumps(rec, ensure_ascii=False))
            with open(os.path.join(HERE, "receipt_cut.jsonl"), "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
