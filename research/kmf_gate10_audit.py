"""GATE10-0001 독립 감사(kmf_gate10.py 잠금 e6fe31fd · sha256 e8b8ffc1…9994 · 그 파일과 kmf_r0q.execute2 · kmf_rlk4.rna_dir/TF · kmf_nb.bars/ind/execute/sig_* 는 부르지 않음).
같이 쓰는 것: kmf_nb.BY(1분봉 원자료) · kmf_hdd_base.Z/DAYS(조용함 판단 · 158일 · 이번 감사 범위 밖) · kmf_hdd_base.stat(성적 요약 형식).
1) 10:00 방향: 1분봉에서 15 · 30 · 60분봉을 직접 묶고(끝 분 = 다음 봉 첫 분 · 914분까지) EMA10 · EMA20 · ATR(봉 폭 EMA14)을 직접 셈 → 방향 기록과 비교.
   또 '그날 600분 이후 1분봉을 아예 지운 자료'로 봉 · EMA를 처음부터 다시 만들어도 같은 방향인지(600분 뒤 봉 사용 0 확인).
2) S3 · R0 신호도 직접 셈(kmf_nb.sig_t T2 s1.5 + 기울기/ATR ≤ 0.5 · sig_r0 정의대로) → 체결 엔진 직접 구현(원판 · 스트레스판) → 날별 손익 비교.
3) 조건 ①~⑤ · 막힌 거래 · 새 거래 · 품질 쉼 효과 · 판정 다시 셈 → out.json 비교.  4) G30+60 원판에서 막힌 대조 거래 목록.
python3 research/kmf_gate10_audit.py → research/kmf_gate10_audit.out"""
import sys, json, random, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from kmf_hdd_base import K, R4, Z, DAYS, stat
import kmf_hdd_pre as P

T, COST, CAP = 600, 0.04, 12.0
BY = K.BY; ALLD = sorted(BY)
OUT = json.loads((HERE / "kmf_gate10_out.json").read_text()); DAILY = json.loads((HERE / "kmf_gate10_daily.json").read_text())
rep = {"잠금 파일 sha256": hashlib.sha256((HERE / "kmf_gate10.py").read_bytes()).hexdigest()}
data_sha = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
rep["입력 해시 = 잠금값"] = data_sha == P.DATA_EXPECT

# ---------- 봉 · 지표 직접 ----------
def mkbars(n, days, upto=None):
    """upto=(d, m): 그날 m분 이상 1분봉과 그 뒤 날은 아예 없는 자료로 봄."""
    out = []
    for d in days:
        if upto and d > upto[0]: break
        g = {}
        for m in sorted(BY[d]):
            if m > 914 or (upto and d == upto[0] and m >= upto[1]): continue
            k = (m - 540) // n; o, h, l, c = BY[d][m][2:6]
            if k in g: g[k][1] = max(g[k][1], h); g[k][2] = min(g[k][2], l); g[k][3] = c
            else: g[k] = [o, h, l, c]
        out += [(d, 540 + (k + 1) * n, *g[k]) for k in sorted(g)]
    return out
def ema(vals, L):
    e = None; res = []
    for v in vals: e = v if e is None else e + (v - e) * 2 / (L + 1); res.append(e)
    return res
def indic(B): return ema([b[5] for b in B], 10), ema([b[5] for b in B], 20), ema([b[3] - b[4] for b in B], 14)
def dir_at(B, e10, e20, i):
    if i < 4: return 0
    sl = e20[i] - e20[i - 4]
    return 1 if (e10[i] > e20[i] and sl > 0) else (-1 if (e10[i] < e20[i] and sl < 0) else 0)

BARS = {n: mkbars(n, ALLD) for n in (15, 30, 60)}; IND = {n: indic(BARS[n]) for n in BARS}
rep["직접 만든 15분봉 = K.B15"] = sum(1 for a, b in zip(BARS[15], K.B15) if a != b) + abs(len(BARS[15]) - len(K.B15))

nq = [d for d in DAYS if not Z[d]]
def mcomplete(d): return all(m in BY[d] for m in range(540, 600))
def last_closed(n, d):
    B = BARS[n]; idx = [i for i, b in enumerate(B) if (b[0], b[1]) <= (d, T)]; return idx[-1]
viol, prevday, mm, trunc_mm, DIR = [], [], [], [], {}
for d in nq:
    r = {}
    for n in (15, 30, 60):
        B = BARS[n]; i = last_closed(n, d); e10, e20, _ = IND[n]; r[str(n)] = dir_at(B, e10, e20, i)
        if B[i][0] == d and B[i][1] > T: viol.append((d, n))
        if i + 1 < len(B) and B[i + 1][0] == d and B[i + 1][1] <= T: viol.append((d, n, "닫힌 봉 놓침"))
        if B[i][0] != d: prevday.append((d, n))
        Bt = mkbars(n, ALLD, upto=(d, T)); t10, t20, _ = indic(Bt)       # 600분 뒤 자료를 처음부터 안 읽은 셈
        if dir_at(Bt, t10, t20, len(Bt) - 1) != r[str(n)] or Bt[-1][:2] != B[i][:2]: trunc_mm.append((d, n))
    a, b, c = r["30"], r["60"], r["15"]; ok = mcomplete(d)
    r["G30+60"] = a if (ok and a != 0 and a == b) else 0
    r["G15+30+60"] = a if (ok and a != 0 and a == b == c) else 0
    DIR[d] = r
    rec = OUT["10:00 방향 기록"].get(d)
    for k in ("15", "30", "60", "G30+60", "G15+30+60"):
        if rec is None or rec[k] != r[k]: mm.append((d, k, r[k], None if rec is None else rec[k]))
rep["1. 방향"] = {"비교 칸": len(nq) * 5, "기록과 다른 칸": len(mm), "다른 칸 목록": mm, "기록에만 있는 날": sorted(set(OUT["10:00 방향 기록"]) - set(nq)),
                 "같은 날 끝 분 > 600 봉 사용": len(viol), "그날 600분 뒤 자료 지운 셈과 다른 칸": len(trunc_mm), "앞 날 봉을 쓴 날(오전 봉 없음)": prevday,
                 "오전 미완결 안 조용한 날": [d for d in nq if not mcomplete(d)], "out 기록 오전 미완결": OUT["meta"]["오전 미완결 안 조용한 날"]}

# ---------- 신호 직접 ----------
B15 = BARS[15]; E10, E20, ATR = IND[15]; J = {}
for j, b in enumerate(B15): J.setdefault(b[0], []).append(j)
def s3(d):
    js = J[d]; out = []
    for t, j in enumerate(js):
        b = B15[j]
        if b[1] > 900 or j < 4: continue
        sl = E20[j] - E20[j - 4]; up = E10[j] > E20[j] and sl > 0; dn = E10[j] < E20[j] and sl < 0
        if not (up or dn): continue
        pc, pe = B15[j - 1][5], E10[j - 1]
        if not ((pc < pe and b[5] > E10[j]) if up else (pc > pe and b[5] < E10[j])): continue
        if not (ATR[j] and abs(sl) / ATR[j] <= 0.5): continue
        mx = 915
        for q in js[t + 1:]:
            if B15[q][1] > 915: break
            if (B15[q][5] < E10[q]) if up else (B15[q][5] > E10[q]): mx = B15[q][1]; break
        out.append((b[1], 1 if up else -1, None, 1.5 * ATR[j], mx))
    return out
def r0(d):
    return [(B15[j][1], -1 if B15[j][5] > E10[j] else 1, E10[j], ATR[j], 915) for j in J[d]
            if B15[j][1] <= 900 and ATR[j] > 0 and abs(B15[j][5] - E10[j]) >= ATR[j]]
rep["신호 직접 = 기존 함수(참고)"] = {"S3 다른 날": sum(1 for d in DAYS if [tuple(round(v, 9) if isinstance(v, float) else v for v in x) for x in s3(d)] != [tuple(round(v, 9) if isinstance(v, float) else v for v in x) for x in R4.s3(d)]),
                                "R0 다른 날": sum(1 for d in DAYS if [tuple(round(v, 9) for v in x) for x in r0(d)] != [tuple(round(v, 9) for v in x) for x in K.sig_r0(d)])}

# ---------- 빈 구간 직접(하루 안 20분 이상 연속 빈 분) ----------
HOLES = {}
for d in DAYS:
    x = BY[d]; s = None
    for m in range(540, 935):
        if m not in x: s = m if s is None else s
        elif s is not None:
            if m - s >= 20: HOLES[d] = (s, m - 1)
            s = None

# ---------- 체결 엔진 직접 ----------
def run(d, sigs, stress):
    x = BY[d]; mins = sorted(x); real = 0.0; n = 0; free = 0; dead = False; log = []; hole = HOLES.get(d) if stress else None
    for (m0, side, tg, sd, mx) in sigs:
        if dead or n >= 2 or CAP + real < 3.0: continue
        me = next((m for m in mins if m >= m0), None)
        if me is None or me < free or me >= mx: continue
        ent = x[me][2]; sd = min(sd, max(0.5, CAP + real - 2 * COST)); stop = ent - side * sd; n += 1; res = None
        for m in (q for q in mins if q >= me):
            o, h, l, c = x[m][2:6]
            if m == me: o = ent
            if hole and me < hole[0] and m > hole[1]: res = (stop, hole[0], hole[1] + 1, "스트레스 손절"); break
            if m >= mx: res = (o, m, m, "정리분"); break
            if (l <= stop) if side > 0 else (h >= stop): res = ((min(o, stop) if side > 0 else max(o, stop)), m, m + 1, "손절"); break
            if tg is not None and ((h >= tg) if side > 0 else (l <= tg)): res = ((max(o, tg) if side > 0 else min(o, tg)), m, m + 1, "목표"); break
            if real + side * (c - ent) - 2 * COST <= -CAP:
                nx = next((q for q in mins if q > m), None); res = (x[nx][2] if nx else c, nx or m, 999, "하루멈춤"); dead = True; break
        if res is None: res = (x[mins[-1]][5], 935, 999, "끝")
        pnl = side * (res[0] - ent) - 2 * COST; real += pnl; free = res[2]
        log.append({"날": d, "신호분": m0, "진입분": me, "방향": side, "정리분": res[1], "사유": res[3], "손익": round(pnl, 4)})
        if real <= -CAP: dead = True
    return real, log

KINDS = ("무게이트 대조", "대조", "G30+60", "G15+30+60")
def sigs(d, kind):
    if Z[d]: return r0(d)
    s = [x for x in s3(d) if x[0] >= T]
    if kind == "무게이트 대조": return s
    if kind == "대조": return s if mcomplete(d) else []
    g = DIR[d][kind]; return [x for x in s if g != 0 and x[1] == g]
PN, LG = {}, {}
for kind in KINDS:
    for mode in ("원판", "스트레스판"):
        p, lg = {}, {}
        for d in DAYS: p[d], lg[d] = run(d, sigs(d, kind), mode == "스트레스판")
        PN[(kind, mode)], LG[(kind, mode)] = p, lg
dmm = {f"{k} {m}": [(d, round(PN[(k, m)][d], 4), DAILY[f"{k} {m}"][d]) for d in DAYS if abs(round(PN[(k, m)][d], 4) - DAILY[f"{k} {m}"][d]) > 1e-9] for k in KINDS for m in ("원판", "스트레스판")}
rep["2. 날별 손익"] = {"비교 칸": len(KINDS) * 2 * len(DAYS), "다른 칸": sum(len(v) for v in dmm.values()), "다른 칸 목록": {k: v for k, v in dmm.items() if v},
                      "직접 찾은 빈 구간(20분 이상)": HOLES, "kmf_r0q.HOLES와 같음": None}
import kmf_r0q as Q
rep["2. 날별 손익"]["kmf_r0q.HOLES와 같음"] = {d: tuple(v) for d, v in Q.HOLES.items()} == HOLES
rep["2. 날별 손익"]["스트레스로 바뀐 날(판별)"] = {k: [d for d in DAYS if abs(PN[(k, '원판')][d] - PN[(k, '스트레스판')][d]) > 1e-12] for k in KINDS}

# ---------- 조건 · 판정 ----------
def boot(v, B=2000, L=5, seed=0):
    rng = random.Random(seed); n = len(v); r = []
    for _ in range(B):
        s = []
        while len(s) < n: i = rng.randrange(0, n - L + 1); s += v[i:i + L]
        r.append(sum(s[:n]))
    r.sort(); return [r[int(0.025 * B)], r[int(0.975 * B) - 1]]
cmp_mm = []; mine = {}
def chk(path, a, b, tol=1e-6):
    same = (a == b) if not isinstance(a, float) and not isinstance(b, float) else abs(a - b) <= tol
    if not same: cmp_mm.append((path, a, b))
for kind in ("G30+60", "G15+30+60"):
    o = OUT["판"][kind]; act = [d for d in nq if DIR[d][kind] != 0]; ok_all = True; mk = {"작동한 안 조용한 날": len(act)}
    chk(f"{kind} 작동한 날", len(act), o["작동한 안 조용한 날"]); chk(f"{kind} +1 날", sum(DIR[d][kind] > 0 for d in act), o["+1 날"]); chk(f"{kind} −1 날", sum(DIR[d][kind] < 0 for d in act), o["−1 날"])
    for mode in ("원판", "스트레스판"):
        p, b = PN[(kind, mode)], PN[("대조", mode)]; lg, lb = LG[(kind, mode)], LG[("대조", mode)]; oo = o[mode]
        ex = [p[d] - b[d] for d in DAYS]; best = max(ex)
        blk = [t for d in DAYS for t in lb[d] if t["신호분"] not in {u["신호분"] for u in lg[d]}]
        new = [t for d in DAYS for t in lg[d] if t["신호분"] not in {u["신호분"] for u in lb[d]}]
        ci = boot(ex); worse = {d: p[d] for d in DAYS if p[d] < -15.0}
        cond = {"① 초과 합 > 0": sum(ex) > 0, "② 막힌 거래 손익 < 0": sum(t["손익"] for t in blk) < 0, "③ 95% 하한 > 0": ci[0] > 0, "④ 한 날 빼도 > 0": sum(ex) - best > 0, "⑤ −15p보다 나쁜 날 0": not worse}
        ok_all = ok_all and all(cond.values())
        s, sb = stat(p), stat(b)
        m = {"초과 합": sum(ex), "95%": ci, "한 날 뺀": sum(ex) - best, "막힌 수": len(blk), "막힌 합": sum(t["손익"] for t in blk), "새 거래": len(new), "조건": cond,
             "S3 거래 수(게이트 · 대조)": [sum(len(lg[d]) for d in nq), sum(len(lb[d]) for d in nq)], "합": s["합"], "MDD": s["MDD"], "대조 합": sb["합"], "대조 MDD": sb["MDD"],
             "안 조용한 날만 합": round(sum(p[d] for d in nq), 2), "−15p보다 나쁜 날": worse}
        mk[mode] = m
        chk(f"{kind} {mode} 초과 합", m["초과 합"], oo["원정밀도"]["초과 합"]); chk(f"{kind} {mode} 95% 하", ci[0], oo["원정밀도"]["초과 합 95%"][0]); chk(f"{kind} {mode} 95% 상", ci[1], oo["원정밀도"]["초과 합 95%"][1])
        chk(f"{kind} {mode} 한 날 뺀", m["한 날 뺀"], oo["원정밀도"]["가장 큰 한 날 뺀 초과"]); chk(f"{kind} {mode} 막힌 합", m["막힌 합"], oo["원정밀도"]["막힌 대조 거래 손익 합"], 1e-3)
        chk(f"{kind} {mode} 막힌 수", len(blk), oo["막힌 대조 거래 수"]); chk(f"{kind} {mode} 새 거래", len(new), oo["새로 생긴 거래 수"]); chk(f"{kind} {mode} 조건", cond, oo["조건"])
        chk(f"{kind} {mode} S3 거래 수", m["S3 거래 수(게이트 · 대조)"], oo["실제 S3 거래 수(게이트 · 대조)"]); chk(f"{kind} {mode} −15 날", {d: round(v, 6) for d, v in worse.items()}, {d: round(v, 6) for d, v in oo["−15p보다 나쁜 날"].items()})
        for a, bb in (("합", "H 수준 합(R0 + 게이트 S3)"), ("MDD", "MDD"), ("대조 합", "대조 합"), ("대조 MDD", "대조 MDD"), ("안 조용한 날만 합", "안 조용한 날만 합")): chk(f"{kind} {mode} {a}", m[a], oo[bb])
    v = "WAITING_DATA" if len(act) < 20 else ("지지" if ok_all else "지지 안 됨"); mk["판정"] = v; chk(f"{kind} 판정", v, o["판정"]); mine[kind] = mk
for mode in ("원판", "스트레스판"):
    a, b = PN[("무게이트 대조", mode)], PN[("대조", mode)]; key = f"품질 쉼 효과({mode} · 품질 일치 대조 − 무게이트 대조)"
    q = {"합": round(sum(b[d] - a[d] for d in DAYS), 4), "날짜별": {d: round(b[d] - a[d], 4) for d in nq if not mcomplete(d)}}
    mine[key] = q; chk(key, q, OUT[key])
rep["3. 조건 · 판정"] = {"비교 항목 다른 것": len(cmp_mm), "다른 것 목록": cmp_mm, "다시 셈": mine}

# ---------- 막힌 거래 목록(G30+60 원판) ----------
lg, lb = LG[("G30+60", "원판")], LG[("대조", "원판")]
blk = [dict(t, **{"그날 고정 방향": DIR[t["날"]]["G30+60"], "15/30/60": [DIR[t["날"]][k] for k in ("15", "30", "60")]}) for d in DAYS for t in lb[d] if t["신호분"] not in {u["신호분"] for u in lg[d]}]
new = [t for d in DAYS for t in lg[d] if t["신호분"] not in {u["신호분"] for u in lb[d]}]
rep["4. G30+60 원판 막힌 대조 거래"] = {"수": len(blk), "손익 합": round(sum(t["손익"] for t in blk), 4),
    "고정 방향 0(그날 쉼)인 날 거래": [len([t for t in blk if t["그날 고정 방향"] == 0]), round(sum(t["손익"] for t in blk if t["그날 고정 방향"] == 0), 4)],
    "고정 방향과 반대 거래": [len([t for t in blk if t["그날 고정 방향"] != 0]), round(sum(t["손익"] for t in blk if t["그날 고정 방향"] != 0), 4)],
    "목록": blk, "새로 생긴 거래(앞 거래가 막혀 뒤 신호가 들어감)": new}

(HERE / "kmf_gate10_audit.out").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
print(json.dumps({"입력 해시": rep["입력 해시 = 잠금값"], "15분봉 다른": rep["직접 만든 15분봉 = K.B15"], "방향 다른 칸": len(mm), "600 뒤 봉": len(viol), "자른 셈 다른": len(trunc_mm),
                  "손익 다른 칸": rep["2. 날별 손익"]["다른 칸"], "빈 구간 같음": rep["2. 날별 손익"]["kmf_r0q.HOLES와 같음"], "조건 다른": len(cmp_mm), "신호": rep["신호 직접 = 기존 함수(참고)"],
                  "판정": {k: mine[k]["판정"] for k in ("G30+60", "G15+30+60")}}, ensure_ascii=False))
for t in blk: print(t["날"], t["신호분"], t["방향"], t["손익"], t["그날 고정 방향"], t["15/30/60"], t["사유"])
