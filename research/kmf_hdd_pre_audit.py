"""HDD-0001 round 2 독립 검산(kmf_hdd_pre.py 잠금판 · sha256 b7c56a23…e5d3).
kmf_hdd_pre의 sig_h · main · nslope · decel · stretch15 · one_day_share는 부르지 않음.
쓰는 것: kmf_nb 엔진(K.execute · K.sig_r0 · K.BY · K.B15 · K.E10) · kmf_rlk4(s3 · rna_dir · TF는 대조용) · kmf_hdd_base(Z · DAYS).
30분 · 60분봉 · EMA · ATR · 기울기 · RNA 방향 · 이격 · 성적(stat) · 승격 판정은 이 파일에서 따로 다시 셈.
검사: 1 날별 손익 · 2 성적 · 판정 · 후보 · 3 미래 참조(봉 끝 ≤ 신호 분 · 자르기 3날) · 4 GB 밴드 1.5 = 2.0 까닭 · 5 GM MDD −35.1 구간 · 6 자료 해시.
python3 research/kmf_hdd_pre_audit.py → research/kmf_hdd_pre_audit.out"""
import sys, os, json, hashlib, subprocess, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import kmf_nb as K, kmf_rlk4 as R4
from kmf_hdd_base import Z, DAYS
OUT = []
def say(*a):
    s = " ".join(str(x) for x in a); OUT.append(s); print(s)

# ---------- 따로 만든 n분봉 · 지표 ----------
def my_bars(n):
    res = []
    for d in K.DAYS:
        grp = collections.OrderedDict()
        for m in sorted(K.BY[d]):
            if m > 914: continue
            r = K.BY[d][m]; k = (m - 540) // n
            if k in grp:
                g = grp[k]; g[1] = max(g[1], r[3]); g[2] = min(g[2], r[4]); g[3] = r[5]
            else: grp[k] = [r[2], r[3], r[4], r[5]]
        for k, g in grp.items(): res.append((d, 540 + n * (k + 1), g[0], g[1], g[2], g[3]))
    return res
def my_ema_atr(B, L):
    out = []; e = a = None
    for b in B:
        e = b[5] if e is None else e + 2.0 / (L + 1) * (b[5] - e)
        a = (b[3] - b[4]) if a is None else a + 2.0 / 15 * ((b[3] - b[4]) - a)
        out.append((e, a))
    return out
MY = {}
for n in (30, 60):
    B = my_bars(n); MY[n] = (B, my_ema_atr(B, 10), my_ema_atr(B, 20))
tf_diff = sum(1 for n in (30, 60) for i in range(max(len(MY[n][0]), len(R4.TF[n][0])))
              if i >= len(MY[n][0]) or i >= len(R4.TF[n][0]) or MY[n][0][i] != R4.TF[n][0][i]
              or abs(MY[n][1][i][0] - R4.TF[n][1][i][0]) > 1e-9 or abs(MY[n][2][i][0] - R4.TF[n][2][i][0]) > 1e-9 or abs(MY[n][2][i][1] - R4.TF[n][2][i][1]) > 1e-9)

USE = []   # 미래 참조 검사용: (n, d, m, 쓴 봉 번호)
def last_closed(n, d, m):
    """끝 분 ≤ m 인 마지막 봉 번호(선형이 아닌 이분 탐색을 따로 씀)."""
    B = MY[n][0]; lo, hi = 0, len(B)
    while lo < hi:
        mid = (lo + hi) // 2
        if (B[mid][0], B[mid][1]) <= (d, m): lo = mid + 1
        else: hi = mid
    return lo - 1
def my_slope(n, d, m, back):
    B, _, E20 = MY[n]; i = last_closed(n, d, m)
    USE.append((n, d, m, i)); i -= back
    if i < 4 or E20[i][1] <= 0: return None
    return abs(E20[i][0] - E20[i - 4][0]) / E20[i][1]
def my_decel(n, d, m):
    a = my_slope(n, d, m, 0); b = my_slope(n, d, m, 1)
    return a is not None and b is not None and a < b
def my_rna(n, d, m):
    B, E10, E20 = MY[n]; i = last_closed(n, d, m); USE.append((n, d, m, i))
    if i < 4: return 0
    sl = E20[i][0] - E20[i - 4][0]
    if E10[i][0] > E20[i][0] and sl > 0: return 1
    if E10[i][0] < E20[i][0] and sl < 0: return -1
    return 0
IDX15 = {(b[0], b[1]): j for j, b in enumerate(K.B15)}
def my_stretch(d, m):
    j = IDX15[(d, m)]; e, a = K.E10[j]
    return abs(K.B15[j][5] - e) / a if a > 0 else 99.0

# ---------- 판별 신호 ----------
FAM = {"GA": [("GA k1.0 tf30", 1.0, "30"), ("GA k1.0 tf30+60", 1.0, "30+60"), ("GA k1.25 tf30", 1.25, "30"), ("GA k1.25 tf30+60", 1.25, "30+60")],
       "GB": [("GB tf15+30 band1.5", "15+30", 1.5), ("GB tf15+30 band2.0", "15+30", 2.0), ("GB tf15+30+60 band1.5", "15+30+60", 1.5), ("GB tf15+30+60 band2.0", "15+30+60", 2.0)],
       "GM": [(f"GM N{n}", n) for n in (3, 4, 5, 6)]}
rna_mismatch = 0
def signals(fam, cfg, d):
    global rna_mismatch
    if Z[d]:
        if fam == "GA":
            out = []
            for s in K.sig_r0(d, k=cfg[1]):
                ok30 = my_decel(30, d, s[0]); ok60 = True if cfg[2] == "30" else my_decel(60, d, s[0])
                if ok30 and ok60: out.append(s)
            return out
        base = K.sig_r0(d)
        if fam == "GM": return [(s[0], s[1], s[2], s[3], min(915, s[0] + 15 * cfg[1])) for s in base]
        return base
    base = R4.s3(d)
    if fam != "GB": return base
    out = []
    for s in base:
        r30 = my_rna(30, d, s[0]); r60 = my_rna(60, d, s[0])
        rna_mismatch += (r30 != R4.rna_dir(30, d, s[0])) + (r60 != R4.rna_dir(60, d, s[0]))
        if r30 == s[1] and (cfg[1] == "15+30" or r60 == s[1]) and my_stretch(d, s[0]) <= cfg[2]: out.append(s)
    return out

DAILY = {"H(대조)": {d: K.execute(d, signals(None, None, d)) for d in DAYS}}
for fam, cfgs in FAM.items():
    for cfg in cfgs: DAILY[cfg[0]] = {d: K.execute(d, signals(fam, cfg, d)) for d in DAYS}

# ---------- 성적(따로 셈) ----------
def my_stat(p):
    v = [p[d] for d in DAYS]; eq = 0.0; peak = 0.0; mdd = 0.0; run = longest = 0; uw = longest_uw = 0; mon = {}
    for d, x in zip(DAYS, v):
        eq += x; mon[d[:6]] = mon.get(d[:6], 0.0) + x
        if eq >= peak: peak = eq; uw = 0
        else: uw += 1; longest_uw = max(longest_uw, uw)
        mdd = min(mdd, eq - peak)
        if x < 0: run += 1; longest = max(longest, run)
        elif x > 0: run = 0
    h = len(v) // 2
    return {"합": round(sum(v), 1), "MDD": round(mdd, 1), "최악": round(min(v), 1), "연속손실": longest, "회복최장": longest_uw,
            "나쁜달": round(min(mon.values()), 1), "앞반": round(sum(v[:h]), 1), "뒤반": round(sum(v[h:]), 1)}
def raw_mdd(p):
    eq = peak = mdd = 0.0
    for d in DAYS: eq += p[d]; peak = max(peak, eq); mdd = min(mdd, eq - peak)
    return mdd
def mdd_episode(p):
    eq = peak = mdd = 0.0; pk_d = None; best = (0.0, None, None)
    for d in DAYS:
        eq += p[d]
        if eq >= peak: peak = eq; pk_d = d
        if eq - peak < best[0]: best = (eq - peak, pk_d, d)
    return best
H = DAILY["H(대조)"]
def share(p):
    base = round(raw_mdd(H), 1); full = round(raw_mdd(p), 1) - base
    if full <= 0: return None
    diff = [d for d in DAYS if p[d] != H[d]]
    if not diff: return 0.0
    return round(max(round(raw_mdd({**H, d: p[d]}), 1) - base for d in diff) / full, 3)

def main():
    pub = json.loads((HERE / "kmf_hdd_pre_out.json").read_text()); pday = json.loads((HERE / "kmf_hdd_pre_daily.json").read_text())
    say("== 0 따로 만든 30 · 60분봉 · EMA · ATR 와 kmf_rlk4.TF 다른 봉 수:", tf_diff)
    # 1
    say("== 1 날별 손익 다시 셈(158일 × 13판)")
    tot = 0
    for k, p in DAILY.items():
        n = sum(1 for d in DAYS if abs(round(p[d], 4) - pday[k][d]) > 1e-9) + (len(pday[k]) != len(DAYS)); tot += n
        say(f"  {k}: 다른 칸 {n} · 합 {round(sum(p.values()), 2)}")
    say("  모두 다른 칸:", tot, "· 판 수", len(DAILY), "· 날 수", len(DAYS), "· RNA 방향(kmf_rlk4.rna_dir 대비) 다른 셈:", rna_mismatch)
    # 2
    say("== 2 성적 · 판정 · 후보 다시 셈")
    res = {}; bad = 0
    for k, p in DAILY.items():
        s = my_stat(p)
        if k != "H(대조)":
            s["−15 넘은 날"] = sum(1 for d in DAYS if p[d] < -15.0); s["한 날 효과"] = share(p)
            s["기본 통과"] = (s["합"] >= 476.0 and s["MDD"] >= -36.1 and s["−15 넘은 날"] == 0 and s["앞반"] > 0 and s["뒤반"] > 0
                          and s["한 날 효과"] is not None and s["한 날 효과"] < 0.5)
        res[k] = s
        for f, v in s.items():
            if pub["rows"][k].get(f) != v: bad += 1; say(f"  다름 {k} {f}: 검산 {v} · 원판 {pub['rows'][k].get(f)}")
    grid_nb = {0: [2, 1], 1: [3, 0], 2: [0, 3], 3: [1, 2]}   # 2×2 격자(행 = tf 또는 k · 열 = 그 안의 두 번째 축)
    passed, strict = [], []
    for fam, cfgs in FAM.items():
        for i, cfg in enumerate(cfgs):
            nb = [j for j in (i - 1, i + 1) if 0 <= j < 4] if fam == "GM" else grid_nb[i]
            nbpass = sum(1 for j in nb if res[cfgs[j][0]]["기본 통과"])
            ok = res[cfg[0]]["기본 통과"] and nbpass >= 1                  # 자기 + 이웃 1 이상 = 2개 이상(원판 읽기)
            res[cfg[0]]["통과"] = ok
            if pub["rows"][cfg[0]]["통과"] != ok: bad += 1; say(f"  다름 {cfg[0]} 통과")
            if ok: passed.append((fam, cfg[0]))
            if res[cfg[0]]["기본 통과"] and nbpass >= 2: strict.append((fam, cfg[0]))
    def pick(lst):
        if not lst: return None
        fams = {}
        for f, k in lst: fams.setdefault(f, []).append(k)
        fb = max(fams, key=lambda f: max(res[k]["MDD"] for k in fams[f]))
        return max(fams[fb], key=lambda k: res[k]["합"])
    pk = pick(passed)
    bad += (pub["통과"] != [k for _, k in passed]) + (pub["새 자료 후보(사용자 승인 뒤)"] != pk)
    say("  통과(검산):", [k for _, k in passed], "· 후보(검산):", pk, "· 원판 후보:", pub["새 자료 후보(사용자 승인 뒤)"])
    say("  엄한 읽기(이웃만 2개 이상 통과)라면 통과:", [k for _, k in strict], "· 후보:", pick(strict))
    say("  성적 · 판정 · 후보 다른 칸 모두:", bad)
    # 3
    say("== 3 미래 참조")
    viol = nxt_bad = prev_day = 0
    for n, d, m, i in USE:
        B = MY[n][0]
        if i >= 0 and (B[i][0], B[i][1]) > (d, m): viol += 1
        if i + 1 < len(B) and (B[i + 1][0], B[i + 1][1]) <= (d, m): nxt_bad += 1
        if i >= 0 and B[i][0] != d: prev_day += 1
    say(f"  30 · 60분봉 사용 {len(USE)}번: 쓴 봉 끝 > 신호 분 {viol} · 다음 봉 끝 ≤ 신호 분(덜 최신) {nxt_bad} · 앞 날 봉을 쓴 경우 {prev_day}(장 초반 · 과거라 문제 없음)")
    st_bad = sum(1 for d in DAYS if not Z[d] for s in R4.s3(d) if K.B15[IDX15[(d, s[0])]][1] != s[0])
    say("  15분 이격: 신호 분과 끝 분이 다른 15분봉을 쓴 경우", st_bad, "(끝 분 m 봉 = m−15 ~ m−1 분 · 진입은 m분 시가)")
    cut_res = {}
    for c in ("20260415", "20260605", "20260820"):
        subprocess.run([sys.executable, str(HERE / "kmf_hdd_pre.py")], env=dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_aud"), check=True, capture_output=True)
        part = json.loads((HERE / "kmf_hdd_pre_daily_aud.json").read_text()); po = json.loads((HERE / "kmf_hdd_pre_out_aud.json").read_text())
        n_cmp = sum(1 for k in pday for d in part[k] if d < c)
        cut_res[c] = {"비교 칸": n_cmp, "다른 칸": sum(1 for k in pday for d, v in part[k].items() if d < c and abs(v - pday[k][d]) > 1e-9),
                      "자른 날 뒤 칸(있으면 안 됨)": sum(1 for k in part for d in part[k] if d >= c), "엔진 마지막 날": po["meta"]["engine_last"]}
    for f in ("kmf_hdd_pre_daily_aud.json", "kmf_hdd_pre_out_aud.json"): (HERE / f).unlink(missing_ok=True)
    say("  자르기 시험(자른 날부터 뒤 줄을 처음부터 안 읽음 · 새 프로세스):", json.dumps(cut_res, ensure_ascii=False))
    # 4
    say("== 4 GB 밴드 1.5 = 2.0 까닭")
    allst, rnaok, band = [], [], []
    for d in DAYS:
        if Z[d]: continue
        for s in R4.s3(d):
            x = my_stretch(d, s[0]); allst.append(x)
            if my_rna(30, d, s[0]) == s[1]: rnaok.append(x)
    say(f"  조용하지 않은 날 S3 신호 {len(allst)}개: 이격 ÷ ATR 가장 큼 {max(allst):.3f} · 1.5 초과 {sum(1 for x in allst if x > 1.5)} · 1.5 초과 2.0 이하 {sum(1 for x in allst if 1.5 < x <= 2.0)}")
    say(f"  30분 합치 통과 {len(rnaok)}개: 1.5 초과 2.0 이하 {sum(1 for x in rnaok if 1.5 < x <= 2.0)} · 2.0 초과 {sum(1 for x in rnaok if x > 2.0)} · 가장 큼 {max(rnaok):.3f}")
    say("  구간별 개수(전체 S3):", {f"{lo}~{lo + 0.25}": sum(1 for x in allst if lo <= x < lo + 0.25) for lo in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75)} | {"2.0 이상": sum(1 for x in allst if x >= 2.0)})
    say("  1.5 넘는 이격 가장 작은 값:", round(min(x for x in allst if x > 1.5), 3), "· 1.5 이하 가장 큰 값:", round(max(x for x in allst if x <= 1.5), 3))
    # 5
    say("== 5 GM MDD 구간 · 어느 팔에서 잃었나")
    for k in ["H(대조)"] + [c[0] for c in FAM["GM"]]:
        p = DAILY[k]; dd, a, b = mdd_episode(p)
        seg = [d for d in DAYS if a < d <= b] if a else [d for d in DAYS if d <= b]
        r0 = sum(p[d] for d in seg if Z[d]); s3 = sum(p[d] for d in seg if not Z[d])
        say(f"  {k}: MDD {dd:.2f} · 고점 {a} → 바닥 {b} · 구간 {len(seg)}일(조용 {sum(1 for d in seg if Z[d])}일) · R0 날 합 {r0:.2f} · S3 날 합 {s3:.2f}")
    gm = [c[0] for c in FAM["GM"]]
    def worst_from(p, a, b):
        seg = [d for d in DAYS if a < d <= b]; return round(sum(p[d] for d in seg), 4), sum(1 for d in seg if Z[d])
    for a, b, why in (("20260623", "20260701", "S3만 있는 구간"), ("20260518", "20260604", "N5 구간"), ("20261002", "20261013", "N4 구간"), ("20260831", "20260908", "H 구간")):
        say(f"  {why} {a}→{b}(조용 {worst_from(H, a, b)[1]}일) 손익 합:", {k: worst_from(DAILY[k], a, b)[0] for k in gm + ["H(대조)"]})
    say("  MDD 소수 4자리:", {k: round(raw_mdd(DAILY[k]), 4) for k in gm + ["H(대조)"]})
    say("  H 구간(08-31→09-08) R0 날 손익(N3 · N4 · N5 · N6 · H):")
    for d in DAYS:
        if "20260831" < d <= "20260908" and Z[d]: say("   ", d, [round(DAILY[k][d], 2) for k in gm + ["H(대조)"]])
    say("  S3 날 GM과 H 다른 칸:", sum(1 for k in gm for d in DAYS if not Z[d] and abs(DAILY[k][d] - H[d]) > 1e-12),
        "→ GM은 R0만 바꾸므로 조용한 날이 하나도 없는 06-23→07-01 S3 낙폭(−35.10)은 어떤 GM 설정도 못 줄임 = GM MDD의 바닥")
    # 6
    say("== 6 자료 · 코드 해시")
    act = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
    src = (HERE / "kmf_hdd_pre.py").read_text(); exp = {}
    for line in src[src.index("DATA_EXPECT = {"):].split("}")[0].split("\n"):
        if '": "' in line:
            parts = line.split('"'); exp[parts[1]] = parts[3]
    say("  실제 = meta:", act == pub["meta"]["data_sha256"], "· 실제 = DATA_EXPECT:", act == exp, "· 파일 3개:", len(exp))
    code = {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in pub["meta"]["code_sha256"]}
    say("  코드 해시 = meta:", {f: code[f] == v for f, v in pub["meta"]["code_sha256"].items()})
    (HERE / "kmf_hdd_pre_audit.out").write_text("\n".join(OUT) + "\n")

if __name__ == "__main__": main()
