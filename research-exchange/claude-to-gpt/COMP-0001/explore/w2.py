"""창 ② (P1 쉬는 날 · 09:45~15:15) 미니 코스피200 선물 1계약 RNA 봇 비교 — 연구용 · 고르지 않음.
신호: 끝난 15/30/60분봉만 · 진입은 봉 끝 분 >= 585(09:45)만 · 1분봉은 체결 · 손절에만(K.execute).
비용 0.04/쪽 · 하루 멈춤 12 · 지연 0 · 15:15(915) 정리.
진단(날 폭/ATR · 방향 효율)은 그날 뒤 자료를 쓰므로 신호로 절대 안 씀 · 설명용만."""
import sys, json, bisect, collections, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
R8 = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/r8/research")
sys.path.insert(0, str(R8))
import kmf_nb as K

REST = json.loads((R8 / "kmf_p1_closed_days.json").read_text())["P1 쉬는 날"]
PERIOD = [d for d in K.DAYS if "20260102" <= d <= "20261012"]
REST = [d for d in REST if d in K.BY]
TRADE_DAYS = [d for d in PERIOD if d not in set(REST)]
HOLES = ["20260304", "20260309", "20260608", "20260623", "20260626", "20260707", "20260713", "20260728", "20260729"]
START = 585

TF = {}
for n in (30, 60):
    B = K.bars(n); E10 = K.ind(B, 10); E20 = K.ind(B, 20); TF[n] = (B, E10, E20, [(b[0], b[1]) for b in B])
J15 = {(K.B15[j][0], K.B15[j][1]): j for j in range(len(K.B15))}
K15 = [(b[0], b[1]) for b in K.B15]

def rna_dir(n, d, m):
    """m분 시각에 끝나 있던 마지막 n분봉의 RNA 방향(그날 봉만 보면 앞날 봉도 포함 · 날 넘어 이어짐)."""
    if n == 15:
        i = bisect.bisect_right(K15, (d, m)) - 1
        if i < 4: return 0
        e10, e20, sl = K.E10[i][0], K.E20[i][0], K.E20[i][0] - K.E20[i - 4][0]
    else:
        B, E10, E20, keys = TF[n]; i = bisect.bisect_right(keys, (d, m)) - 1
        if i < 4: return 0
        e10, e20, sl = E10[i][0], E20[i][0], E20[i][0] - E20[i - 4][0]
    return 1 if (e10 > e20 and sl > 0) else (-1 if (e10 < e20 and sl < 0) else 0)

def slope15(d, m):
    j = J15[(d, m)]; a = K.E10[j][1]
    return abs(K.E20[j][0] - K.E20[j - 4][0]) / a if a else 99.0

def win(sigs): return [s for s in sigs if s[0] >= START]
def r0(k, s=1.0): return lambda d: win(K.sig_r0(d, k, s))
def t2(s): return lambda d: win(K.sig_t(d, "T2", s=s))
def s3w(th): return lambda d: [x for x in t2(1.5)(d) if slope15(d, x[0]) <= th]
s3 = s3w(0.5)
def r0_f(k, mode):
    def f(d):
        out = []
        for x in r0(k)(d):
            r30, r60 = rna_dir(30, d, x[0]), rna_dir(60, d, x[0])
            if mode == "60같은쪽" and r60 != x[1]: continue          # 60분 추세 쪽으로만 되돌림
            if mode == "60거스름뺌" and r60 == -x[1]: continue
            if mode == "30·60하나라도거스름뺌" and (r30 == -x[1] or r60 == -x[1]): continue
            out.append(x)
        return out
    return f
def switch(mode):
    """09:45(585분)에 끝나 있던 봉의 RNA로 그날 방식 고정: 정렬 → 그 방향 T2 s1.5 · 아니면 R0 k1.0."""
    def f(d):
        r15, r30, r60 = (rna_dir(n, d, START) for n in (15, 30, 60))
        al = r15 if (mode == "15·30·60" and r15 != 0 and r15 == r30 == r60) else (r60 if mode == "60만" else 0)
        if al: return [x for x in t2(1.5)(d) if x[1] == al]
        return r0(1.0)(d)
    return f

VARS = {
    "R0 k0.75 s1.0": r0(0.75), "R0 k1.0 s1.0": r0(1.0), "R0 k1.25 s1.0": r0(1.25), "R0 k1.5 s1.0": r0(1.5),
    "R0 k1.0 s1.5": r0(1.0, 1.5), "R0 k1.0 s0.75": r0(1.0, 0.75),
    "R0 k1.0 + 60분 추세 쪽만": r0_f(1.0, "60같은쪽"), "R0 k1.0 − 60분 거스름 뺌": r0_f(1.0, "60거스름뺌"),
    "R0 k1.0 − 30·60 하나라도 거스름 뺌": r0_f(1.0, "30·60하나라도거스름뺌"),
    "T2 s1.0": t2(1.0), "T2 s1.5": t2(1.5), "S3 (T2 s1.5 + 기울기/ATR≤0.5)": s3, "S3 이웃 ≤0.35": s3w(0.35), "S3 이웃 ≤0.75": s3w(0.75),
    "바꿈: 09:45 15·30·60 정렬→T2 · 아니면 R0": switch("15·30·60"), "바꿈: 09:45 60분 RNA→T2 · 평평→R0": switch("60만"),
}

def stats(p, ntr, ntr_win, days):
    eq = pk = mdd = 0.0
    for d in days: eq += p[d]; pk = max(pk, eq); mdd = min(mdd, eq - pk)
    h = len(days) // 2; top = sorted(days, key=lambda d: -p[d])[:5]
    tot = sum(p[d] for d in days)
    return {"합": round(tot, 2), "MDD": round(mdd, 2), "최악": round(min(p[d] for d in days), 2),
            "거래일": sum(1 for d in days if ntr[d]), "거래수": sum(ntr[d] for d in days),
            "승률%": round(100 * sum(ntr_win[d] for d in days) / max(1, sum(ntr[d] for d in days)), 1),
            "앞반": round(sum(p[d] for d in days[:h]), 2), "뒤반": round(sum(p[d] for d in days[h:]), 2),
            "−15 아래 날": sum(1 for d in days if p[d] < -15), "상위5일 합": round(sum(p[d] for d in top), 2), "상위5일 뺀 합": round(tot - sum(p[d] for d in top), 2)}

def run(days):
    res, daily, trades = {}, {}, {}
    for name, f in VARS.items():
        p, ntr, nw, log = {}, collections.Counter(), collections.Counter(), []
        for d in days:
            n0 = len(log); p[d] = K.execute(d, f(d), delay=0, log=log)
            ntr[d] = len(log) - n0; nw[d] = sum(1 for t in log[n0:] if t["손익"] > 0)
        res[name] = {"전체64": stats(p, ntr, nw, days),
                     "06-08(구멍) 뺌": stats(p, ntr, nw, [d for d in days if d not in HOLES]),
                     "01-02(EMA 준비 덜 됨) 뺌": stats(p, ntr, nw, [d for d in days if d != "20260102"])}
        daily[name] = {d: round(p[d], 4) for d in days}; trades[name] = log
    return res, daily, trades

def diag():
    """그날 뒤 자료로만 하는 진단(신호 아님): 09:45~15:15 폭 ÷ 09:45 때 15분 ATR · 방향 효율 |끝−시작| ÷ 1분 종가 변화 합 · |끝−시작| ÷ 폭."""
    out = {}
    for name, days in (("P1 쉬는 날", REST), ("P1 거래하는 날", TRADE_DAYS)):
        rr, ef, nr = [], [], []
        for d in days:
            ms = [m for m in sorted(K.BY[d]) if START <= m < 915]
            if len(ms) < 30 or (d, START) not in J15: continue
            a = K.E10[J15[(d, START)]][1]
            hi = max(K.BY[d][m][3] for m in ms); lo = min(K.BY[d][m][4] for m in ms)
            o = K.BY[d][ms[0]][2]; c = K.BY[d][ms[-1]][5]
            path = sum(abs(K.BY[d][ms[i]][5] - K.BY[d][ms[i - 1]][5]) for i in range(1, len(ms))) or 1e-9
            rr.append((hi - lo) / a if a else 0); ef.append(abs(c - o) / path); nr.append(abs(c - o) / (hi - lo) if hi > lo else 0)
        out[name] = {"날": len(rr), "폭/ATR15 가운데": round(st.median(rr), 2), "폭/ATR15 평균": round(st.mean(rr), 2),
                     "경로 효율 가운데": round(st.median(ef), 3), "경로 효율 평균": round(st.mean(ef), 3),
                     "|끝−시작|/폭 가운데": round(st.median(nr), 3), "|끝−시작|/폭 평균": round(st.mean(nr), 3)}
    return out

if __name__ == "__main__":
    res, daily, trades = run(REST)
    meta = {"쉬는 날 수": len(REST), "구멍 날 중 쉬는 날": [d for d in HOLES if d in REST], "첫날": REST[0], "끝날": REST[-1],
            "앞반 끝": REST[len(REST) // 2 - 1], "판 수": len(VARS)}
    out = {"meta": meta, "진단(신호 아님)": diag(), "판": res}
    (HERE / "w2_out.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (HERE / "w2_daily.json").write_text(json.dumps(daily, ensure_ascii=False))
    (HERE / "w2_trades.json").write_text(json.dumps(trades, ensure_ascii=False))
    print(json.dumps(meta, ensure_ascii=False)); print(json.dumps(out["진단(신호 아님)"], ensure_ascii=False))
    for k, v in res.items():
        a = v["전체64"]; b = v["06-08(구멍) 뺌"]
        print(f"{k:40s} 합{a['합']:7.2f} MDD{a['MDD']:7.2f} 최악{a['최악']:6.2f} 일{a['거래일']:3d} 수{a['거래수']:3d} 승{a['승률%']:5.1f} 앞{a['앞반']:6.2f} 뒤{a['뒤반']:6.2f} <-15:{a['−15 아래 날']} 상5{a['상위5일 합']:6.2f} 뺀{a['상위5일 뺀 합']:7.2f} | 구멍뺌 {b['합']:.2f} | 01-02뺌 {v['01-02(EMA 준비 덜 됨) 뺌']['합']:.2f}")
