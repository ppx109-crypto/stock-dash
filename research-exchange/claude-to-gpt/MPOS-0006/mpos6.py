"""MPOS-0006 — (mpos5.py 이어받음) V_ONLY 대조(횡보 · 하락 = P0 · 상승 = VOL) + C1 신호 기회 진단(성과 고르기 없음).
MPOS-0005 — '둘 다'(사용자 2026-10-15): 횡보 C1(인버스 방패 + 확인형 롱 신호 때 069500) + 상승 C2(과열 g ≥ kσ 때 레버리지 0.2) 또는 VOL(GPT: 20일 흔들림 > 지난 252개 중앙값이면 0.2).
mpos4.py의 execute() · 잠금 검증 · 자르기를 그대로 옮김. python3 mpos5.py p0check | synth | run | cut <칸|all>"""
import json, os, sys, math, hashlib
sys.path.insert(0, "/home/user/stock-dash/research")
os.environ.setdefault("REG_BOX", "MPOS-0006")
import mix54_run as M, regime_dev as Dv
HERE = os.path.dirname(os.path.abspath(__file__))
Dv.BASE_CSV = M.BASES / f"{M.name((0.5, 0.3))}.csv"
CFG = dict(Dv.R0, **M.OVERLAYS["L0.4_S0.4"])
HOLD, UP_HALF = 10, 0.2
INV, LONG = {"114800": 0.4}, {"069500": 0.4}
KS = (1.0, 1.5, 2.0)
CELLS = ["P0", "V_ONLY"]                                                     # 2칸 · 후보 1
CUTS = ["P0", "V_ONLY"]

def sigs(px_days, px):
    """g = 종가/20일 평균 − 1 · σ = 앞 60개 g 표본 표준편차 · v20 = 20개 하루 수익 표본 표준편차 · vmed = 그 앞 252개 v20 중앙값(그날 제외)."""
    xs = [px[d] for d in px_days]; g, v, out = [], [], {}
    for k, d in enumerate(px_days):
        gk = xs[k] / (sum(xs[k - 19:k + 1]) / 20) - 1 if k >= 19 else None
        g.append(gk); s = None
        prev = [x for x in g[max(0, k - 60):k] if x is not None]
        if gk is not None and k - 60 >= 19 and len(prev) == 60:
            m = sum(prev) / 60; s = math.sqrt(sum((x - m) ** 2 for x in prev) / 59)
        vk = None
        if k >= 20:
            r = [xs[i] / xs[i - 1] - 1 for i in range(k - 19, k + 1)]; m = sum(r) / 20
            vk = math.sqrt(sum((x - m) ** 2 for x in r) / 19)
        v.append(vk); med = None
        pv = v[max(0, k - 252):k]
        if vk is not None and len(pv) == 252 and None not in pv:
            sv = sorted(pv); med = (sv[125] + sv[126]) / 2
        out[d] = (gk, s if s and s > 0 else None, vk, med)
    return out

def confirm_long(p, pp, S, k):
    g, s = S[p][0], S[p][1]
    if pp is None or g is None: return False
    g0, s0 = S[pp][0], S[pp][1]
    return g0 is not None and s0 is not None and g0 <= -k * s0 and g0 < g < 0

def execute(vb, hold, cash, pending, key, tgt, d, p, base):
    """mpos4.py execute() 그대로."""
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
        if sum(hold.values()) <= 1e-15: hold = {}; full = None
    if cash < -vb * base[d][1] - 1e-12:
        c = base[d][1]; x = (-c * vb - cash) / (1 - Dv.COST_BASE_DOWN - c); vb -= x; cash += x * (1 - Dv.COST_BASE_DOWN)
    return vb, hold, cash, pending, full

def account(cell, log=None):
    base, etf, br, flow = Dv.data()
    if Dv.FEAT is None or Dv.FEAT[0] is not Dv.DATA:
        Dv.FEAT = (Dv.DATA, Dv.features(etf, br, flow, Dv.short_breadth() if br else {}))
    feat = Dv.FEAT[1]; cfg = CFG; st = Dv.states(feat, cfg)
    pdays = sorted(etf["069500"]); S = sigs(pdays, etf["069500"]); pidx = {d: i for i, d in enumerate(pdays)}
    days = [d for d in sorted(base) if Dv.LO <= d <= Dv.HI and all(d in etf[c] for c in Dv.ETF)]
    side_on = cell not in ("P0", "V_ONLY")
    if cell == "V_ONLY": ks, ku = None, None
    elif cell != "P0":
        a, b = cell.split("_"); ks = float(a[1:]); ku = None if b == "V" else float(b[1:])
    A, vb, cash = 1.0, 1.0, 0.0; hold = {}
    navs, nst = {days[0]: 1.0}, {}
    pending = None; sp, sa, up, ua = False, 0, False, 0          # 횡보 개입 · 나이 / 상승 과열 개입 · 나이
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        vb *= base[d][0] / base[p][0]
        for c in hold: hold[c] *= etf[c][d] / etf[c][p]
        s_prev = st.get(p, "횡보")
        if s_prev != "횡보": sp, sa = False, 0
        if s_prev != "상승": up, ua = False, 0
        fb, c_, fe = Dv.targets(s_prev, cfg, feat.get(p)); want = {c_: fe} if fe > 0 else {}
        if side_on and s_prev == "횡보":                       # C1(MPOS-0003)과 같음(V_ONLY는 횡보 = P0)
            ex = False
            if sp:
                sa += 1; g = S[p][0]
                if (g is not None and g >= 0) or sa >= HOLD: sp, sa, ex = False, 0, True
            if not sp and not ex:
                pi = pidx.get(p); pp = pdays[pi - 1] if pi else None
                if confirm_long(p, pp, S, ks) and base[d][1] > 0: sp, sa = True, 0
            want = LONG if sp else INV
        elif cell != "P0" and s_prev == "상승":
            if ku is not None:                                 # C2(MPOS-0004)과 같음
                ex = False
                if up:
                    ua += 1; g = S[p][0]
                    if (g is not None and g <= 0) or ua >= HOLD: up, ua, ex = False, 0, True
                g, s_ = S[p][0], S[p][1]
                if not up and not ex and g is not None and s_ is not None and g >= ku * s_: up, ua = True, 0
                half = up
            else:                                              # VOL(GPT): 날마다 v20 > vmed면 반 · 창 모자라면 P0
                v20, med = S[p][2], S[p][3]; half = v20 is not None and med is not None and v20 > med
            want = {c_: UP_HALF} if half else want
        tgt = (fb, want); key = (s_prev, tuple(sorted(want.items())))
        vb, hold, cash, pending, full = execute(vb, hold, cash, pending, key, tgt, d, p, base)
        if sp and full is True and "069500" not in hold: sp, sa = False, 0                 # C1: 실제 체결 없으면 개입 끝(MPOS-0003과 같음)
        if sp and full is None: sp, sa, pending = False, 0, None                          # C1: 전량 덜어냄 → 개입 끝 · 다음 날 다시 맞춤
        navs[d] = vb + sum(hold.values()) + cash; nst[d] = s_prev
        if log is not None: log[d] = (S[p][0], S[p][1], S[p][2], S[p][3], s_prev, sp, sa, up, ua, tuple(sorted(hold.items())), vb, cash, navs[d])
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

def nei(c):
    if c == "V_ONLY": return []
    a, b = c.split("_"); i = KS.index(float(a[1:])); out = []
    for di in (-1, 1):
        if 0 <= i + di < 3: out.append(f"S{KS[i + di]}_{b}")
    if b != "V":
        jj = KS.index(float(b[1:]))
        for dj in (-1, 1):
            if 0 <= jj + dj < 3: out.append(f"{a}_U{KS[jj + dj]}")
    return out

def judge(R):
    b = R["P0"]
    def ok1(c):
        x = R[c]
        return x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"] and x["연"] >= 30.702
    ok = [c for c in CELLS[1:] if ok1(c) and all(ok1(n) for n in nei(c))]
    return ok, sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연"], c))

LOCK = {"/home/user/stock-dash/research/regime_dev.py": "9b8c18720c489707ca6fc0ab71e888cc6a5dab5e54bcd4d6eb20265cd58fe0bc",
        "/home/user/stock-dash/research/mix54_run.py": "b77ba1c1a68d7d6e242f30f4a3ed3c6fc654dd57e3a6dc44ab96852faf7bbd6e",
        "/tmp/mix0054-bases/d0.5_b0.3_no15m.csv": "6bacf87ea66e8cde576e7d8b3cd533e2b18ccd78ed8afdb7e79d5ebb72824531",
        "/tmp/rev-full.pkl": "540114ff96929ceb3e9d6420887e5f5457df4ab65c4457377b9bec13a1fa06a6"}
SNAPDIR = os.path.join(HERE, "inputs")          # 저장소 자료가 날마다 늘어서, 잠근 때 바이트를 여기 복사해 씀

def verify():
    h = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
    got = {f: h(f) for f in LOCK}; got["mpos5.py"] = h(os.path.abspath(__file__))
    lk = json.load(open(os.path.join(HERE, "inputs_lock.json")))
    for f, v in lk.items(): got[f] = h(os.path.join(SNAPDIR, f))
    bad = [f for f, v in LOCK.items() if got[f] != v] + [f for f, v in lk.items() if got[f] != v]
    if Dv.SNAP != "/tmp/rev-full.pkl" or Dv.CUT or str(Dv.BASE_CSV) != "/tmp/mix0054-bases/d0.5_b0.3_no15m.csv": bad.append("경로 · 환경")
    json.dump({"해시": got, "경로": {"ROOT": str(Dv.ROOT), "ETF": list(Dv.ETF), "LO-HI": [Dv.LO, Dv.HI], "SNAPDIR": SNAPDIR}, "불일치": bad},
              open(os.path.join(HERE, "receipt_lock.json"), "w"), ensure_ascii=False, indent=1)
    if bad: sys.exit(f"잠금 불일치 → 중단: {bad}")
    print("잠금 확인 PASS · receipt_lock.json")

_load0 = Dv.load
def load_snap():                                  # 잠근 복사본에서 etf · market 자료를 읽음(ROOT 바꿈 없이 경로만 바꿈)
    root0 = Dv.ROOT; Dv.ROOT = __import__("pathlib").Path(SNAPDIR)
    try: return _load0()
    finally: Dv.ROOT = root0
Dv.load = load_snap

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd in ("run", "cut"): verify()
    if cmd == "p0check":
        a, _ = Dv.account(CFG); b, _ = account("P0")
        mx = max(abs(a[d] - b[d]) for d in a); print("P0 vs 원래 account 최대 NAV 차", mx, "날", len(a), "→", "PASS(허용 1e-12)" if mx <= 1e-12 else "FAIL")
    elif cmd == "synth":
        base, etf, br, flow = Dv.data()
        Dv.DATA = ({d: (v[0], 0.0) for d, v in base.items()}, etf, br, flow); Dv.FEAT = None
        lg = {}; account("V_ONLY", lg)
        bad = sum(1 for v in lg.values() if v[9])
        print("합성 room 0 · V_ONLY: ETF 든 날", bad, "→", "PASS" if bad == 0 else "FAIL")
    elif cmd == "diag":   # GPT #414 B · #416: C1 확인형 롱 신호 기회 깔때기(성과 고르기 없음 · 판정 안 바꿈)
        base, etf, br, flow = Dv.data()
        if Dv.FEAT is None or Dv.FEAT[0] is not Dv.DATA: Dv.FEAT = (Dv.DATA, Dv.features(etf, br, flow, Dv.short_breadth() if br else {}))
        st = Dv.states(Dv.FEAT[1], CFG); pdays = sorted(etf["069500"]); S = sigs(pdays, etf["069500"])
        days = [d for d in sorted(base) if Dv.LO <= d <= Dv.HI and all(d in etf[c] for c in Dv.ETF)]
        out = {}
        for k in KS:
            ev = [(pdays[i], pdays[i - 1]) for i in range(1, len(pdays)) if Dv.LO <= pdays[i] <= Dv.HI and confirm_long(pdays[i], pdays[i - 1], S, k)]
            side = [p for p, _ in ev if st.get(p) == "횡보"]
            nxt = {days[j - 1]: days[j] for j in range(1, len(days))}
            roomok = [p for p in side if p in nxt and base[nxt[p]][1] > 0]
            lg = {}; account(f"S{k}_U1.0", lg)
            entries = sum(1 for j, d in enumerate(sorted(lg)) if lg[d][5] and lg[d][6] == 0 and (j == 0 or not lg[sorted(lg)[j - 1]][5] or lg[sorted(lg)[j - 1]][6] != 0))
            held = sum(1 for v in lg.values() if v[5])
            out[k] = {"신호(전 기간)": len(ev), "그중 횡보": len(side), "그중 room>0": len(roomok), "실제 새 진입": entries, "개입 날": held}
        print(json.dumps(out, ensure_ascii=False)); json.dump(out, open(os.path.join(HERE, "diag.json"), "w"), ensure_ascii=False, indent=1)
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
            diff = [d for d in common if part[d] != full[d]]
            rec = {"칸": c, "자른 날": cut, "비교 날": len(common), "빠진 날": len(miss), "다른 날": len(diff), "첫 다른 날": diff[:3], "판정": "PASS" if common and not miss and not diff else "FAIL"}
            print(json.dumps(rec, ensure_ascii=False))
            with open(os.path.join(HERE, "receipt_cut.jsonl"), "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
