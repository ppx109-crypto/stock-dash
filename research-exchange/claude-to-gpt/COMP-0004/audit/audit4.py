"""COMP-0004 독립 감사(agent4). 비공개 실행기는 안 보고 규칙만으로 다시 셈.
실행: cd r8 && python3 ../comp/agent4/audit4.py"""
import sys, json, random, collections
from pathlib import Path
R8 = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/r8")
OUTP = Path(__file__).resolve().parent / "audit4.out"
sys.path.insert(0, str(R8 / "research"))
import kmf_nb as K

RS = R8 / "research"
SIG = json.loads((RS / "kmf_comp_lastm_sig.json").read_text())
OUT = json.loads((RS / "kmf_comp_lastm_out.json").read_text())
DAILY = json.loads((RS / "kmf_comp_lastm_out_daily.json").read_text())
LOG = json.loads((RS / "kmf_comp_lastm_out_log.json").read_text())
DAYS = SIG["meta"]["days"]; HOLES = SIG["holes"]; P2 = DAILY["P2 혼자"]; KIND = DAILY["날 종류"]
COST = 0.04; RT = 2 * COST
PLANS = ["M1 s1.0", "M1 s1.5", "M2 s1.0", "M2 s1.5"]
res = {}

def ex(lst, x):
    if len(lst) < 3: lst.append(x)

# ---------- A. 같은 날 미래 참조: 884분까지 1분봉만으로 신호 다시 만들기 ----------
def own_bars(d, upto):
    """그날 1분봉(m ≤ upto, m ≤ 914)으로 15분봉 직접 묶기 → [(끝 분, 시, 고, 저, 종)]"""
    g = {}
    for m in sorted(K.BY[d]):
        if m > upto or m > 914: continue
        r = K.BY[d][m]; k = (m - 540) // 15
        if k not in g: g[k] = [r[2], r[3], r[4], r[5]]
        else: g[k][1] = max(g[k][1], r[3]); g[k][2] = min(g[k][2], r[4]); g[k][3] = r[5]
    return [(540 + (k + 1) * 15, *g[k]) for k in sorted(g)]

def step(state, b):
    e, a = state; c, tr = b[4], b[2] - b[3]
    e = c if e is None else e + (c - e) * 2 / 11; a = tr if a is None else a + (tr - a) * 2 / 15
    return (e, a)

def own_signals():
    """날마다: 앞날까지 상태(앞날 914분까지 봉) + 그날 884분까지 봉 → 885분 ATR · M1 · M2."""
    st = (None, None); out = {}
    for d in K.DAYS:
        x = K.BY[d]
        # 그날 885분에 닫힌 봉까지(끝 분 ≤ 885) — 884분 이하 1분봉만 씀
        s2 = st; last_end = None
        for b in own_bars(d, 884):
            if b[0] <= 885: s2 = step(s2, b); last_end = b[0]
        atr = s2[1] if last_end is not None else None
        if d in DAYS:
            i = K.DAYS.index(d); prev = K.DAYS[i - 1]
            px_ = K.BY[prev]; pc = px_[max(px_)][5]            # 앞날 마지막 1분봉 종가(앞날 자료라 미래 아님)
            m569 = [m for m in x if m <= 569]; c569 = x[max(m569)][5] if m569 else None
            m884 = [m for m in x if m <= 884]; c884 = x[max(m884)][5] if m884 else None
            o = x[min(x)][2] if min(x) <= 884 else None
            m1 = None if (pc is None or c569 is None) else c569 - pc
            m2 = None if (c884 is None or o is None) else c884 - o
            me = next((mm for mm in range(885, 915) if mm in x), None)
            out[d] = {"M1": m1, "M2": m2, "atr": atr, "me": me}
        # 다음 날을 위해 그날 전체(914분까지) 봉으로 상태 넘김
        for b in own_bars(d, 914): st = step(st, b)
    return out

OWN = own_signals()
A = {"불일치 수": 0, "예시": [], "비교 칸": 0}
for p in PLANS:
    k, s = p.split(" "); s = float(s[1:])
    for d in DAYS:
        o = OWN[d]; r = o[k]
        ok = o["me"] is not None and o["atr"] and r
        mine = [[o["me"], 1 if r > 0 else -1, s * o["atr"]]] if ok else []
        theirs = [[v[0], v[1], v[3]] for v in SIG["sig"][p].get(d, [])]
        A["비교 칸"] += 1
        bad = len(mine) != len(theirs) or any(a[0] != b[0] or a[1] != b[1] or abs(a[2] - b[2]) > 1e-9 for a, b in zip(mine, theirs))
        extra = [v for v in SIG["sig"][p].get(d, []) if v[2] is not None or v[4] != 915 or v[5] != 885]
        if bad or extra:
            A["불일치 수"] += 1; ex(A["예시"], [p, d, mine, theirs])
A["표에 없는 날"] = [d for d in DAYS if any(d not in SIG["sig"][p] for p in PLANS)]
A["신호 없는 날(판별)"] = {p: [d for d in DAYS if not SIG["sig"][p].get(d)] for p in PLANS}
res["A 같은 날 미래 참조"] = A

# ---------- B · C 체결 ----------
def run_trade(d, me, side, sd, lim, stress):
    """규칙으로 한 거래 셈 → (정리 분, 사유, 손익) 또는 None(진입 안 함)."""
    if lim < 3: return None, "한도<3"
    sd = min(sd, lim - RT)
    if sd < 0.5: return None, "폭<0.5"
    x = K.BY[d]; ent = x[me][2]; stop = ent - side * sd
    h0 = HOLES.get(d)
    for m in range(me, 935):
        if m not in x: continue
        if stress and h0 and me < h0[0] and m > h0[1] and m >= h0[0]:
            # 빈 구간을 들고 지나감: 빈 구간 끝 뒤 첫 분에 손절가로 정리
            return (m, "손절(빈 구간)", side * (stop - ent) - RT), None
        o, h, l = x[m][2], x[m][3], x[m][4]
        if m == me: o = ent
        if m >= 915: return (m, "정리", side * (o - ent) - RT), None
        if (l <= stop) if side > 0 else (h >= stop):
            px = min(o, stop) if side > 0 else max(o, stop)
            return (m, "손절", side * (px - ent) - RT), None
    return (935, "끝", side * (K.last_close(d) - ent) - RT), None

KINDN = {"나": "나 막힌 날(되돌림 켜짐)", "다": "다 P2 쉼", "가": "가 P2 본 날"}
B = {"불일치 수": 0, "예시": [], "비교 날": 0, "신호 있는데 거래 없는 (나) 날": {}, "진입 안 함 사유": {}}
C = {"불일치 수": 0, "예시": [], "비교 거래": 0, "참고(정리인데 규칙 폭 손절 닿음)": [], "신호 있는데 거래 없는 (가) 날": {}, "P2 우선 거래": {}}
D = {"불일치 수": 0, "예시": []}
LOGD = {pk: collections.defaultdict(list) for pk in LOG}
for pk, rows in LOG.items():
    for r in rows: LOGD[pk][r[0]].append(r)
for pk in LOG:
    p, ver = pk.rsplit(" ", 1); stress = ver == "스트레스판"
    dv = DAILY[pk]; nores = []; skip_reason = collections.Counter(); ga_no = []; p2first = []
    for d in DAYS:
        sg = SIG["sig"][p].get(d, []); lg = LOGD[pk].get(d, []); kind = KIND[d]
        # D 항등식
        lhs = dv["결합"][d] - P2[d]; rhs = dv["보완"][d] + dv["P2 바뀐 몫"][d]
        if abs(lhs - rhs) > 1e-9: D["불일치 수"] += 1; ex(D["예시"], [pk, d, lhs, rhs, "결합−P2≠보완+바뀐 몫"])
        dif = abs(dv["보완"][d] - sum(r[4] for r in lg))
        if dif > 1e-9: D["반올림 차(1e-9 넘음)"] = D.get("반올림 차(1e-9 넘음)", 0) + 1; D["반올림 최대 차"] = max(D.get("반올림 최대 차", 0), dif)
        if dif > 1e-6: D["불일치 수"] += 1; ex(D["예시"], [pk, d, dv["보완"][d], sum(r[4] for r in lg), "보완≠거래 합"])
        if len(lg) > 1: D["불일치 수"] += 1; ex(D["예시"], [pk, d, "하루 거래 2개 이상"])
        if lg and not sg: B["불일치 수"] += 1; ex(B["예시"], [pk, d, "신호 없는데 거래"])
        if kind in (KINDN["나"], KINDN["다"]):
            B["비교 날"] += 1
            if dv["P2 바뀐 몫"][d] != 0: B["불일치 수"] += 1; ex(B["예시"], [pk, d, "나·다 날인데 P2 바뀐 몫≠0", dv["P2 바뀐 몫"][d]])
            lim = 15.0 if kind == KINDN["다"] else 15.0 + min(0.0, P2[d])
            mine = None; why = None
            if sg:
                me, side, _, sd, _, _ = sg[0]
                mine, why = run_trade(d, me, side, sd, lim, stress)
            if mine is None and sg: skip_reason[why] += 1
            if mine is None and lg:
                if kind == KINDN["나"] and why is None:
                    pass
                B["불일치 수"] += 1; ex(B["예시"], [pk, d, kind, "규칙상 진입 안 함", why, lg])
            elif mine is not None and not lg:
                if kind == KINDN["나"]: nores.append([d, round(lim, 4), round(P2[d], 4)])   # 되돌림 보유로 쉰 날(비공개 · 확인 불가)
                else: B["불일치 수"] += 1; ex(B["예시"], [pk, d, kind, "규칙상 진입인데 거래 없음", mine])
            elif mine is not None and lg:
                r = lg[0]
                rs = "손절" if mine[1].startswith("손절") else mine[1]
                if r[1] != sg[0][0] or r[2] != mine[0] or r[3] != rs or abs(r[4] - mine[2]) > 1e-6:
                    B["불일치 수"] += 1; ex(B["예시"], [pk, d, kind, "다시 셈", list(mine), "기록", r])
        else:
            # C (가) 날: 제출 거래 조건부 확인
            if sg and not lg: ga_no.append(d)
            for r in lg:
                C["비교 거래"] += 1
                me, side, _, sd_rule, _, _ = sg[0]; x = K.BY[d]
                if r[1] != me: C["불일치 수"] += 1; ex(C["예시"], [pk, d, "진입 분 다름", r, me]); continue
                ent = x[me][2]; xp = ent + side * (r[4] + RT); m_out = r[2]; why = r[3]
                if m_out not in x: C["불일치 수"] += 1; ex(C["예시"], [pk, d, "정리 분 자료 없음", r]); continue
                o_out = ent if m_out == me else x[m_out][2]
                prob = []
                if why == "손절":
                    w = side * (ent - xp)    # 함의 폭(분 시가가 더 나쁘면 폭보다 클 수 있음)
                    hit_px = min(o_out, ent - side * w) if side > 0 else max(o_out, ent - side * w)
                    # 손절가에서 났거나(=ent−side·w) 시가 갭(시가 < 손절가)
                    # 함의 폭 ≤ 규칙 폭 · ≥ 0.5 · 정리 분에 그 손절가 닿음 · 그 앞 분에 닿음 없음
                    l, h = x[m_out][4], x[m_out][3]
                    gap = (o_out < ent - side * w - 1e-9) if side > 0 else (o_out > ent - side * w + 1e-9)
                    if w > sd_rule + 1e-6: prob.append(f"함의 폭 {w:.4f} > 규칙 폭 {sd_rule:.4f}")
                    if w < 0.5 - 1e-6: prob.append(f"함의 폭 {w:.4f} < 0.5")
                    stp = ent - side * w
                    if not ((l <= stp + 1e-6) if side > 0 else (h >= stp - 1e-6)): prob.append("정리 분에 손절가 닿지 않음")
                    for m in range(me, m_out):
                        if m in x and ((x[m][4] <= stp + 1e-9) if side > 0 else (x[m][3] >= stp - 1e-9)): prob.append(f"앞 분 {m}에 이미 닿음"); break
                elif why == "정리":
                    first915 = next((mm for mm in range(915, 935) if mm in x), None)
                    if m_out != first915: prob.append(f"정리 분 {m_out} ≠ 915 이상 첫 분 {first915}")
                    if abs(xp - x[m_out][2]) > 1e-6: prob.append(f"정리가 {xp:.4f} ≠ 시가 {x[m_out][2]}")
                    stp = ent - side * sd_rule
                    for m in range(me, m_out):
                        if m in x and ((x[m][4] <= stp) if side > 0 else (x[m][3] >= stp)):
                            C["참고(정리인데 규칙 폭 손절 닿음)"].append([pk, d, m]); break
                elif why == "P2 우선":
                    p2first.append(d)
                    if not (me <= m_out < 915): prob.append(f"P2 우선 분 {m_out} 범위 밖")
                    if abs(xp - o_out) > 1e-6: prob.append(f"P2 우선 정리가 {xp:.4f} ≠ 그 분 시가 {o_out}")
                    stp = ent - side * sd_rule
                    for m in range(me, m_out):
                        if m in x and ((x[m][4] <= stp) if side > 0 else (x[m][3] >= stp)):
                            C["참고(정리인데 규칙 폭 손절 닿음)"].append([pk, d, m, "P2 우선"]); break
                else: prob.append(f"모르는 사유 {why}")
                if prob: C["불일치 수"] += 1; ex(C["예시"], [pk, d, r, prob])
    B["신호 있는데 거래 없는 (나) 날"][pk] = nores
    B["진입 안 함 사유"][pk] = dict(skip_reason)
    C["신호 있는데 거래 없는 (가) 날"][pk] = ga_no
    C["P2 우선 거래"][pk] = p2first
res["B 나·다 날 다시 셈"] = B; res["C 가 날 조건부"] = C; res["D 날별 항등식"] = D

# ---------- E. 요약 다시 셈 ----------
def mdd(v):
    eq = pk_ = 0.0; m = 0.0
    for x in v: eq += x; pk_ = max(pk_, eq); m = min(m, eq - pk_)
    return m
def boot(v):
    n = len(v); rng = random.Random(0); out = []
    for _ in range(2000):
        s = []
        while len(s) < n:
            i = rng.randrange(0, n - 5 + 1); s += v[i:i + 5]
        out.append(sum(s[:n]))
    out.sort(); return [out[int(0.025 * 2000)], out[int(0.975 * 2000) - 1]]
E = {"불일치 수": 0, "예시": [], "판": {}}
p2v = [P2[d] for d in DAYS]; n = len(DAYS)
inc_sum = {}
for pk in LOG:
    dv = DAILY[pk]; comb = [dv["결합"][d] for d in DAYS]; inc = [dv["결합"][d] - P2[d] for d in DAYS]
    big = max(range(n), key=lambda i: inc[i])
    e = {"증분 합": sum(inc), "증분 앞 반": sum(inc[:n // 2]), "증분 뒤 반": sum(inc[n // 2:]),
         "증분 한 날 뺀": sum(inc) - inc[big], "가장 큰 증분 날": [DAYS[big], inc[big]],
         "결합 MDD": mdd(comb), "P2 MDD": mdd(p2v), "결합 합": sum(comb), "P2 합": sum(p2v), "결합 최악": min(comb),
         "−15 나쁜 날": [d for d in DAYS if dv["결합"][d] < -15 - 1e-9], "증분 95%": boot(inc),
         "진입 날": sum(1 for d in DAYS if LOGD[pk].get(d)), "보완 합": sum(dv["보완"][d] for d in DAYS), "P2 바뀐 몫 합": sum(dv["P2 바뀐 몫"][d] for d in DAYS),
         "P2 바뀐 날": sum(1 for d in DAYS if abs(dv["P2 바뀐 몫"][d]) > 1e-12)}
    inc_sum[pk] = e["증분 합"]; E["판"][pk] = e
for pk, e in E["판"].items():
    p, ver = pk.rsplit(" ", 1); k, s = p.split(" "); other = f"{k} {'s1.5' if s == 's1.0' else 's1.0'} {ver}"
    c = {"① 증분 > 0": e["증분 합"] > 0, "② 앞 · 뒤 반 > 0": e["증분 앞 반"] > 0 and e["증분 뒤 반"] > 0, "③ 한 날 빼도 > 0": e["증분 한 날 뺀"] > 0,
         "④ MDD 안 깊어짐": e["결합 MDD"] >= e["P2 MDD"] - 1e-9, "⑤ −15 나쁜 날 0": not e["−15 나쁜 날"], "⑥ 95% 하한 > 0": e["증분 95%"][0] > 0,
         "⑦ 이웃 부호 같음": (e["증분 합"] > 0) == (inc_sum[other] > 0), "⑧ 진입 날 ≥ 10": e["진입 날"] >= 10}
    e["조건"] = c
    o = OUT[p][ver]
    pairs = [("증분 합", e["증분 합"], o["증분 합"]), ("증분 앞 반", e["증분 앞 반"], o["증분 앞 반"]), ("증분 뒤 반", e["증분 뒤 반"], o["증분 뒤 반"]),
             ("증분 한 날 뺀", e["증분 한 날 뺀"], o["증분 한 날 뺀"]), ("결합 MDD", e["결합 MDD"], o["결합"]["MDD"]), ("P2 MDD", e["P2 MDD"], o["P2 혼자"]["MDD"]),
             ("결합 합", e["결합 합"], o["결합"]["합"]), ("P2 합", e["P2 합"], o["P2 혼자"]["합"]), ("결합 최악", e["결합 최악"], o["결합"]["최악"]),
             ("95% 하", e["증분 95%"][0], o["증분 95%"][0]), ("95% 상", e["증분 95%"][1], o["증분 95%"][1]), ("진입 날", e["진입 날"], o["보완 진입 날"]),
             ("보완 합", e["보완 합"], o["보완 단독 합"]), ("P2 바뀐 몫 합", e["P2 바뀐 몫 합"], o["P2 바뀐 몫 합"]), ("P2 바뀐 날", e["P2 바뀐 날"], o["P2 바뀐 날"]),
             ("가장 큰 증분 값", e["가장 큰 증분 날"][1], o["가장 큰 증분 날"][1])]
    for nm, a, b in pairs:
        if abs(a - b) > 1e-6: E["불일치 수"] += 1; ex(E["예시"], [pk, nm, a, b])
    if e["가장 큰 증분 날"][0] != o["가장 큰 증분 날"][0]: E["불일치 수"] += 1; ex(E["예시"], [pk, "가장 큰 증분 날", e["가장 큰 증분 날"][0], o["가장 큰 증분 날"][0]])
    if sorted(e["−15 나쁜 날"]) != sorted(o["−15 나쁜 날"]): E["불일치 수"] += 1; ex(E["예시"], [pk, "−15 나쁜 날", e["−15 나쁜 날"], o["−15 나쁜 날"]])
    for ck, cv in c.items():
        if o["조건"].get(ck) != cv: E["불일치 수"] += 1; ex(E["예시"], [pk, ck, cv, o["조건"].get(ck)])
    # 날 종류별 · 사유
    kk = collections.defaultdict(lambda: [0, 0.0]); rs = collections.Counter()
    for d in DAYS:
        for r in LOGD[pk].get(d, []): kk[KIND[d]][0] += 1; kk[KIND[d]][1] += DAILY[pk]["보완"][d]; rs[r[3]] += 1
    for kd, (cn, sm) in kk.items():
        ov = o["날 종류별(진입 날 · 보완 합)"].get(kd)
        if ov is None or ov[0] != cn or abs(ov[1] - sm) > 1e-6: E["불일치 수"] += 1; ex(E["예시"], [pk, "날 종류별", kd, [cn, sm], ov])
    if dict(rs) != o["정리 사유"]: E["불일치 수"] += 1; ex(E["예시"], [pk, "정리 사유", dict(rs), o["정리 사유"]])
    e["날 종류별"] = {kd: v for kd, v in kk.items()}; e["정리 사유"] = dict(rs)
verdict = {}
for p in PLANS:
    c1 = E["판"][f"{p} 원판"]["조건"]; c2 = E["판"][f"{p} 스트레스판"]["조건"]
    if not (c1["⑧ 진입 날 ≥ 10"] and c2["⑧ 진입 날 ≥ 10"]): v = "WAITING_DATA"
    elif all(c1.values()) and all(c2.values()): v = "지지"
    else: v = "지지 안 됨"
    verdict[p] = {"감사": v, "제출": OUT[p]["판정"], "같음": v == OUT[p]["판정"], "거짓 조건": [k for k, x in c1.items() if not x]}
    if v != OUT[p]["판정"]: E["불일치 수"] += 1; ex(E["예시"], [p, "판정", v, OUT[p]["판정"]])
E["판정"] = verdict
res["E 요약 다시 셈"] = E

# ---------- F. 결합 낙폭 가장 깊은 구간 ----------
F = {}
for pk in LOG:
    if not pk.endswith("원판"): continue
    dv = DAILY[pk]; eq = 0.0; peak = 0.0; peak_i = -1; best = (0.0, None, None)
    for i, d in enumerate(DAYS):
        eq += dv["결합"][d]
        if eq > peak: peak = eq; peak_i = i
        if eq - peak < best[0]: best = (eq - peak, peak_i, i)
    dd, a, b = best
    rows = [[DAYS[j], KIND[DAYS[j]], round(dv["결합"][DAYS[j]], 3), round(dv["보완"][DAYS[j]], 3), round(P2[DAYS[j]], 3)] for j in range(a + 1, b + 1)]
    F[pk] = {"낙폭": dd, "고점 날": DAYS[a] if a >= 0 else "시작", "바닥 날": DAYS[b], "구간 보완 합": sum(r[3] for r in rows), "구간 P2 합": sum(r[4] for r in rows),
             "구간 P2 혼자 MDD 같은 구간 몫": sum(r[4] for r in rows), "날별 [날, 종류, 결합, 보완, P2]": rows}
res["F 결합 낙폭 구간"] = F

# 참고: 스트레스판과 원판 차이 · 빈 구간과 겹친 날
res["참고"] = {
    "원판=스트레스판 날별 동일": {p: all(DAILY[f"{p} 원판"][kk] == DAILY[f"{p} 스트레스판"][kk] for kk in ("결합", "보완", "P2 바뀐 몫")) for p in PLANS},
    "885~915와 겹치는 빈 구간": {d: v for d, v in HOLES.items() if d in DAYS and v[0] <= 915 and v[1] >= 885},
    "20260623 1분봉 빈틈(873→903) 진입 분 903": [r for r in LOG["M1 s1.0 원판"] if r[0] == "20260623"],
}
OUTP.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
for k, v in res.items():
    if isinstance(v, dict) and "불일치 수" in v: print(k, "불일치", v["불일치 수"], v.get("예시"))
print(json.dumps(verdict, ensure_ascii=False))
print(json.dumps(B["신호 있는데 거래 없는 (나) 날"], ensure_ascii=False))
print(json.dumps(B["진입 안 함 사유"], ensure_ascii=False))
print(json.dumps(C["신호 있는데 거래 없는 (가) 날"], ensure_ascii=False))
print("D 반올림", D.get("반올림 차(1e-9 넘음)"), D.get("반올림 최대 차"))
for pk in LOG:
    dv = DAILY[pk]; ch = [(d, KIND[d], dv["P2 바뀐 몫"][d], LOGD[pk].get(d)) for d in DAYS if abs(dv["P2 바뀐 몫"][d]) > 1e-12]
    if ch: print("P2 바뀐 날", pk, ch)
print("P2 우선", json.dumps(C["P2 우선 거래"], ensure_ascii=False))
print("참고 C", C["참고(정리인데 규칙 폭 손절 닿음)"])
print(json.dumps(res["참고"], ensure_ascii=False))
for pk, f in F.items(): print(pk, round(f["낙폭"], 3), f["고점 날"], f["바닥 날"], round(f["구간 보완 합"], 3), round(f["구간 P2 합"], 3), len(f["날별 [날, 종류, 결합, 보완, P2]"]))
