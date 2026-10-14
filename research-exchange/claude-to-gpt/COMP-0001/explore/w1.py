"""창 ① (09:00~09:45) 전용 미니 코스피200 선물 RNA 봇 비교 · 1계약 · 한쪽 0.04 · 하루 멈춤 12 · 지연 0.
진입 = 15분봉 끝 09:15(555분) · 09:30(570분)만 · 모든 신호 정리 분 = 585(09:45 시가에 정리).
신호 자료: 그날 끝난 15분봉 · 전날까지 끝난 30/60분봉(rna_dir(n, d, 540)) · 전날까지 날봉 · 09:00 시가(갭).
판은 결과 보기 전에 아래 VARIANTS로 고정(16개 이하). 고르지 않음 · 이웃만 보여 줌.
python3 w1.py → w1_out.json · w1_daily.json  |  python3 w1.py --cut-test → 자르기 시험."""
import sys, os, json, collections, statistics as st
R8 = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/r8/research"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R8)
import kmf_nb as K
import kmf_rlk4 as R                                     # TF · rna_dir (30/60분)

EXIT = 585
J15 = {(K.B15[j][0], K.B15[j][1]): j for j in range(len(K.B15))}
DIDX = {d: i for i, d in enumerate(K.DAYS)}

# 날봉 ATR(날 폭 EMA14) · 날 종가 EMA10 · EMA20 — 그날 앞 날까지만
DAILY = {}
e10 = e20 = a = None
for d in K.DAYS:
    DAILY[d] = (e10, e20, a)                              # d 시작 때 알려진 값(전날까지)
    x = K.BY[d]; c = K.last_close(d); rng = max(r[3] for r in x.values()) - min(r[4] for r in x.values())
    e10 = c if e10 is None else e10 + (c - e10) * 2 / 11; e20 = c if e20 is None else e20 + (c - e20) * 2 / 21
    a = rng if a is None else a + (rng - a) * 2 / 15

def prev_day(d):
    i = DIDX[d]; return K.DAYS[i - 1] if i > 0 else None

def bar(d, m):
    j = J15.get((d, m));
    if j is None: return None
    b = K.B15[j]; e1, at = K.E10[j]; e2 = K.E20[j][0]
    sl = (e2 - K.E20[j - 4][0]) if j >= 4 else 0.0
    return dict(o=b[2], h=b[3], l=b[4], c=b[5], e10=e1, e20=e2, atr=at, sl=sl, j=j)

def gap_units(d):
    p = prev_day(d); da = DAILY[d][2]
    if p is None or not da: return None
    o = K.BY[d].get(540)
    if o is None: return None                             # 09:00 첫 분이 없으면 갭 모름
    return (o[2] - K.last_close(p)) / da

# ---------- 신호 ----------
def v_gap_fade(d, k, s=1.0):
    """갭 되돌림: |갭| ≥ k×날ATR · 09:15 15분 종가가 아직 갭 쪽으로 EMA10 바깥(위 갭이면 종가 > EMA10) → 반대로 · 목표 = 전날 종가."""
    g = gap_units(d); b = bar(d, 555)
    if g is None or b is None or abs(g) < k: return []
    side = -1 if g > 0 else 1
    if not ((b["c"] > b["e10"]) if g > 0 else (b["c"] < b["e10"])): return []
    return [(555, side, K.last_close(prev_day(d)), s * b["atr"], EXIT)]

def v_gap_follow(d, k, s=1.0):
    """갭 따라감: |갭| ≥ k×날ATR · 09:15 종가가 갭 방향으로 시가보다 더 가고 EMA10 같은 쪽 → 따라감 · 목표 없음."""
    g = gap_units(d); b = bar(d, 555); o = K.BY[d].get(540)
    if g is None or b is None or abs(g) < k: return []
    up = g > 0
    if not ((b["c"] > o[2] and b["c"] > b["e10"]) if up else (b["c"] < o[2] and b["c"] < b["e10"])): return []
    return [(555, 1 if up else -1, None, s * b["atr"], EXIT)]

def v_band_rev(d, k, s=1.0, flat=None):
    """15분 EMA10 띠 되돌림(R0를 창 안으로): 09:15 · 09:30 종가가 EMA10 ± k×ATR 바깥 → 반대 · 목표 EMA10.
    flat 주면 |EMA20 4봉 기울기|/ATR ≤ flat 일 때만."""
    out = []
    for m in (555, 570):
        b = bar(d, m)
        if b is None or b["atr"] <= 0: continue
        if flat is not None and abs(b["sl"]) / b["atr"] > flat: continue
        if abs(b["c"] - b["e10"]) >= k * b["atr"]: out.append((m, -1 if b["c"] > b["e10"] else 1, b["e10"], s * b["atr"], EXIT))
    return out

def v_first_cont(d, k, s=1.0):
    """첫 15분봉 이어감: 09:15 종가가 EMA10 ± k×ATR 바깥이고 그 방향이 전날 60분 RNA 방향과 같음 → 따라감."""
    b = bar(d, 555); dr = R.rna_dir(60, d, 540)
    if b is None or dr == 0 or b["atr"] <= 0: return []
    dev = (b["c"] - b["e10"]) / b["atr"]
    if (dev >= k and dr > 0) or (dev <= -k and dr < 0): return [(555, dr, None, s * b["atr"], EXIT)]
    return []

def v_trend_brk(d, when, s=1.0):
    """전날 RNA 추세(60분 · 30분 둘 다 같은 방향) 쪽 이른 돌파.
    09:15: 첫 봉 종가 > 시가 · > EMA10(위 방향 · 아래는 반대). 09:30: 둘째 봉 종가 > 첫 봉 고가(아래는 < 저가)."""
    dr = R.rna_dir(60, d, 540)
    if dr == 0 or R.rna_dir(30, d, 540) != dr: return []
    out = []; b1 = bar(d, 555)
    if b1 is None: return []
    if 555 in when and ((b1["c"] > b1["o"] and b1["c"] > b1["e10"]) if dr > 0 else (b1["c"] < b1["o"] and b1["c"] < b1["e10"])):
        out.append((555, dr, None, s * b1["atr"], EXIT))
    b2 = bar(d, 570)
    if 570 in when and b2 is not None and ((b2["c"] > b1["h"]) if dr > 0 else (b2["c"] < b1["l"])):
        out.append((570, dr, None, s * b2["atr"], EXIT))
    return out

VARIANTS = {
    "A 갭 되돌림 k0.3": lambda d: v_gap_fade(d, 0.3),
    "A 갭 되돌림 k0.5": lambda d: v_gap_fade(d, 0.5),
    "A 갭 되돌림 k0.7": lambda d: v_gap_fade(d, 0.7),
    "B 갭 따라감 k0.3": lambda d: v_gap_follow(d, 0.3),
    "B 갭 따라감 k0.5": lambda d: v_gap_follow(d, 0.5),
    "C 띠 되돌림 k1.0": lambda d: v_band_rev(d, 1.0),
    "C 띠 되돌림 k1.5": lambda d: v_band_rev(d, 1.5),
    "C 띠 되돌림 k2.0": lambda d: v_band_rev(d, 2.0),
    "F 띠 되돌림 k1.0 평평≤0.5": lambda d: v_band_rev(d, 1.0, flat=0.5),
    "F 띠 되돌림 k1.5 평평≤0.5": lambda d: v_band_rev(d, 1.5, flat=0.5),
    "D 첫봉 이어감(60분 RNA) k0.5": lambda d: v_first_cont(d, 0.5),
    "D 첫봉 이어감(60분 RNA) k1.0": lambda d: v_first_cont(d, 1.0),
    "E 추세 돌파 09:15만": lambda d: v_trend_brk(d, (555,)),
    "E 추세 돌파 09:30만": lambda d: v_trend_brk(d, (570,)),
    "E 추세 돌파 둘 다": lambda d: v_trend_brk(d, (555, 570)),
}
EVAL = [d for d in K.DAYS if "20260108" <= d <= "20261013"]
P1 = set(json.load(open(os.path.join(R8, "kmf_p1_closed_days.json")))["P1 쉬는 날"])
HOLE = "20260608"

def stats(p, days, logs_by_day):
    eq = pk = mdd = 0.0
    for d in days: eq += p[d]; pk = max(pk, eq); mdd = min(mdd, eq - pk)
    tr = [t for d in days for t in logs_by_day.get(d, [])]
    mon = collections.defaultdict(float)
    for d in days: mon[d[:6]] += p[d]
    h = len(days) // 2; top = sorted(days, key=lambda d: -p[d])[:5]
    wm = min(mon.items(), key=lambda kv: kv[1])
    return {"합": round(sum(p[d] for d in days), 2), "MDD": round(mdd, 2), "최악일": round(min(p[d] for d in days), 2),
            "거래일": sum(1 for d in days if logs_by_day.get(d)), "거래수": len(tr),
            "승률": round(sum(1 for t in tr if t["손익"] > 0) / len(tr), 3) if tr else None,
            "앞절반": round(sum(p[d] for d in days[:h]), 2), "뒤절반": round(sum(p[d] for d in days[h:]), 2),
            "최악달": f"{wm[0]} {wm[1]:.2f}", "−15 미만 날": sum(1 for d in days if p[d] < -15),
            "상위5일 합": round(sum(p[d] for d in top), 2), "상위5일 뺀 합": round(sum(p[d] for d in days) - sum(p[d] for d in top), 2)}

def run():
    res, daily = {}, {}
    for name, f in VARIANTS.items():
        p, lb = {}, {}
        for d in EVAL:
            log = []; p[d] = K.execute(d, f(d), delay=0, log=log); lb[d] = log
        assert all(t["정리분"] <= EXIT or t["사유"] in ("손절", "목표", "하루멈춤") for d in lb for t in lb[d])
        assert all(t["진입분"] in (555, 570) or t["진입분"] < EXIT for d in lb for t in lb[d])
        nohole = [d for d in EVAL if d != HOLE]; p1d = [d for d in EVAL if d in P1]
        res[name] = {"전체": stats(p, EVAL, lb), "06-08 뺌": stats(p, nohole, lb), "P1 쉬는 날": stats(p, p1d, lb),
                     "06-08 손익": round(p.get(HOLE, 0.0), 2)}
        daily[name] = {d: round(p[d], 4) for d in EVAL}
    return res, daily

if __name__ == "__main__":
    sfx = os.getenv("W1_SFX", "")
    if sys.argv[1:] == ["--cut-test"]:
        import subprocess
        full = json.load(open(os.path.join(HERE, "w1_daily.json"))); out = {}
        for c in ("20260401", "20260701", "20260901"):
            subprocess.run([sys.executable, __file__], env=dict(os.environ, KMF_CUT=c, W1_SFX="_cut"), check=True, capture_output=True)
            part = json.load(open(os.path.join(HERE, "w1_daily_cut.json")))
            out[c] = sum(1 for k in full for d, v in part[k].items() if d < c and abs(v - full[k][d]) > 1e-9)
        os.remove(os.path.join(HERE, "w1_daily_cut.json")); os.remove(os.path.join(HERE, "w1_out_cut.json"))
        print("자르기 시험 다른 칸", out); sys.exit(1 if sum(out.values()) else 0)
    res, daily = run()
    meta = {"평가 날": len(EVAL), "첫날": EVAL[0], "끝날": EVAL[-1], "P1 쉬는 날(평가 안)": sum(1 for d in EVAL if d in P1)}
    json.dump({"meta": meta, "res": res}, open(os.path.join(HERE, f"w1_out{sfx}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(daily, open(os.path.join(HERE, f"w1_daily{sfx}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(json.dumps(meta, ensure_ascii=False))
    for n, r in res.items():
        a, b, c = r["전체"], r["06-08 뺌"], r["P1 쉬는 날"]
        print(f"{n:28s} 합{a['합']:7.2f} MDD{a['MDD']:7.2f} 최악{a['최악일']:6.2f} 일{a['거래일']:3d} 수{a['거래수']:3d} 승{a['승률']} 앞{a['앞절반']:6.2f} 뒤{a['뒤절반']:6.2f} 달[{a['최악달']}] <-15:{a['−15 미만 날']} top5 {a['상위5일 합']:6.2f} 뺀{a['상위5일 뺀 합']:6.2f} | 0608뺌 {b['합']:6.2f} (0608 {r['06-08 손익']}) | P1 {c['합']:6.2f} MDD{c['MDD']:6.2f} n{c['거래일']}")
