"""COMP-0005 독립 감사(agent5). 비공개 실행기는 안 보고 규칙만으로 다시 셈.
실행: python3 audit5.py  (r8/research를 sys.path에 넣음)
주의: 판 반복 변수 섞임을 막으려고 판마다 값을 함수 안에서 새로 만든다(바깥 dv · e 재사용 금지)."""
import sys, json, random, collections, hashlib
from pathlib import Path
R8 = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/r8")
OUTP = Path(__file__).resolve().parent / "audit5.out"
sys.path.insert(0, str(R8 / "research"))
import kmf_nb as K

RS = R8 / "research"
SIG2 = json.loads((RS / "kmf_comp_lastm2_sig.json").read_text())
SIG1 = json.loads((RS / "kmf_comp_lastm_sig.json").read_text())
OUT = json.loads((RS / "kmf_comp_lastm2_out.json").read_text())
DAILY = json.loads((RS / "kmf_comp_lastm2_out_daily.json").read_text())
LOG = json.loads((RS / "kmf_comp_lastm2_out_log.json").read_text())
OUT4 = json.loads((RS / "kmf_comp_lastm_out.json").read_text())
DAILY4 = json.loads((RS / "kmf_comp_lastm_out_daily.json").read_text())
LOG4 = json.loads((RS / "kmf_comp_lastm_out_log.json").read_text())
DAYS = SIG2["meta"]["days"]; HOLES = SIG2["holes"]; P2 = DAILY["P2 혼자"]; KIND = DAILY["날 종류"]
N = len(DAYS); H = N // 2
COST = 0.04; RT = 2 * COST
PLANS = ["M12 s1.0", "M12 s1.5", "M1cap s1.0", "M1cap s1.5"]
VERS = ["원판", "스트레스판"]
PKS = [f"{p} {v}" for p in PLANS for v in VERS]
KN = {"나": "나 막힌 날(되돌림 켜짐)", "다": "다 P2 쉼", "가": "가 P2 본 날"}
res = {}

def ex(lst, x):
    if len(lst) < 3: lst.append(x)

def bylog(rows):
    g = collections.defaultdict(list)
    for r in rows: g[r[0]].append(r)
    return g
LOGD = {pk: bylog(LOG[pk]) for pk in LOG}
LOG4D = {pk: bylog(LOG4[pk]) for pk in LOG4}

# ---------- 0. 변환 ----------
Z = {"불일치 수": 0, "예시": [], "비교 칸": 0, "기타": {}}
Z["기타"]["원천 sha256"] = hashlib.sha256((RS / "kmf_comp_lastm_sig.json").read_bytes()).hexdigest()
Z["기타"]["sig2 sha256"] = hashlib.sha256((RS / "kmf_comp_lastm2_sig.json").read_bytes()).hexdigest()
Z["기타"]["sig2 sha256 = 영수증"] = Z["기타"]["sig2 sha256"] == OUT["_영수증"]["신호 표 sha256"]
Z["기타"]["날 목록 같음"] = SIG2["meta"]["days"] == SIG1["meta"]["days"]
Z["기타"]["holes 같음"] = SIG2["holes"] == SIG1["holes"]
Z["기타"]["P2 혼자 · 날 종류 COMP-0004와 같음"] = DAILY4["P2 혼자"] == P2 and DAILY4["날 종류"] == KIND
Z["기타"]["판 키"] = sorted(SIG2["sig"]) == sorted(PLANS)
cnt = {}
for s in ("1.0", "1.5"):
    m1 = SIG1["sig"][f"M1 s{s}"]; m2 = SIG1["sig"][f"M2 s{s}"]
    for p, rule in ((f"M12 s{s}", "M12"), (f"M1cap s{s}", "cap")):
        t = SIG2["sig"][p]
        if set(t) != set(m1) or set(t) != set(DAYS): Z["불일치 수"] += 1; ex(Z["예시"], [p, "날 키 다름"])
        for d in DAYS:
            a, b = m1.get(d, []), m2.get(d, [])
            if rule == "M12":
                exp = a if (a and b and a[0][1] == b[0][1]) else []
            else:
                exp = a
            Z["비교 칸"] += 1
            if t.get(d) != exp: Z["불일치 수"] += 1; ex(Z["예시"], [p, d, t.get(d), exp])
            if len(t.get(d, [])) > 1: Z["불일치 수"] += 1; ex(Z["예시"], [p, d, "행 2개 이상"])
        cnt[p] = sum(1 for d in DAYS if t.get(d))
    # 같은 방향 · 다른 방향 · 한쪽만 날 수
    both = [d for d in DAYS if m1.get(d) and m2.get(d)]
    Z["기타"][f"s{s} 날 수"] = {"M1 신호": sum(1 for d in DAYS if m1.get(d)), "M2 신호": sum(1 for d in DAYS if m2.get(d)),
                             "둘 다": len(both), "둘 다 · 같은 방향": sum(1 for d in both if m1[d][0][1] == m2[d][0][1]),
                             "둘 다 · 다른 방향": sum(1 for d in both if m1[d][0][1] != m2[d][0][1]),
                             "둘 다인데 진입 분 · 손절 폭 다름(M1 행 씀)": sum(1 for d in both if m1[d][0][0] != m2[d][0][0] or abs(m1[d][0][3] - m2[d][0][3]) > 1e-12)}
Z["기타"]["신호 날 수"] = cnt
res["0 변환"] = Z

# ---------- A · B 체결 ----------
def run_trade(d, me, side, sd, lim, stress):
    """규칙으로 한 거래 → ((정리 분, 사유, 손익), None) 또는 (None, 미진입 사유)."""
    if lim < 3: return None, "한도<3"
    sd = min(sd, lim - RT)
    if sd < 0.5: return None, "폭<0.5"
    x = K.BY[d]; ent = x[me][2]; stop = ent - side * sd
    h0 = HOLES.get(d)
    for m in range(me, 935):
        if m not in x: continue
        if stress and h0 and me < h0[0] and m > h0[1] and m >= h0[0]:
            return (m, "손절(빈 구간)", side * (stop - ent) - RT), None
        o, h, l = x[m][2], x[m][3], x[m][4]
        if m == me: o = ent
        if m >= 915: return (m, "정리", side * (o - ent) - RT), None
        if (l <= stop) if side > 0 else (h >= stop):
            pxx = min(o, stop) if side > 0 else max(o, stop)
            return (m, "손절", side * (pxx - ent) - RT), None
    return (935, "끝", side * (K.last_close(d) - ent) - RT), None

A = {"불일치 수": 0, "예시": [], "비교 날": 0, "비교 거래": 0, "신호 있는데 거래 없는 (나) 날": {}, "진입 안 함 사유": {},
     "참고: 쉰 (나) 날이 COMP-0004 M1 쉰 날에 들어감": {}}
B = {"불일치 수": 0, "예시": [], "비교 거래": 0, "신호 있는데 거래 없는 (가) 날": {}, "P2 우선 거래": {}, "참고(정리 · P2 우선인데 규칙 폭 손절 먼저 닿음)": [],
     "참고: M1cap 함의 폭 최대(손절 거래)": {}, "참고: 규칙 폭 > 14.92인 (가) 신호 날": {}}
C = {"불일치 수": 0, "예시": [], "반올림 최대 차": 0.0}
NORES4 = {"20260116", "20260210", "20260921"}   # COMP-0004 감사(agent4)에서 M1 · M2 모든 판이 쉰 (나) 날

def audit_plan(pk):
    p, ver = pk.rsplit(" ", 1); stress = ver == "스트레스판"
    dv = DAILY[pk]; lgd = LOGD[pk]; sig = SIG2["sig"][p]
    nores = []; skip = collections.Counter(); ga_no = []; p2first = []; capw = 0.0
    for d in DAYS:
        sg = sig.get(d, []); lg = lgd.get(d, []); kind = KIND[d]
        # C 항등식
        lhs = dv["결합"][d] - P2[d]; rhs = dv["보완"][d] + dv["P2 바뀐 몫"][d]
        if abs(lhs - rhs) > 1e-6: C["불일치 수"] += 1; ex(C["예시"], [pk, d, lhs, rhs, "결합−P2≠보완+바뀐 몫"])
        dif = abs(dv["보완"][d] - sum(r[4] for r in lg)); C["반올림 최대 차"] = max(C["반올림 최대 차"], dif, abs(lhs - rhs))
        if dif > 1e-6: C["불일치 수"] += 1; ex(C["예시"], [pk, d, dv["보완"][d], sum(r[4] for r in lg), "보완≠거래 합"])
        if len(lg) > 1: C["불일치 수"] += 1; ex(C["예시"], [pk, d, "하루 거래 2개 이상"])
        if lg and not sg: A["불일치 수"] += 1; ex(A["예시"], [pk, d, "신호 없는데 거래"]); continue
        if kind in (KN["나"], KN["다"]):
            A["비교 날"] += 1
            if dv["P2 바뀐 몫"][d] != 0: A["불일치 수"] += 1; ex(A["예시"], [pk, d, "나·다 날인데 P2 바뀐 몫≠0", dv["P2 바뀐 몫"][d]])
            lim = 15.0 if kind == KN["다"] else 15.0 + min(0.0, P2[d])
            mine, why = (None, None)
            if sg:
                me, side, _, sd, _, _ = sg[0]
                mine, why = run_trade(d, me, side, sd, lim, stress)
                if mine is None: skip[why] += 1
            if mine is None and lg:
                A["불일치 수"] += 1; ex(A["예시"], [pk, d, kind, "규칙상 진입 안 함", why, lg])
            elif mine is not None and not lg:
                if kind == KN["나"]: nores.append([d, round(lim, 4), round(P2[d], 4)])
                else: A["불일치 수"] += 1; ex(A["예시"], [pk, d, kind, "규칙상 진입인데 거래 없음", mine])
            elif mine is not None and lg:
                A["비교 거래"] += 1; r = lg[0]
                rs = "손절" if mine[1].startswith("손절") else mine[1]
                if r[1] != sg[0][0] or r[2] != mine[0] or r[3] != rs or abs(r[4] - mine[2]) > 1e-6:
                    A["불일치 수"] += 1; ex(A["예시"], [pk, d, kind, "다시 셈", list(mine), "기록", r])
        else:
            if sg and not lg: ga_no.append(d)
            if sg and p.startswith("M1cap") and sg[0][3] > 15 - RT: B["참고: 규칙 폭 > 14.92인 (가) 신호 날"].setdefault(pk, []).append([d, round(sg[0][3], 4)])
            for r in lg:
                B["비교 거래"] += 1
                me, side, _, sd_rule, _, _ = sg[0]; x = K.BY[d]
                if r[1] != me: B["불일치 수"] += 1; ex(B["예시"], [pk, d, "진입 분 다름", r, me]); continue
                ent = x[me][2]; xp = ent + side * (r[4] + RT); m_out = r[2]; why = r[3]
                if m_out not in x: B["불일치 수"] += 1; ex(B["예시"], [pk, d, "정리 분 자료 없음", r]); continue
                o_out = ent if m_out == me else x[m_out][2]
                prob = []
                if why == "손절":
                    w = side * (ent - xp); stp = ent - side * w
                    l, h = x[m_out][4], x[m_out][3]
                    gap = (o_out < stp - 1e-9) if side > 0 else (o_out > stp + 1e-9)
                    capw = max(capw, w)
                    lim_w = sd_rule if not p.startswith("M1cap") else min(sd_rule, 15 - RT)
                    if w > lim_w + 1e-6 and not gap: prob.append(f"함의 폭 {w:.4f} > 허용 폭 {lim_w:.4f}")
                    if w < 0.5 - 1e-6 and not gap: prob.append(f"함의 폭 {w:.4f} < 0.5")
                    if not ((l <= stp + 1e-6) if side > 0 else (h >= stp - 1e-6)): prob.append("정리 분에 손절가 닿지 않음")
                    for m in range(me, m_out):
                        if m in x and ((x[m][4] <= stp + 1e-9) if side > 0 else (x[m][3] >= stp - 1e-9)): prob.append(f"앞 분 {m}에 이미 닿음"); break
                    if gap: prob.append("시가 갭 손절(함의 폭 해석 주의)")
                elif why in ("정리", "P2 우선"):
                    if why == "정리":
                        first915 = next((mm for mm in range(915, 935) if mm in x), None)
                        if m_out != first915: prob.append(f"정리 분 {m_out} ≠ 915 이상 첫 분 {first915}")
                        if abs(xp - x[m_out][2]) > 1e-6: prob.append(f"정리가 {xp:.4f} ≠ 시가 {x[m_out][2]}")
                    else:
                        p2first.append(d)
                        if not (me <= m_out < 915): prob.append(f"P2 우선 분 {m_out} 범위 밖")
                        if abs(xp - o_out) > 1e-6: prob.append(f"P2 우선 정리가 {xp:.4f} ≠ 그 분 시가 {o_out}")
                    stp = ent - side * (sd_rule if not p.startswith("M1cap") else min(sd_rule, 15 - RT))
                    for m in range(me, m_out):
                        if m in x and ((x[m][4] <= stp) if side > 0 else (x[m][3] >= stp)):
                            B["참고(정리 · P2 우선인데 규칙 폭 손절 먼저 닿음)"].append([pk, d, m, why]); break
                else: prob.append(f"모르는 사유 {why}")
                if prob: B["불일치 수"] += 1; ex(B["예시"], [pk, d, r, prob])
    A["신호 있는데 거래 없는 (나) 날"][pk] = nores
    A["진입 안 함 사유"][pk] = dict(skip)
    A["참고: 쉰 (나) 날이 COMP-0004 M1 쉰 날에 들어감"][pk] = all(r[0] in NORES4 for r in nores)
    B["신호 있는데 거래 없는 (가) 날"][pk] = ga_no
    B["P2 우선 거래"][pk] = p2first
    if p.startswith("M1cap"): B["참고: M1cap 함의 폭 최대(손절 거래)"][pk] = capw
    return len(nores)

NORES_N = {pk: audit_plan(pk) for pk in PKS}
res["A 나·다 날 다시 셈"] = A; res["B 가 날 조건부"] = B; res["C 날별 항등식"] = C

# ---------- D. 요약 ----------
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

P2V = [P2[d] for d in DAYS]
def summ(pk):
    dv = DAILY[pk]; lgd = LOGD[pk]
    comb = [dv["결합"][d] for d in DAYS]; inc = [dv["결합"][d] - P2[d] for d in DAYS]
    big = max(range(N), key=lambda i: inc[i])
    kk = {}; rs = collections.Counter()
    for d in DAYS:
        lg = lgd.get(d, [])
        for r in lg: rs[r[3]] += 1
        if lg:
            v = kk.setdefault(KIND[d], [0, 0.0]); v[0] += 1; v[1] += dv["보완"][d]
    return {"증분 합": sum(inc), "증분 앞 반": sum(inc[:H]), "증분 뒤 반": sum(inc[H:]), "증분 한 날 뺀": sum(inc) - inc[big],
            "가장 큰 증분 날": [DAYS[big], inc[big]], "결합 MDD": mdd(comb), "P2 MDD": mdd(P2V), "결합 합": sum(comb), "P2 합": sum(P2V),
            "결합 최악": min(comb), "P2 최악": min(P2V), "−15 나쁜 날": [d for d in DAYS if dv["결합"][d] < -15 - 1e-9], "증분 95%": boot(inc),
            "진입 날": sum(1 for d in DAYS if lgd.get(d)), "보완 합": sum(dv["보완"][d] for d in DAYS),
            "P2 바뀐 몫 합": sum(dv["P2 바뀐 몫"][d] for d in DAYS), "P2 바뀐 날": sum(1 for d in DAYS if abs(dv["P2 바뀐 몫"][d]) > 1e-12),
            "날 종류별": kk, "정리 사유": dict(rs), "되돌림 보유로 쉰 날": NORES_N[pk]}

D = {"불일치 수": 0, "예시": [], "판": {}}
SUM = {pk: summ(pk) for pk in PKS}
for pk in PKS:
    e = SUM[pk]; p, ver = pk.rsplit(" ", 1); fam, s = p.split(" ")
    other = f"{fam} {'s1.5' if s == 's1.0' else 's1.0'} {ver}"
    c = {"① 증분 > 0": e["증분 합"] > 0, "② 앞 · 뒤 반 > 0": e["증분 앞 반"] > 0 and e["증분 뒤 반"] > 0, "③ 한 날 빼도 > 0": e["증분 한 날 뺀"] > 0,
         "④ MDD 안 깊어짐": e["결합 MDD"] >= e["P2 MDD"] - 1e-9, "⑤ −15 나쁜 날 0": not e["−15 나쁜 날"], "⑥ 95% 하한 > 0": e["증분 95%"][0] > 0,
         "⑦ 이웃 부호 같음": (e["증분 합"] > 0) == (SUM[other]["증분 합"] > 0), "⑧ 진입 날 ≥ 10": e["진입 날"] >= 10}
    e["조건"] = c
    o = OUT[p][ver]
    pairs = [("증분 합", e["증분 합"], o["증분 합"]), ("증분 앞 반", e["증분 앞 반"], o["증분 앞 반"]), ("증분 뒤 반", e["증분 뒤 반"], o["증분 뒤 반"]),
             ("증분 한 날 뺀", e["증분 한 날 뺀"], o["증분 한 날 뺀"]), ("결합 MDD", e["결합 MDD"], o["결합"]["MDD"]), ("P2 MDD", e["P2 MDD"], o["P2 혼자"]["MDD"]),
             ("결합 합", e["결합 합"], o["결합"]["합"]), ("P2 합", e["P2 합"], o["P2 혼자"]["합"]), ("결합 최악", e["결합 최악"], o["결합"]["최악"]),
             ("P2 최악", e["P2 최악"], o["P2 혼자"]["최악"]),
             ("95% 하", e["증분 95%"][0], o["증분 95%"][0]), ("95% 상", e["증분 95%"][1], o["증분 95%"][1]), ("진입 날", e["진입 날"], o["보완 진입 날"]),
             ("보완 합", e["보완 합"], o["보완 단독 합"]), ("P2 바뀐 몫 합", e["P2 바뀐 몫 합"], o["P2 바뀐 몫 합"]), ("P2 바뀐 날", e["P2 바뀐 날"], o["P2 바뀐 날"]),
             ("가장 큰 증분 값", e["가장 큰 증분 날"][1], o["가장 큰 증분 날"][1]), ("되돌림 보유로 쉰 날", e["되돌림 보유로 쉰 날"], o["되돌림 보유로 쉰 날"]),
             ("날 수", N, o["날 수"])]
    for nm, a, b in pairs:
        if abs(a - b) > 1e-6: D["불일치 수"] += 1; ex(D["예시"], [pk, nm, a, b])
    if e["가장 큰 증분 날"][0] != o["가장 큰 증분 날"][0]: D["불일치 수"] += 1; ex(D["예시"], [pk, "가장 큰 증분 날", e["가장 큰 증분 날"][0], o["가장 큰 증분 날"][0]])
    if sorted(e["−15 나쁜 날"]) != sorted(o["−15 나쁜 날"]): D["불일치 수"] += 1; ex(D["예시"], [pk, "−15 나쁜 날", e["−15 나쁜 날"], o["−15 나쁜 날"]])
    for ck, cv in c.items():
        if o["조건"].get(ck) != cv: D["불일치 수"] += 1; ex(D["예시"], [pk, ck, cv, o["조건"].get(ck)])
    if set(o["조건"]) != set(c): D["불일치 수"] += 1; ex(D["예시"], [pk, "조건 이름 다름", sorted(o["조건"])])
    ok_kind = set(e["날 종류별"]) == set(o["날 종류별(진입 날 · 보완 합)"]) and all(
        o["날 종류별(진입 날 · 보완 합)"][kd][0] == v[0] and abs(o["날 종류별(진입 날 · 보완 합)"][kd][1] - v[1]) <= 1e-6 for kd, v in e["날 종류별"].items())
    if not ok_kind: D["불일치 수"] += 1; ex(D["예시"], [pk, "날 종류별", e["날 종류별"], o["날 종류별(진입 날 · 보완 합)"]])
    if e["정리 사유"] != o["정리 사유"]: D["불일치 수"] += 1; ex(D["예시"], [pk, "정리 사유", e["정리 사유"], o["정리 사유"]])
    D["판"][pk] = e
verdict = {}
for p in PLANS:
    c1 = SUM[f"{p} 원판"]["조건"]; c2 = SUM[f"{p} 스트레스판"]["조건"]
    if not (c1["⑧ 진입 날 ≥ 10"] and c2["⑧ 진입 날 ≥ 10"]): v = "WAITING_DATA"
    elif all(c1.values()) and all(c2.values()): v = "지지"
    else: v = "지지 안 됨"
    verdict[p] = {"감사": v, "제출": OUT[p]["판정"], "같음": v == OUT[p]["판정"], "거짓 조건(원판)": [k for k, x in c1.items() if not x],
                  "거짓 조건(스트레스판)": [k for k, x in c2.items() if not x]}
    if v != OUT[p]["판정"]: D["불일치 수"] += 1; ex(D["예시"], [p, "판정", v, OUT[p]["판정"]])
D["판정"] = verdict
D["확인 불가"] = {pk: {"P2 한도 줄어든 날(DSE < 15)": OUT[pk.rsplit(' ', 1)[0]][pk.rsplit(' ', 1)[1]]["P2 한도 줄어든 날(DSE < 15)"],
                       "겹친 분": OUT[pk.rsplit(' ', 1)[0]][pk.rsplit(' ', 1)[1]]["겹친 분"]} for pk in PKS}
res["D 요약 다시 셈"] = D

# ---------- E. 보조: 같은 s의 COMP-0004 M1 결합 대비 ----------
E = {"불일치 수": 0, "예시": [], "판": {}}
for pk in PKS:
    p, ver = pk.rsplit(" ", 1); s = p.split(" ")[1]
    m1k = f"M1 {s} {ver}"
    a = DAILY[pk]["결합"]; b = DAILY4[m1k]["결합"]
    diff = [a[d] - b[d] for d in DAYS]; mx = max(diff)
    e = {"기준": m1k, "차 합": sum(diff), "앞 반": sum(diff[:H]), "뒤 반": sum(diff[H:]), "최대 하루 뺀": sum(diff) - mx,
         "95%": boot(diff), "M1 결합 MDD": mdd([b[d] for d in DAYS]), "차 0 아닌 날": sum(1 for x in diff if abs(x) > 1e-9)}
    o = OUT[p][ver]["보조 · COMP-0004 M1 대비"]
    for nm in ("차 합", "앞 반", "뒤 반", "최대 하루 뺀", "M1 결합 MDD"):
        if abs(e[nm] - o[nm]) > 1e-6: E["불일치 수"] += 1; ex(E["예시"], [pk, nm, e[nm], o[nm]])
    for j in (0, 1):
        if abs(e["95%"][j] - o["95%"][j]) > 1e-6: E["불일치 수"] += 1; ex(E["예시"], [pk, f"95%[{j}]", e["95%"][j], o["95%"][j]])
    # M1 결합 MDD는 COMP-0004 요약 값과도 견줌
    o4 = OUT4[f"M1 {s}"][ver]["결합"]["MDD"]
    if abs(e["M1 결합 MDD"] - o4) > 1e-6: E["불일치 수"] += 1; ex(E["예시"], [pk, "M1 결합 MDD ≠ COMP-0004 요약", e["M1 결합 MDD"], o4])
    E["판"][pk] = e
res["E 보조 다시 셈"] = E

# ---------- F. H4 ----------
F = {}
for s in ("s1.0", "s1.5"):
    m1sig = SIG1["sig"][f"M1 {s}"]; m12 = SIG2["sig"][f"M12 {s}"]
    dv4 = DAILY4[f"M1 {s} 원판"]; lg4 = LOG4D[f"M1 {s} 원판"]
    groups = {"남은 날(M12 신호 있음)": [d for d in DAYS if m1sig.get(d) and m12.get(d)],
              "뺀 날(M1만 · M12 없음)": [d for d in DAYS if m1sig.get(d) and not m12.get(d)]}
    tab = {}
    for g, ds in groups.items():
        row = {}
        for half, sub in (("전체", ds), ("앞 반", [d for d in ds if DAYS.index(d) < H]), ("뒤 반", [d for d in ds if DAYS.index(d) >= H])):
            row[half] = {"신호 날": len(sub), "M1 거래 날": sum(1 for d in sub if lg4.get(d)),
                         "M1 보완 합": round(sum(dv4["보완"][d] for d in sub), 4), "M1 P2 바뀐 몫 합": round(sum(dv4["P2 바뀐 몫"][d] for d in sub), 4),
                         "M1 결합−P2 합": round(sum(dv4["결합"][d] - P2[d] for d in sub), 4)}
        # 날 종류별 보완 합(전체)
        kk = {}
        for d in ds:
            v = kk.setdefault(KIND[d], [0, 0.0]); v[0] += 1; v[1] = round(v[1] + dv4["보완"][d], 4)
        row["날 종류별 [날, M1 보완 합]"] = kk
        tab[g] = row
    # 같은 날 M12 원판 보완과 COMP-0004 M1 보완이 같은지(남은 날)
    dv12 = DAILY[f"M12 {s} 원판"]
    same = [d for d in groups["남은 날(M12 신호 있음)"] if abs(dv12["보완"][d] - dv4["보완"][d]) > 1e-9]
    tab["참고: 남은 날 중 M12 보완 ≠ M1 보완인 날"] = [[d, KIND[d], round(dv12["보완"][d], 4), round(dv4["보완"][d], 4)] for d in same]
    # M12 결합 낙폭 구간
    for ver in ("원판",):
        dv = DAILY[f"M12 {s} {ver}"]; eq = 0.0; peak = 0.0; peak_i = -1; best = (0.0, None, None)
        for i, d in enumerate(DAYS):
            eq += dv["결합"][d]
            if eq > peak: peak = eq; peak_i = i
            if eq - peak < best[0]: best = (eq - peak, peak_i, i)
        dd, a, b = best
        rows = [[DAYS[j], KIND[DAYS[j]], round(dv["결합"][DAYS[j]], 3), round(dv["보완"][DAYS[j]], 3), round(P2[DAYS[j]], 3)] for j in range(a + 1, b + 1)]
        # P2 혼자 낙폭 구간도 같이
        eq = 0.0; peak = 0.0; pi = -1; bp = (0.0, None, None)
        for i, d in enumerate(DAYS):
            eq += P2[d]
            if eq > peak: peak = eq; pi = i
            if eq - peak < bp[0]: bp = (eq - peak, pi, i)
        tab[f"M12 {s} {ver} 결합 낙폭"] = {"낙폭": round(dd, 4), "고점 날": DAYS[a] if a >= 0 else "시작", "바닥 날": DAYS[b], "날 수": len(rows),
                                         "구간 보완 합": round(sum(r[3] for r in rows), 3), "구간 P2 합": round(sum(r[4] for r in rows), 3),
                                         "날별 [날, 종류, 결합, 보완, P2]": rows,
                                         "참고: P2 혼자 낙폭": [round(bp[0], 4), DAYS[bp[1]] if bp[1] >= 0 else "시작", DAYS[bp[2]]]}
    F[s] = tab
res["F H4 진단"] = F

# ---------- G. H5 ----------
G = {"불일치 수": 0, "예시": []}
for s in ("s1.0", "s1.5"):
    for ver in VERS:
        cap = DAILY[f"M1cap {s} {ver}"]; m1 = DAILY4[f"M1 {s} {ver}"]
        lc = LOGD[f"M1cap {s} {ver}"]; l1 = LOG4D[f"M1 {s} {ver}"]
        rows = []; tot = [0.0, 0.0, 0.0]; bykind = collections.Counter()
        for d in DAYS:
            dc = cap["결합"][d] - m1["결합"][d]; db = cap["보완"][d] - m1["보완"][d]; dp = cap["P2 바뀐 몫"][d] - m1["P2 바뀐 몫"][d]
            if abs(dc - (db + dp)) > 1e-6: G["불일치 수"] += 1; ex(G["예시"], [s, ver, d, dc, db, dp])
            if max(abs(dc), abs(db), abs(dp)) > 1e-9:
                tot[0] += dc; tot[1] += db; tot[2] += dp; bykind[KIND[d]] += 1
                sg = SIG2["sig"][f"M1cap {s}"].get(d, [])
                rows.append({"날": d, "종류": KIND[d], "결합 차": round(dc, 4), "보완 차": round(db, 4), "P2 차": round(dp, 4),
                             "규칙 폭": round(sg[0][3], 4) if sg else None, "P2 혼자": round(P2[d], 4),
                             "M1cap 거래": [r[1:] for r in lc.get(d, [])], "M1 거래": [r[1:] for r in l1.get(d, [])]})
        G[f"{s} {ver}"] = {"차 합": round(tot[0], 4), "보완 차 합": round(tot[1], 4), "P2 차 합": round(tot[2], 4), "차 0 아닌 날": len(rows),
                           "종류별 날 수": dict(bykind), "날 목록": rows}
def dd_window(vals):
    eq = 0.0; peak = 0.0; pi = -1; best = (0.0, -1, -1)
    for i, x in enumerate(vals):
        eq += x
        if eq > peak: peak = eq; pi = i
        if eq - peak < best[0]: best = (eq - peak, pi, i)
    return best
for s in ("s1.0", "s1.5"):
    cap = DAILY[f"M1cap {s} 원판"]; m1 = DAILY4[f"M1 {s} 원판"]
    for nm, dv in ((f"M1cap {s} 원판", cap), (f"COMP-0004 M1 {s} 원판", m1)):
        dd, a, b = dd_window([dv["결합"][d] for d in DAYS])
        rows = [[DAYS[j], KIND[DAYS[j]], round(dv["결합"][DAYS[j]], 3), round(dv["보완"][DAYS[j]], 3), round(dv["P2 바뀐 몫"][DAYS[j]], 3), round(P2[DAYS[j]], 3)] for j in range(a + 1, b + 1)]
        G[f"{nm} 결합 낙폭"] = {"낙폭": round(dd, 4), "고점 날": DAYS[a] if a >= 0 else "시작", "바닥 날": DAYS[b],
                               "구간 보완 합": round(sum(r[3] for r in rows), 3), "구간 P2 바뀐 몫 합": round(sum(r[4] for r in rows), 3), "구간 P2 혼자 합": round(sum(r[5] for r in rows), 3),
                               "날별 [날, 종류, 결합, 보완, P2 바뀐 몫, P2 혼자]": rows}
res["G H5 진단"] = G

res["참고"] = {
    "원판=스트레스판 날별 동일": {p: all(DAILY[f"{p} 원판"][k] == DAILY[f"{p} 스트레스판"][k] for k in ("결합", "보완", "P2 바뀐 몫")) and LOG[f"{p} 원판"] == LOG[f"{p} 스트레스판"] for p in PLANS},
    "885~915와 겹치는 빈 구간": {d: v for d, v in HOLES.items() if d in DAYS and v[0] <= 915 and v[1] >= 885},
}
OUTP.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))

for k, v in res.items():
    if isinstance(v, dict) and "불일치 수" in v: print(k, "불일치", v["불일치 수"], json.dumps(v.get("예시"), ensure_ascii=False)[:800])
print("0 기타", json.dumps(Z["기타"], ensure_ascii=False))
print("판정", json.dumps(verdict, ensure_ascii=False))
print("A 쉰 나 날", json.dumps(A["신호 있는데 거래 없는 (나) 날"], ensure_ascii=False))
print("A 미진입 사유", json.dumps(A["진입 안 함 사유"], ensure_ascii=False), A["비교 날"], A["비교 거래"])
print("A 쉰 날 ⊆ COMP4", json.dumps(A["참고: 쉰 (나) 날이 COMP-0004 M1 쉰 날에 들어감"], ensure_ascii=False))
print("B 가 날 거래 없음", json.dumps(B["신호 있는데 거래 없는 (가) 날"], ensure_ascii=False), B["비교 거래"])
print("B P2 우선", json.dumps(B["P2 우선 거래"], ensure_ascii=False))
print("B 참고", B["참고(정리 · P2 우선인데 규칙 폭 손절 먼저 닿음)"], B["참고: M1cap 함의 폭 최대(손절 거래)"], json.dumps(B["참고: 규칙 폭 > 14.92인 (가) 신호 날"]))
print("C 반올림", C["반올림 최대 차"])
print("참고", json.dumps(res["참고"], ensure_ascii=False))
