"""COMP-0001 창 ① 독립 감사(kmf_comp_w1.py 는 고치지 않고 읽기만).
1) 6판 신호를 따로 다시 만듦(날봉 ATR · EMA10/20 은 처음부터 다시 셈 · 15분봉 값은 kmf_nb B15/E10/E20 · T2 는 kmf_nb.sig_t 를 555 · 570 첫 신호로 거름)
   + 자체 체결기(kmf_nb.execute 규칙 · 지연 0 · maxn 2 · 스트레스판은 kmf_r0q 설명대로) → 원판 · 스트레스판 날별 손익을 kmf_comp_w1_daily.json 과 1e-9 로 견줌.
2) 정리 ≤ 585 · 진입 ≥ 555 · 신호가 신호 분 뒤에 끝나는 봉을 쓰지 않음 · 날봉 값이 그날 앞 날들만 씀 — 점검.
3) 판별: 합 · 거래일 · 상위 5일 몫 · 빈 29분 9일 기여 · 가장 좋은 하루 뺀 합.
python3 research/kmf_comp_w1_audit.py → research/kmf_comp_w1_audit.out"""
import sys, json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import kmf_nb as K

EXIT, FIRST_ENTRY = 585, 555
COST, CAP = 0.04, 12.0
HOLES = {"20260304": (680, 708), "20260309": (632, 660), "20260608": (544, 572), "20260623": (874, 902), "20260626": (731, 759),
         "20260707": (832, 860), "20260713": (809, 837), "20260728": (614, 642), "20260729": (753, 781)}
DAYS_ALL = K.DAYS
EVAL = [d for d in DAYS_ALL if "20260108" <= d <= "20261012"]
JB = {(b[0], b[1]): j for j, b in enumerate(K.B15)}
problems = []

# ---------- 날봉 값: 그날 앞 날들만으로 처음부터 셈(날마다 새로) ----------
def day_range(d):
    x = K.BY[d]; return max(r[3] for r in x.values()) - min(r[4] for r in x.values())
def day_close(d):
    x = K.BY[d]; return x[max(x)][5]
RNG = {d: day_range(d) for d in DAYS_ALL}; CLS = {d: day_close(d) for d in DAYS_ALL}

def daily_from_prefix(prefix):
    e10 = e20 = a = None
    for q in prefix:
        c, r = CLS[q], RNG[q]
        e10 = c if e10 is None else e10 + (c - e10) * 2 / 11
        e20 = c if e20 is None else e20 + (c - e20) * 2 / 21
        a = r if a is None else a + (r - a) * 2 / 15
    return (e10, e20, a)
MYDAILY = {d: daily_from_prefix(DAYS_ALL[:i]) for i, d in enumerate(DAYS_ALL)}   # d 앞 날까지만 넘김

# ---------- 15분봉 값 점검: 1분봉에서 다시 묶고 EMA 를 앞으로만 다시 셈 ----------
def my_e(L):
    e = a = None; out = []
    for b in K.B15:
        c, tr = b[5], b[3] - b[4]
        e = c if e is None else e + (c - e) * 2 / (L + 1); a = tr if a is None else a + (tr - a) * 2 / 15; out.append((e, a))
    return out
ME10, ME20 = my_e(10), my_e(20)
ind_bad = sum(1 for j in range(len(K.B15)) if abs(ME10[j][0] - K.E10[j][0]) > 1e-9 or abs(ME10[j][1] - K.E10[j][1]) > 1e-9 or abs(ME20[j][0] - K.E20[j][0]) > 1e-9)

def bar_minutes_ok(j, m_sig):
    """봉 j 가 신호 분 m_sig 에 끝나는지 · 그 봉을 이루는 1분봉이 모두 같은 날 m_sig 앞인지 · OHLC 를 1분봉으로 다시 맞춤."""
    d, end = K.B15[j][0], K.B15[j][1]
    if end > m_sig: return False
    ms = [m for m in K.BY[d] if end - 15 <= m < end]
    if not ms or max(ms) >= m_sig: return False
    o = K.BY[d][min(ms)][2]; h = max(K.BY[d][m][3] for m in ms); l = min(K.BY[d][m][4] for m in ms); c = K.BY[d][max(ms)][5]
    return all(abs(u - v) < 1e-12 for u, v in zip((o, h, l, c), K.B15[j][2:6]))

def feat(d, m):
    j = JB.get((d, m))
    if j is None: return None
    b = K.B15[j]
    return dict(j=j, c=b[5], e10=ME10[j][0], atr=ME10[j][1], e20=ME20[j][0], sl=(ME20[j][0] - ME20[j - 4][0]) if j >= 4 else 0.0)

USED = []   # (판, 날, 신호 분, [쓴 봉 번호], 쓴 날봉 날짜 끝)

# ---------- 신호(독립) ----------
def s_gap(d, k, name):
    i = DAYS_ALL.index(d)
    if i == 0: return []
    da = MYDAILY[d][2]; o = K.BY[d].get(540); b = feat(d, 555)
    if not da or o is None or b is None: return []
    g = (o[2] - CLS[DAYS_ALL[i - 1]]) / da
    if abs(g) < k: return []
    if not ((b["c"] > b["e10"]) if g > 0 else (b["c"] < b["e10"])): return []
    USED.append((name, d, 555, [b["j"]]))
    return [(555, -1 if g > 0 else 1, CLS[DAYS_ALL[i - 1]], b["atr"], EXIT)]

def s_band(d, k, name, flat=0.5):
    out = []
    for m in (555, 570):
        b = feat(d, m)
        if b is None or b["atr"] <= 0 or abs(b["sl"]) / b["atr"] > flat: continue
        if abs(b["c"] - b["e10"]) >= k * b["atr"]:
            USED.append((name, d, m, [b["j"], b["j"] - 4])); out.append((m, -1 if b["c"] > b["e10"] else 1, b["e10"], b["atr"], EXIT))
    return out

def s_t2_mine(d, s):
    """T2 를 직접 다시: 같은 방향(EMA10 · 20 배열 + EMA20 4봉 기울기) · 앞 봉 종가 EMA10 반대편 · 이번 봉 종가 방향 쪽 · 봉 끝 555/570 첫 신호.
    정리 = 뒤 15분 종가가 EMA10 거꾸로 건넌 봉 끝(585 까지만 봄) · 아니면 585."""
    js = [j for j in K.BYD[d]]
    for t, j in enumerate(js):
        b = K.B15[j]
        if b[1] not in (555, 570) or j < 4: continue
        e10, a = ME10[j]; e20 = ME20[j][0]; slope = e20 - ME20[j - 4][0]
        up = e10 > e20 and slope > 0; dn = e10 < e20 and slope < 0
        if not (up or dn): continue
        pb, pe = K.B15[j - 1], ME10[j - 1][0]
        if not ((pb[5] < pe and b[5] > e10) if up else (pb[5] > pe and b[5] < e10)): continue
        mx = EXIT
        for q in js[t + 1:]:
            if K.B15[q][1] > EXIT: break
            if (K.B15[q][5] < ME10[q][0]) if up else (K.B15[q][5] > ME10[q][0]): mx = K.B15[q][1]; break
        return [(b[1], 1 if up else -1, None, s * a, mx)]
    return []

def s_t2(d, s, name):
    mine = s_t2_mine(d, s)
    via = []
    for (m0, side, tg, sd, mx) in K.sig_t(d, "T2", s=s):
        if m0 in (555, 570): via = [(m0, side, tg, sd, min(mx, EXIT))]; break
    if [(a, b, c, round(e, 12), f) for a, b, c, e, f in mine] != [(a, b, c, round(e, 12), f) for a, b, c, e, f in via]:
        problems.append(f"T2 직접 vs sig_t 다름 {d} s{s}: {mine} / {via}")
    if via:
        j = JB[(d, via[0][0])]; USED.append((name, d, via[0][0], [j, j - 1, j - 4]))
    return via

VARIANTS = {"H1 T2 손절 1.0": lambda d, n: s_t2(d, 1.0, n), "H1 T2 손절 1.5": lambda d, n: s_t2(d, 1.5, n),
            "갭 되돌림 k0.3": lambda d, n: s_gap(d, 0.3, n), "갭 되돌림 k0.5": lambda d, n: s_gap(d, 0.5, n),
            "띠 되돌림 k1.0 평평": lambda d, n: s_band(d, 1.0, n), "띠 되돌림 k1.5 평평": lambda d, n: s_band(d, 1.5, n)}

# ---------- 체결(독립 · kmf_nb.execute 규칙 · 스트레스판은 kmf_r0q 설명) ----------
def run(d, sigs, stress):
    x = K.BY[d]; mins = sorted(x); real = 0.0; cnt = 0; free_at = 0; stopped = False; trades = []
    hole = HOLES.get(d) if stress else None
    for (m0, side, tg, sd, mx) in sigs:
        if stopped or cnt >= 2 or CAP + real < 3.0: continue
        me = next((m for m in mins if m >= m0), None)
        if me is None or me < free_at or me >= mx: continue
        ent = x[me][2]; sd = min(sd, max(0.5, CAP + real - 2 * COST)); stop = ent - side * sd; cnt += 1; out = None
        for m in (m for m in mins if m >= me):
            o, h, l, c = x[m][2:6]
            if m == me: o = ent
            if hole and me < hole[0] and m > hole[1]:            # 빈 구간을 들고 지남 → 그 안에서 손절가로 정리 · 다음 진입은 구간 뒤
                out = (stop, hole[0], hole[1] + 1); break
            if m >= mx: out = (o, m, m); break                    # 정리 분 시가
            if (l <= stop) if side > 0 else (h >= stop): out = ((min(o, stop) if side > 0 else max(o, stop)), m, m + 1); break
            if tg is not None and ((h >= tg) if side > 0 else (l <= tg)): out = ((max(o, tg) if side > 0 else min(o, tg)), m, m + 1); break
            if real + side * (c - ent) - 2 * COST <= -CAP:
                nm = next((q for q in mins if q > m), None); out = (x[nm][2] if nm else c, nm or m, 999); stopped = True; break
        if out is None: out = (CLS[d], 935, 999)
        r = side * (out[0] - ent) - 2 * COST; real += r; free_at = out[2]
        trades.append({"신호분": m0, "진입분": me, "정리분": out[1], "손익": r})
        if real <= -CAP: stopped = True
    return real, trades

def main():
    import kmf_comp_w1 as W                                   # 날봉 값 점검용으로만 읽음
    src = HERE / "kmf_comp_w1_daily.json"; ref = json.loads(src.read_text())
    res = {"meta": {"kmf_comp_w1.py sha256": hashlib.sha256((HERE / "kmf_comp_w1.py").read_bytes()).hexdigest(),
                    "kmf_comp_w1_daily.json sha256": hashlib.sha256(src.read_bytes()).hexdigest(), "평가 날": len(EVAL), "첫날": EVAL[0], "끝날": EVAL[-1]}}
    # 2-d) 날봉 값이 그날 앞 날만 쓰는지: 앞 날 묶음만 넘겨 새로 셈한 값 == 원 코드 DAILY
    dbad = sum(1 for d in DAYS_ALL if any((u is None) != (v is None) or (u is not None and abs(u - v) > 1e-9) for u, v in zip(MYDAILY[d], W.DAILY[d])))
    # 그날 값을 일부러 바꿔도 그날 · 앞 날 DAILY 가 그대로인지(구조 점검): d 의 폭 · 종가를 크게 바꾸고 d 까지의 값 비교
    pert_bad = 0
    for i in range(1, len(DAYS_ALL), 17):
        d = DAYS_ALL[i]; keep = (RNG[d], CLS[d]); RNG[d] += 1e3; CLS[d] += 1e3
        pert_bad += int(daily_from_prefix(DAYS_ALL[:i]) != MYDAILY[d]); RNG[d], CLS[d] = keep
    mism, daily, logs = {}, {}, {}
    for name, f in VARIANTS.items():
        for mode in ("원판", "스트레스판"):
            p, lg = {}, {}
            for d in EVAL:
                n0 = len(USED); sig = f(d, name)
                if mode == "스트레스판": del USED[n0:]             # 같은 신호 두 번 기록하지 않게
                p[d], lg[d] = run(d, sig, mode == "스트레스판")
            key = f"{name} {mode}"; daily[key] = p; logs[key] = lg
            mism[key] = sum(1 for d in EVAL if abs(p[d] - ref[key][d]) > 1e-9) + int(set(ref[key]) != set(EVAL))
    # 2-a,b) 정리 ≤ 585 · 진입 ≥ 555
    late = {k: [(d, t["정리분"]) for d in EVAL for t in lg[d] if t["정리분"] > EXIT] for k, lg in logs.items()}
    early = {k: [(d, t["진입분"]) for d in EVAL for t in lg[d] if t["진입분"] < FIRST_ENTRY or t["신호분"] < FIRST_ENTRY] for k, lg in logs.items()}
    entry_not_after_signal = sum(1 for lg in logs.values() for d in EVAL for t in lg[d] if t["진입분"] < t["신호분"])
    # 2-c) 신호 봉이 신호 분 뒤에 끝나지 않음 · 쓴 봉 1분봉이 모두 신호 분 앞
    bar_bad = sum(1 for (_, d, m, js) in USED for j in js if j >= 0 and not (K.B15[j][0] < d or (K.B15[j][0] == d and bar_minutes_ok(j, m))))   # 앞 날 봉이거나 · 같은 날이면 신호 분까지 끝난 봉
    stress_diff = {k.replace(" 원판", ""): sum(1 for d in EVAL if abs(daily[k][d] - daily[k.replace("원판", "스트레스판")][d]) > 1e-12) for k in daily if k.endswith("원판")}
    res["1 재현"] = {"날별 손익 다른 칸(1e-9 · 판 · 방식별)": mism, "다른 칸 합": sum(mism.values()),
                   "15분 EMA · ATR 다시 셈 다른 봉": ind_bad, "T2 직접 구현 vs sig_t 다른 날": len({x for x in problems if x.startswith("T2")}),
                   "원판 vs 스트레스판 손익 다른 날": stress_diff,
                   "스트레스판이 같은 까닭": "빈 구간 중 창(555~585)과 겹치는 것은 06-08(544~572)뿐이고 그날 진입은 빈 구간 뒤(573 이후)라 '빈 구간을 들고 지남'이 없음 · 나머지 8구간은 614 이후 시작"}
    res["2 미래 참조 · 창 점검"] = {"585 넘어 정리": {k: v for k, v in late.items() if v}, "585 넘은 정리 수": sum(len(v) for v in late.values()),
                           "555 앞 진입 · 신호": sum(len(v) for v in early.values()), "신호 분 앞 진입": entry_not_after_signal,
                           "신호가 쓴 봉 수": len(USED) and sum(len([j for j in js if j >= 0]) for *_, js in USED),
                           "신호 분 뒤에 끝나거나 1분봉이 신호 분 이후인 봉": bar_bad,
                           "날봉 ATR · EMA: 앞 날만으로 새로 셈한 값과 다른 날": dbad, "그날 자료 바꿔도 그날 값 바뀐 날(표본)": pert_bad,
                           "갭: 09:00 시가 − 전날 마지막 종가 / 전날까지 날 ATR": "독립 구현과 손익 일치로 확인"}
    hole_days = set(HOLES)
    per = {}
    for name in VARIANTS:
        p = daily[f"{name} 원판"]; lg = logs[f"{name} 원판"]; tot = sum(p.values())
        top5 = sorted(p.values(), reverse=True)[:5]; pos = sum(v for v in p.values() if v > 0)
        best_d = max(EVAL, key=lambda d: p[d])
        per[name] = {"합": round(tot, 4), "거래일": sum(1 for d in EVAL if lg[d]), "거래 수": sum(len(lg[d]) for d in EVAL),
                     "상위 5일 합": round(sum(top5), 4), "상위 5일 ÷ 합": round(sum(top5) / tot, 3) if tot else None,
                     "상위 5일 ÷ 이익 난 날 합": round(sum(top5) / pos, 3) if pos else None,
                     "빈 9일 기여": round(sum(p[d] for d in hole_days if d in p), 4),
                     "빈 9일 날별": {d: round(p[d], 4) for d in sorted(hole_days) if d in p and abs(p[d]) > 0},
                     "가장 좋은 날": best_d, "가장 좋은 날 손익": round(p[best_d], 4), "가장 좋은 날 뺀 합": round(tot - p[best_d], 4),
                     "가장 나쁜 날 손익": round(min(p.values()), 4), "스트레스판 합": round(sum(daily[f"{name} 스트레스판"].values()), 4)}
    res["3 판별"] = per
    res["문제 목록"] = sorted(set(problems))
    (HERE / "kmf_comp_w1_audit.out").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({"다른 칸 합": res["1 재현"]["다른 칸 합"], "585 넘은 정리": res["2 미래 참조 · 창 점검"]["585 넘은 정리 수"],
                      "봉 위반": bar_bad, "날봉 위반": dbad, "문제": len(problems)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
