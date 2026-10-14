# COMP-0003 독립 감사 (agent3) - 결합 실행기 코드는 보지 않고 규칙만으로 다시 셈
import os
import sys, json, random, collections
R8 = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/r8"
OUT = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/comp/agent3/audit3.out" + os.getenv("AUD_SUF", "")
sys.path.insert(0, R8 + "/research")
import kmf_nb as K

RS = R8 + "/research/"
SIG = json.load(open(RS + "kmf_comp_joint_sig.json"))
SUM = json.load(open(RS + "kmf_comp_joint_out.json"))
DAILY = json.load(open(RS + "kmf_comp_joint_out_daily.json"))
LOG = json.load(open(RS + "kmf_comp_joint_out_log.json"))
DAYS = sorted(SIG["meta"]["days"]) if isinstance(SIG["meta"]["days"], list) else None
HOLES = SIG["holes"]
import os
# 정정(코디네이터 2026-10-14): 기록 손익 = 정리 쪽 비용 0.04만 뺀 값 -> 정리가 = 진입가 + 방향*(기록 손익 + 0.04), 실제 손익 = 기록 - 0.04
C2 = float(os.getenv("AUD_C", K.COST))
ENTRY_COST = float(os.getenv("AUD_EC", K.COST))
TIE = 1e-6  # 기록 손익이 소수 6자리 반올림이라 손절가와 고/저가가 이 안이면 닿음 여부 판단 불가(경계)
TOL = 1e-5
EPS = 1e-9

def bar(d, m): return K.BY[d].get(m)
def first_bar_at_or_after(d, m):
    ms = [x for x in sorted(K.BY[d]) if x >= m]
    return ms[0] if ms else None
def mins_between(d, a, b):  # a <= m < b 인 1분봉 분
    return [m for m in sorted(K.BY[d]) if a <= m < b]
def touched_stop(b, dr, S): return (b[4] <= S + 1e-12) if dr > 0 else (b[3] >= S - 1e-12)
def touched_tgt(b, dr, T): return (b[3] >= T - 1e-12) if dr > 0 else (b[4] <= T + 1e-12)

PANS = list(LOG.keys())
res = {"판별": {}, "항목별": {}, "예시": {}}
cnt = collections.Counter(); ex = collections.defaultdict(list); ref = collections.Counter(); refex = collections.defaultdict(list)
info = collections.Counter()
def bad(key, pan, msg):
    cnt[key] += 1
    if len(ex[key]) < 3: ex[key].append(pan + " | " + msg)
def note(key, pan, msg):
    ref[key] += 1
    if len(refex[key]) < 3: refex[key].append(pan + " | " + msg)

hold_min = {}
for pan in PANS:
    rule = pan.split()[0]; stress = pan.endswith("스트레스판")
    trades = LOG[pan]
    perday = collections.Counter(t[0] for t in trades)
    for d, n in perday.items():
        if n > 1: bad("1. 하루 거래 2개 이상", pan, f"{d} {n}개")
    hm = 0
    for (d, me, xm, why, pnl) in trades:
        cnt["거래 수(검사함)"] += 0
        info["거래 총수"] += 1
        hm += xm - me
        rows = [r for r in SIG["sig"][rule].get(d, []) if r[0] == me]
        if not rows:
            bad("1. 진입 분이 신호 표에 없음", pan, f"{d} me={me}"); continue
        if len(rows) > 1: info["같은 진입 분 신호 여러 줄"] += 1
        me_, dr, T, wr, xr, m0 = rows[0]
        if me < m0: bad("1. 진입 분 < 신호 분(미래 참조)", pan, f"{d} me={me} m0={m0}")
        if d not in DAYS: bad("1. 평가 날 밖 거래", pan, d)
        eb = bar(d, me)
        if eb is None: bad("2. 진입 분 1분봉 없음", pan, f"{d} {me}"); continue
        E = eb[2]
        X = E + dr * (pnl + C2)
        xb = bar(d, xm)
        if xm < me: bad("2. 정리 분 < 진입 분", pan, f"{d}"); continue
        exit_lim = first_bar_at_or_after(d, min(xr, 915))
        lastm = max(K.BY[d])
        if why not in ("날 끝",) and exit_lim is not None and xm > exit_lim:
            bad("2. 정리 분이 규칙 정리 분 뒤", pan, f"{d} xm={xm} 규칙={exit_lim} 사유={why}")
        if xb is None and why != "빈 구간 손절(스트레스)":
            bad("2. 정리 분 1분봉 없음", pan, f"{d} {xm} {why}"); continue
        Sr = E - dr * wr  # 규칙 손절 폭 기준 손절가
        hole = HOLES.get(d)
        # 앞선 분들: 진입 분 ~ 정리 분 앞
        prev = mins_between(d, me, xm)
        if stress and hole:  # 스트레스판: 빈 구간 안 분은 볼 수 없다고 보고 뺀 쪽도 따로 셈
            prev_vis = [m for m in prev if not (hole[0] <= m <= hole[1])]
        else:
            prev_vis = prev
        def tgt_hit_before(ms): return [m for m in ms if T is not None and touched_tgt(bar(d, m), dr, T)]
        if why == "손절":
            o = xb[2]
            gap = (dr > 0 and abs(X - o) < TOL and o < E - dr * 0) and False
            S_imp = X; w_imp = dr * (E - S_imp)
            if not touched_stop(xb, dr, S_imp + dr * TOL):
                bad("2. 손절: 정리 분에 그 손절가 닿지 않음", pan, f"{d} xm={xm} 손절가={S_imp:.4f} 봉={xb[2:6]}")
            gap_case = abs(X - o) < TOL and ((dr > 0 and o < E) or (dr < 0 and o > E)) and xm != me
            if gap_case and (w_imp > wr + TOL or w_imp < 0.5 - TOL):
                # 시가가 손절가를 넘어 더 나쁘게 체결: 손절가 S는 [시가 쪽] 어딘가
                info["손절 시가 갭 체결(따로 셈)"] += 1
                lo_ms = prev_vis
                ext = (min(bar(d, m)[4] for m in lo_ms) if dr > 0 else max(bar(d, m)[3] for m in lo_ms)) if lo_ms else None
                wmax = min(wr, dr * (E - o))
                ok = wmax >= 0.5 - TOL and (ext is None or wmax > dr * (E - ext) + 1e-12)
                if not ok: bad("2. 손절(갭): 맞는 손절 폭 없음", pan, f"{d} xm={xm} 시가={o} wmax={wmax:.4f}")
            else:
                if gap_case: info["손절 시가 = 손절가 근처(갭 겸 폭 범위 안)"] += 1
                if w_imp > wr + TOL: bad("2. 손절: 함의 손절 폭 > 규칙 손절 폭", pan, f"{d} 함의={w_imp:.5f} 규칙={wr:.5f}")
                if w_imp < 0.5 - TOL: bad("2. 손절: 함의 손절 폭 < 0.5", pan, f"{d} 함의={w_imp:.5f}")
                # 가격 규칙: 롱 min(시가, S)
                exp = min(o, S_imp) if dr > 0 else max(o, S_imp)
                if abs(exp - X) > TOL: bad("2. 손절: 가격 규칙 불일치", pan, f"{d} X={X} 기대={exp}")
                if w_imp < wr - 1e-6: info["손절 폭이 규칙보다 좁음(쿠션 추정)"] += 1
                hits = [m for m in prev_vis if touched_stop(bar(d, m), dr, S_imp - dr * TIE)]
                ties = [m for m in prev_vis if m not in hits and touched_stop(bar(d, m), dr, S_imp + dr * TIE)]
                if hits: bad("2. 손절: 그 손절가에 더 먼저 닿은 분 있음", pan, f"{d} 먼저={hits[0]} xm={xm}")
                if ties: note("참고 · 손절: 앞선 분 고/저가 = 손절가(반올림 안 · 경계)", pan, f"{d} 경계 분={ties[0]} 저/고={bar(d, ties[0])[4] if dr > 0 else bar(d, ties[0])[3]} 손절가={S_imp:.6f} xm={xm}")
                xe = xb[4] if dr > 0 else xb[3]
                if abs(xe - S_imp) <= TIE and abs(xb[2] - S_imp) > TIE: note("참고 · 손절: 정리 분 고/저가 = 손절가(경계에서 닿음으로 처리)", pan, f"{d} xm={xm} 저/고={xe} 손절가={S_imp:.6f}")
            th = tgt_hit_before(prev_vis)
            if th: bad("2. 손절: 목표에 더 먼저 닿은 분 있음", pan, f"{d} 먼저={th[0]} xm={xm}")
        elif why == "목표":
            if T is None: bad("2. 목표: 목표 없는 신호인데 목표 사유", pan, d); continue
            o = xb[2]
            exp = max(o, T) if dr > 0 else min(o, T)
            if xm == me: exp = T if touched_tgt(xb, dr, T) else exp
            if abs(exp - X) > TOL: bad("2. 목표: 정리가 ≠ 목표(또는 시가 갭)", pan, f"{d} X={X:.5f} 기대={exp:.5f} 목표={T:.5f}")
            if not touched_tgt(xb, dr, T): bad("2. 목표: 정리 분에 목표 닿지 않음", pan, f"{d} xm={xm}")
            th = tgt_hit_before(prev_vis)
            if th: bad("2. 목표: 목표에 더 먼저 닿은 분 있음", pan, f"{d} 먼저={th[0]} xm={xm}")
            # 진입~정리 분까지 손절 안 닿는 폭이 [0.5, 규칙 폭] 안에 있어야 함(같은 분이면 손절 먼저)
            ms = prev_vis + [xm]
            ext = min(bar(d, m)[4] for m in ms) if dr > 0 else max(bar(d, m)[3] for m in ms)
            need = dr * (E - ext)  # 이보다 넓은 폭이어야 안 닿음
            if not (need < wr - 1e-12): bad("2. 목표: 규칙 손절 폭으로도 손절이 먼저 닿음", pan, f"{d} 필요 폭>{need:.4f} 규칙={wr:.4f}")
            elif need >= 0.5: info["목표: 손절 폭 하한이 0.5 넘음(폭 제약 생김)"] += 1
        elif why in ("정리", "P2 우선"):
            o = xb[2]
            if abs(X - o) > TOL: bad(f"2. {why}: 정리가 ≠ 그 분 시가", pan, f"{d} xm={xm} X={X:.5f} 시가={o}")
            if why == "정리" and exit_lim is not None and xm != exit_lim:
                bad("2. 정리: 정리 분 ≠ min(정리 분,915) 이상 첫 1분봉", pan, f"{d} xm={xm} 기대={exit_lim}")
            th = tgt_hit_before(prev_vis)
            if th: bad(f"2. {why}: 목표에 더 먼저 닿은 분 있음", pan, f"{d} 먼저={th[0]} xm={xm}")
            sh = [m for m in prev_vis if touched_stop(bar(d, m), dr, Sr)]
            if sh: note(f"참고 · {why}: 규칙 손절 폭 기준 손절이 먼저 닿음", pan, f"{d} 먼저={sh[0]} xm={xm}")
            # 쿠션으로 좁아진 폭이면 닿을 수 있는지(참고): 0.5 폭이 닿는지
            ms = prev_vis
            if ms:
                ext = min(bar(d, m)[4] for m in ms) if dr > 0 else max(bar(d, m)[3] for m in ms)
                need = dr * (E - ext)
                info[f"{why}: 거래 수"] += 1
                if need >= 0.5 - 1e-12: info[f"{why}: 폭이 {need:.2f} 이하이면 손절됐을 거래(쿠션 하한 제약)"] += 0
        elif why == "날 끝":
            if abs(X - K.last_close(d)) > TOL: bad("2. 날 끝: 정리가 ≠ 마지막 종가", pan, d)
        elif why == "빈 구간 손절(스트레스)":
            if not stress: bad("2. 원판에 빈 구간 손절", pan, d)
            if not hole: bad("2. 빈 구간 없는 날 빈 구간 손절", pan, d); continue
            if not me < hole[0]: bad("2. 빈 구간 손절: 진입 분 ≥ 빈 구간 시작", pan, d)
            fa = first_bar_at_or_after(d, hole[1] + 1)
            if xm != fa: bad("2. 빈 구간 손절: 정리 분 ≠ 빈 구간 끝 뒤 첫 분", pan, f"{d} xm={xm} 기대={fa}")
            w_imp = dr * (E - X)
            if w_imp > wr + TOL or w_imp < 0.5 - TOL: bad("2. 빈 구간 손절: 폭 범위 밖", pan, f"{d} {w_imp}")
        else:
            bad("2. 모르는 사유", pan, f"{d} {why}")
    hold_min[pan] = hm

# 3. 날별
for pan in PANS:
    dd = DAILY[pan]; P2 = DAILY["P2 혼자"]
    tp = collections.defaultdict(float)
    for t in LOG[pan]: tp[t[0]] += t[4] - ENTRY_COST
    for d in DAYS:
        b = dd["보완"].get(d, 0.0)
        if abs(b - tp.get(d, 0.0)) > TOL: bad("3. 보완 ≠ 거래 손익 합", pan, f"{d} 보완={b} 거래합={tp.get(d,0.0)}")
        lhs = dd["결합"][d] - P2[d]; rhs = b + dd["P2 바뀐 몫"].get(d, 0.0)
        if abs(lhs - rhs) > EPS: bad("3. 결합−P2 ≠ 보완+P2 바뀐 몫", pan, f"{d} {lhs} vs {rhs}")
    for k in ("결합", "보완", "P2 바뀐 몫"):
        if set(dd[k]) - set(DAYS): bad("3. 평가 날 밖 날 값", pan, k)
    if set(dd["결합"]) != set(DAYS): bad("3. 결합 날 집합 ≠ 평가 날", pan, f"{len(dd['결합'])}")

# 4. 요약 다시 셈
def mdd(v):
    c = 0.0; pk = 0.0; m = 0.0
    for x in v:
        c += x; pk = max(pk, c); m = min(m, c - pk)
    return m
def boot(v, B=2000, L=5):
    rng = random.Random(0); n = len(v); out = []
    for _ in range(B):
        s = []
        while len(s) < n:
            i = rng.randrange(0, n - L + 1); s += v[i:i + L]
        out.append(sum(s[:n]))
    out.sort(); return [out[int(0.025 * B)], out[int(0.975 * B) - 1]]
P2v = [DAILY["P2 혼자"][d] for d in DAYS]
mine = {}
for pan in PANS:
    dd = DAILY[pan]
    J = [dd["결합"][d] for d in DAYS]; inc = [j - p for j, p in zip(J, P2v)]; n = len(inc); h = n // 2
    big = max(range(n), key=lambda i: inc[i])
    ent = len({t[0] for t in LOG[pan]})
    reasons = collections.Counter(t[3] for t in LOG[pan])
    m = {"결합 합": sum(J), "결합 MDD": mdd(J), "결합 최악": min(J), "P2 합": sum(P2v), "P2 MDD": mdd(P2v), "P2 최악": min(P2v),
         "증분 합": sum(inc), "증분 앞 반": sum(inc[:h]), "증분 뒤 반": sum(inc[h:]), "증분 한 날 뺀": sum(inc) - inc[big],
         "가장 큰 증분 날": [DAYS[big], inc[big]], "증분 95%": boot(inc), "보완 단독 합": sum(dd["보완"].get(d, 0) for d in DAYS),
         "P2 바뀐 몫 합": sum(dd["P2 바뀐 몫"].get(d, 0) for d in DAYS), "P2 바뀐 날": sum(1 for d in DAYS if abs(dd["P2 바뀐 몫"].get(d, 0)) > 1e-12),
         "보완 진입 날": ent, "보완 거래 수": len(LOG[pan]), "정리 사유": dict(reasons), "보완 보유 분": hold_min[pan],
         "−15 나쁜 날": {d: x for d, x in zip(DAYS, J) if x < -15}, "날 수": n}
    mine[pan] = m
COND = ["① 증분 > 0", "② 앞 · 뒤 반 > 0", "③ 한 날 빼도 > 0", "④ MDD 안 깊어짐", "⑤ −15 나쁜 날 0", "⑥ 95% 하한 > 0", "⑦ 이웃 부호 같음", "⑧ 진입 날 ≥ 10"]
verdict_mine = {}
for key in SUM:
    if key.startswith("_"): continue
    rule, f = key.split()
    other = f"{rule} {'f0.5' if f == 'f0.25' else 'f0.25'}"
    allc = True; wait = False
    for var in ("원판", "스트레스판"):
        m = mine[f"{key} {var}"]; mo = mine[f"{other} {var}"]
        c = {COND[0]: m["증분 합"] > 0, COND[1]: m["증분 앞 반"] > 0 and m["증분 뒤 반"] > 0, COND[2]: m["증분 한 날 뺀"] > 0,
             COND[3]: m["결합 MDD"] >= m["P2 MDD"], COND[4]: len(m["−15 나쁜 날"]) == 0, COND[5]: m["증분 95%"][0] > 0,
             COND[6]: (m["증분 합"] > 0) == (mo["증분 합"] > 0), COND[7]: m["보완 진입 날"] >= 10}
        m["조건"] = c
        allc &= all(c.values()); wait |= not c[COND[7]]
        S = SUM[key][var]
        cmp = [("결합 합", S["결합"]["합"]), ("결합 MDD", S["결합"]["MDD"]), ("결합 최악", S["결합"]["최악"]), ("P2 합", S["P2 혼자"]["합"]),
               ("P2 MDD", S["P2 혼자"]["MDD"]), ("P2 최악", S["P2 혼자"]["최악"])]
        cmp += [(k, S[k]) for k in ("증분 합", "증분 앞 반", "증분 뒤 반", "증분 한 날 뺀", "보완 단독 합", "P2 바뀐 몫 합", "P2 바뀐 날", "보완 진입 날", "보완 거래 수", "보완 보유 분", "날 수")]
        for k, v in cmp:
            if abs(m[k] - v) > 1e-6: bad("4. 요약 수치 불일치", f"{key} {var}", f"{k}: 다시 셈={m[k]} 요약={v}")
        if m["가장 큰 증분 날"][0] != S["가장 큰 증분 날"][0] or abs(m["가장 큰 증분 날"][1] - S["가장 큰 증분 날"][1]) > 1e-6:
            bad("4. 요약 수치 불일치", f"{key} {var}", f"가장 큰 증분 날 {m['가장 큰 증분 날']} vs {S['가장 큰 증분 날']}")
        for i in range(2):
            if abs(m["증분 95%"][i] - S["증분 95%"][i]) > 1e-6: bad("4. 95% 구간 불일치", f"{key} {var}", f"{m['증분 95%']} vs {S['증분 95%']}")
        if m["정리 사유"] != S["정리 사유"]: bad("4. 정리 사유 수 불일치", f"{key} {var}", f"{m['정리 사유']} vs {S['정리 사유']}")
        if m["−15 나쁜 날"] != S["−15 나쁜 날"]: bad("4. −15 나쁜 날 불일치", f"{key} {var}", "")
        for cn in COND:
            if c[cn] != S["조건"].get(cn): bad("4. 조건 판정 불일치", f"{key} {var}", f"{cn}: 다시 셈={c[cn]} 요약={S['조건'].get(cn)}")
    vd = "WAITING_DATA" if wait else ("지지" if allc else "지지 안 됨")
    verdict_mine[key] = vd
    if vd != SUM[key]["판정"]: bad("4. 판정 불일치", key, f"다시 셈={vd} 요약={SUM[key]['판정']}")

# 5. 스트레스판 vs 원판
diff5 = {}
for key in SUM:
    if key.startswith("_"): continue
    a = LOG[f"{key} 원판"]; b = LOG[f"{key} 스트레스판"]
    da = {t[0]: t for t in a}; db = {t[0]: t for t in b}
    dif = [d for d in sorted(set(da) | set(db)) if da.get(d) != db.get(d)]
    diff5[key] = dif
    for d in dif:
        if d not in HOLES: bad("5. 빈 구간 없는 날 원판·스트레스 거래 다름", key, d)
    dA = DAILY[f"{key} 원판"]; dB = DAILY[f"{key} 스트레스판"]
    dd = [d for d in DAYS if any(abs(dA[k].get(d, 0) - dB[k].get(d, 0)) > 1e-12 for k in ("결합", "보완", "P2 바뀐 몫"))]
    for d in dd:
        if d not in HOLES: bad("5. 빈 구간 없는 날 원판·스트레스 날별 값 다름", key, d)
    diff5[key + " 날별 다른 날"] = dd
# 빈 구간 날에 보유가 빈 구간과 겹친 거래(스트레스가 영향 줄 수 있었던 거래)
hole_overlap = []
for pan in PANS:
    for (d, me, xm, why, pnl) in LOG[pan]:
        if d in HOLES:
            h0, h1 = HOLES[d]
            hole_overlap.append([pan, d, me, xm, why, pnl, "보유가 빈 구간과 겹침" if (me < h0 and xm >= h0) or (h0 <= me <= h1) else "안 겹침"])

res["판별"] = verdict_mine
res["항목별 불일치 수"] = {k: v for k, v in cnt.items() if v}
res["예시(3개까지)"] = {k: v for k, v in ex.items()}
res["참고(판단 불가 · 불일치로 안 셈)"] = {k: {"수": ref[k], "예시": refex[k]} for k in ref}
res["정보"] = dict(info)
res["다시 셈 요약"] = {p: {k: v for k, v in m.items()} for p, m in mine.items()}
res["5. 원판·스트레스 다른 날"] = diff5
res["5. 빈 구간 날 거래"] = hole_overlap
res["검사 항목"] = ["1 진입분 신호표·하루1개·신호분 이후", "2 정리가 거꾸로 셈·사유별 가격·앞선 닿음", "3 날별 보완·항등식", "4 요약·조건·판정 다시 셈", "5 원판·스트레스 차이"]
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: res[k] for k in ("판별", "항목별 불일치 수", "예시(3개까지)", "참고(판단 불가 · 불일치로 안 셈)", "정보", "5. 원판·스트레스 다른 날", "5. 빈 구간 날 거래")}, ensure_ascii=False, indent=1, default=str))
