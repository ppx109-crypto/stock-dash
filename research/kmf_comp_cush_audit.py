"""COMP-0002 독립 감사(kmf_comp_cush.py 잠금 sha256 8778cdea…0ea4 · 그 파일은 고치지 않고 부르지도 않음).
1. 체결을 따로 짠 my_exec로 R0(kmf_nb.sig_r0 기본) · S3(kmf_rlk4.s3)를 원판 · 스트레스판으로 다시 셈 → _daily.json과 날별 비교(1e-9) · 조건 · 판정 비교.
   R0 신호는 1분봉에서 15분봉 · EMA10 · ATR을 따로 다시 만들어 kmf_nb.sig_r0와도 견줌.
2. 깔때기(평가 날 → 끝난 분 < 900 · 쿠션 ≥ 1 → 쿠션 ≥ 3 → 끝난 분 뒤 신호 있음 → 실제 진입 → 첫 신호 건너뜀인데 뒤 신호 있었음) · 손절폭이 쿠션으로 잘렸는지.
3. 증분을 표의 '종류'(본 / 그 밖)로 나눔.  4. 진입 분 > 끝난 분 · 정리 분 ≤ 915 · 보완 손실 ≤ 쿠션 확인.
python3 research/kmf_comp_cush_audit.py → research/kmf_comp_cush_audit.out"""
import sys, json, hashlib, random, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import kmf_nb as K, kmf_rlk4 as R4, kmf_r0q as Q

LOCK = "8778cdeacbbc9b25b0fb976cc66f032f4eb602b6d69f85871792f239820e0ea4"
TAB = json.loads((HERE / "kmf_p2_done_table.json").read_text())
OUT = json.loads((HERE / "kmf_comp_cush_out.json").read_text())
DAILY = json.loads((HERE / "kmf_comp_cush_daily.json").read_text())
COST = 0.04
EVAL = [d for d in K.DAYS if "20260108" <= d <= "20261012" and d in TAB]
lines = []
def say(*a): s = " ".join(str(x) for x in a); lines.append(s); print(s)

# ---------- R0 신호 따로 만들기(1분봉 → 15분봉 → EMA10 · ATR(봉 폭 EMA14) · 날 넘어 이어짐) ----------
def my_r0_all():
    e = a = None; res = collections.defaultdict(list)
    for d in K.DAYS:
        x = K.BY[d]; g = {}
        for m in sorted(x):
            if m > 914: continue
            k = (m - 540) // 15; o, h, l, c = x[m][2], x[m][3], x[m][4], x[m][5]
            if k not in g: g[k] = [o, h, l, c]
            else: g[k][1] = max(g[k][1], h); g[k][2] = min(g[k][2], l); g[k][3] = c
        for k in sorted(g):
            end = 540 + (k + 1) * 15; _, h, l, c = g[k]
            e = c if e is None else e + (c - e) * 2 / 11; a = (h - l) if a is None else a + ((h - l) - a) * 2 / 15
            if end <= 900 and a > 0 and abs(c - e) >= a: res[d].append((end, -1 if c > e else 1, e, a, 915))
    return res
MYR0 = my_r0_all()
r0_sig_diff = sum(1 for d in EVAL if len(MYR0[d]) != len(K.sig_r0(d)) or any(
    p[0] != q[0] or p[1] != q[1] or abs(p[2] - q[2]) > 1e-9 or abs(p[3] - q[3]) > 1e-9 for p, q in zip(MYR0[d], K.sig_r0(d))))

# ---------- 따로 짠 체결(신호 1개 · maxn 1 · CAP = 쿠션) ----------
def my_exec(d, sig, cap, stress):
    """반환 (손익, 기록 또는 None, 건너뜀 사유). 기록 = 진입분 · 정리분 · 원 손절폭 · 쓴 손절폭 · 잘림 여부."""
    if cap < 3.0: return 0.0, None, "CAP+실현 < 3"
    m0, side, tg, sd0, mx = sig; x = K.BY[d]; ms = [m for m in sorted(x) if m <= 934]
    me = next((m for m in ms if m >= m0), None)
    if me is None: return 0.0, None, "진입 분 없음"
    if me >= mx: return 0.0, None, "진입 분 ≥ 정리 분"
    ent = x[me][2]; sd = min(sd0, max(0.5, cap - 2 * COST)); stop = ent - side * sd
    hole = Q.HOLES.get(d) if stress else None; ex = None
    for m in ms:
        if m < me: continue
        o = ent if m == me else x[m][2]; h, l, c = x[m][3], x[m][4], x[m][5]
        if hole and m > hole[1] and me < hole[0]: ex = (stop, hole[0], "빈구간"); break
        if m >= mx: ex = (o, m, "정리"); break
        hit = (l <= stop) if side > 0 else (h >= stop)
        if hit: ex = ((min(o, stop) if side > 0 else max(o, stop)), m, "손절"); break
        if tg is not None and ((h >= tg) if side > 0 else (l <= tg)): ex = ((max(o, tg) if side > 0 else min(o, tg)), m, "목표"); break
        if side * (c - ent) - 2 * COST <= -cap:
            nm = next((q for q in ms if q > m), None); ex = ((x[nm][2] if nm else c), (nm or m), "하루멈춤"); break
    if ex is None: ex = (K.last_close(d), 935, "끝")
    r = side * (ex[0] - ent) - 2 * COST
    return r, {"신호분": m0, "진입분": me, "정리분": ex[1], "사유": ex[2], "원 손절폭": sd0, "쓴 손절폭": sd, "잘림": sd < sd0 - 1e-12, "손익": r}, None

def bci(v, B=2000, L=5):
    rng = random.Random(0); n = len(v); out = []
    for _ in range(B):
        s = []
        while len(s) < n: i = rng.randrange(0, n - L + 1); s += v[i:i + L]
        out.append(sum(s[:n]))
    out.sort(); return [out[int(0.025 * B)], out[int(0.975 * B) - 1]]
def mdd(p):
    eq = pk = m = 0.0
    for d in EVAL: eq += p[d]; pk = max(pk, eq); m = min(m, eq - pk)
    return m

say("== COMP-0002 독립 감사 ==")
sha = hashlib.sha256((HERE / "kmf_comp_cush.py").read_bytes()).hexdigest()
say("잠금 해시 일치:", sha == LOCK, "| 표 해시가 out.json과 같음:",
    hashlib.sha256((HERE / "kmf_p2_done_table.json").read_bytes()).hexdigest() == OUT["meta"]["code_sha256"]["kmf_p2_done_table.json"])
say("평가 날:", len(EVAL), EVAL[0], "~", EVAL[-1], "| out.json days:", OUT["meta"]["days"])
say("표: 끝 실현 ≠ 그날 손익인 날", sum(1 for d in EVAL if abs(TAB[d]["끝 실현"] - TAB[d]["그날 손익"]) > 1e-12), "| 끝난 분 비어 있는 날", sum(1 for d in EVAL if TAB[d]["끝난 분"] is None))
say("R0 신호 따로 만든 것과 kmf_nb.sig_r0가 다른 날:", r0_sig_diff)
p2 = {d: TAB[d]["그날 손익"] for d in EVAL}
say("P2 혼자 날별 손익 daily.json과 다른 날:", sum(1 for d in EVAL if abs(p2[d] - DAILY["P2 혼자"][d]) > 1e-9))

cush_days = [d for d in EVAL if TAB[d]["끝난 분"] is not None and TAB[d]["끝난 분"] < 900 and TAB[d]["끝 실현"] >= 1.0]
SIGF = {"R0": lambda d: MYR0[d], "S3": lambda d: R4.s3(d)}
total_mis = 0; verdict_mis = 0; cond_mis = 0
for name, f in SIGF.items():
    say(f"\n## {name}")
    ok_all = True; act0 = None
    for mode in ("원판", "스트레스판"):
        stress = mode == "스트레스판"; c = {d: 0.0 for d in EVAL}; rec = {}; fun = collections.Counter(); skips = collections.Counter()
        for d in EVAL:
            fun["평가 날"] += 1
            if d not in cush_days: continue
            fun["끝난 분<900 · 쿠션≥1"] += 1; dm, cu = TAB[d]["끝난 분"], TAB[d]["끝 실현"]
            sig = [s for s in f(d) if s[0] > dm]
            if cu >= 3.0:
                fun["  그중 쿠션≥3"] += 1
                if sig: fun["    그중 끝난 분 뒤 신호 있음"] += 1
            elif sig: fun["  (쿠션 1~3 · 신호 있었으나 CAP<3으로 못 들어감)"] += 1
            if not sig: continue
            r, lg, why = my_exec(d, sig[0], cu, stress); c[d] = r
            if lg: rec[d] = lg; fun["      그중 실제 진입"] += 1
            elif why != "CAP+실현 < 3":
                skips[why] += 1
                if len(sig) > 1: fun["      첫 신호 건너뜀 · 뒤 신호 있었음"] += 1
        mis = sum(1 for d in EVAL if abs(c[d] - DAILY[f"{name} {mode}"][d]) > 1e-9); total_mis += mis
        say(f"[{mode}] daily.json과 다른 날(1e-9): {mis}")
        for k, v in fun.items(): say(f"  깔때기 {k}: {v}")
        say("  첫 신호 건너뛴 사유:", dict(skips) or "없음")
        # 손절폭 잘림
        for cl in (True, False):
            g = [t for t in rec.values() if t["잘림"] == cl]
            say(f"  손절폭 {'쿠션에 잘림' if cl else '안 잘림'}: 거래 {len(g)} · 이긴 {sum(1 for t in g if t['손익'] > 0)} · 손익 합 {sum(t['손익'] for t in g):.4f}")
        # 종류별 증분
        by = collections.defaultdict(lambda: [0, 0, 0.0])
        for d in EVAL:
            k = "본" if TAB[d]["종류"] == "본" else "그 밖(막힘 · 되돌림 등)"
            if d in cush_days: by[k][0] += 1
            if d in rec: by[k][1] += 1
            by[k][2] += c[d]
        for k, (n, a, s) in sorted(by.items()): say(f"  종류 {k}: 쿠션 날 {n} · 활성 {a} · 증분 합 {s:.4f}")
        # 4번 점검
        bad_entry = [d for d, t in rec.items() if t["진입분"] <= TAB[d]["끝난 분"]]
        bad_exit = [d for d, t in rec.items() if t["정리분"] > 915]
        over = [d for d, t in rec.items() if -t["손익"] > TAB[d]["끝 실현"] + 1e-12]
        say(f"  진입 분 ≤ 끝난 분: {len(bad_entry)} · 정리 분 > 915: {len(bad_exit)} · 손실 > 쿠션: {len(over)}",
            "| 최대 손실/쿠션 비:", round(max([-t["손익"] / TAB[d]["끝 실현"] for d, t in rec.items()] + [0]), 4),
            "| 정리 사유:", dict(collections.Counter(t["사유"] for t in rec.values())))
        # 진입 기록도 out.json과 견줌
        rlog = OUT["판"][name][mode]["보완 진입 기록"]
        logmis = sum(1 for d in set(rlog) | set(rec) if d not in rlog or d not in rec or rlog[d][0]["진입분"] != rec[d]["진입분"]
                     or rlog[d][0]["정리분"] != rec[d]["정리분"] or rlog[d][0]["신호분"] != rec[d]["신호분"])
        say(f"  out.json 진입 기록(신호 · 진입 · 정리 분)과 다른 날: {logmis}")
        # 조건 다시 셈
        inc = [c[d] for d in EVAL]; h = len(EVAL) // 2; best = max(range(len(inc)), key=lambda i: inc[i]); ci = bci(inc)
        comb = {d: p2[d] + c[d] for d in EVAL}
        cond = {"① 증분 > 0": sum(inc) > 0, "② 앞 · 뒤 반 > 0": sum(inc[:h]) > 0 and sum(inc[h:]) > 0, "③ 한 날 빼도 > 0": sum(inc) - inc[best] > 0,
                "④ MDD 안 깊어짐": mdd(comb) >= mdd(p2), "⑤ −15 나쁜 날 0": not any(v < -15.0 for v in comb.values()), "⑥ 95% 하한 > 0": ci[0] > 0, "⑦ 활성 날 ≥ 10": len(rec) >= 10}
        cm = sum(1 for k in cond if cond[k] != OUT["판"][name][mode]["조건"][k]); cond_mis += cm
        say(f"  증분 합 {sum(inc):.4f} · 앞/뒤 반 {sum(inc[:h]):.4f}/{sum(inc[h:]):.4f} · 한 날 뺀 {sum(inc) - inc[best]:.4f} · 95% [{ci[0]:.4f}, {ci[1]:.4f}] · 활성 {len(rec)} · 이긴 {sum(1 for t in rec.values() if t['손익'] > 0)}")
        say(f"  결합 MDD {mdd(comb):.4f} (P2 혼자 {mdd(p2):.4f}) · 결합 최악 {min(comb.values()):.4f}")
        say(f"  조건 {cond} · out.json과 다른 조건 수: {cm}")
        ok_all = ok_all and all(cond.values())
        if mode == "원판": act0 = len(rec)
    v = "WAITING_DATA" if act0 < 10 else ("지지" if ok_all else "지지 안 됨")
    vm = int(v != OUT["판"][name]["판정"]); verdict_mis += vm
    say(f"  판정 다시 셈: {v} · out.json: {OUT['판'][name]['판정']} · 다름 {vm}")

hz = [(d, TAB[d]["끝난 분"], Q.HOLES[d]) for d in cush_days if d in Q.HOLES]
say("\n쿠션 날 중 빈 구간 날(날 · 끝난 분 · 빈 구간):", hz, "| 빈 구간이 끝난 분 뒤에 걸친 날:", sum(1 for _, dm, hh in hz if hh[1] > dm), "→ 0이면 스트레스판은 원판과 같을 수밖에 없음")
say("참고: ④는 P2 혼자 MDD(", round(mdd(p2), 4), ")가 하루 최악(", round(min(p2.values()), 4), ")과 같아 보완 손실 ≤ 쿠션이면 거의 저절로 참 · S3는 kmf_rlk4 원래의 '조용하지 않은 날' 거르기 없이 모든 쿠션 날에 씀(잠금 설계대로)")
say(f"\n== 합계: 날별 손익 다른 칸 {total_mis} · 조건 다른 칸 {cond_mis} · 판정 다른 칸 {verdict_mis} · R0 신호 다른 날 {r0_sig_diff} ==")
(HERE / "kmf_comp_cush_audit.out").write_text("\n".join(lines) + "\n")
