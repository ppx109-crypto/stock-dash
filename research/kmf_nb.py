"""KMF 새 봇 비교(RLK-0002 · 공개 · 표준 라이브러리만). v12 · 사용자 운영 봇 규칙은 하나도 안 씀.
자료: kiwoom-data/mini_1min_2026_01_08.csv(01-02 ~ 08-31) + kiwoom-data/kospi200_futures_1min.csv(09-01 ~ 10-12 · 미니 A056* · 그날 거래량 1등 계약)
      + futures-1m/mini_kospi200_futures_1min.csv(10-13 하루) · 개발 끝 = 10-13(10-14부터는 안 읽음 · 시험 자료 보호).
신호는 15분봉(끝난 봉만) · 1분봉은 체결 · 손절 · 평가에만. 1계약 · 한쪽 0.04p · 하루 멈춤 12p · 장 끝 하루 −15p 잣대.
python3 research/kmf_nb.py → research/kmf_nb_out.json(판별 성적) · kmf_nb_daily.json(판 · 지연별 날별 손익) · kmf_nb_trades.json(주요 4판 거래별 · 지연 0) · --cut-test."""
import csv, json, os, sys, statistics as st, itertools, collections, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "kiwoom-data/mini_1min_2026_01_08.csv"; FUT = ROOT / "kiwoom-data/kospi200_futures_1min.csv"; F1M = ROOT / "futures-1m/mini_kospi200_futures_1min.csv"
DEV_FROM_F1M, DEV_END = "20261013", "20261014"           # futures-1m은 10-13 하루만 · 10-14부터는 처음부터 안 읽음
COST, CAP, FIRST, LAST = 0.04, 12.0, 540, 934
CUT = os.getenv("KMF_CUT", "")                          # 자르기 시험: 이 날부터 뒤 줄은 읽으면서 버림(파일은 열고 해시는 파일 전체)

def load():
    rows = []
    with open(MINI, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            m = int(r["minute"])
            if CUT and r["date"] >= CUT: continue
            if FIRST <= m <= LAST: rows.append((r["date"], m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"]))))
    last = max(r[0] for r in rows); fut = collections.defaultdict(list)
    with open(FUT, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            d = r["datetime"][:10].replace("-", "")
            if d <= last or d >= DEV_FROM_F1M or not r["code"].startswith("A056") or (CUT and d >= CUT): continue
            m = int(r["datetime"][11:13]) * 60 + int(r["datetime"][14:16])
            if FIRST <= m <= LAST: fut[d].append((r["code"], m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"]))))
    for d in sorted(fut):
        vol = collections.Counter()
        for x in fut[d]: vol[x[0]] += x[6]
        main = sorted(vol.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        rows += [(d,) + x[1:] for x in sorted((x for x in fut[d] if x[0] == main), key=lambda x: x[1])]
    with open(F1M, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            d = r["datetime"][:10].replace("-", "")
            if not (DEV_FROM_F1M <= d < DEV_END) or (CUT and d >= CUT): continue
            m = int(r["datetime"][11:13]) * 60 + int(r["datetime"][14:16])
            if FIRST <= m <= LAST: rows.append((d, m, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), int(float(r["volume"]))))
    return sorted(rows, key=lambda r: (r[0], r[1]))

ROWS = load(); BY = collections.defaultdict(dict); DUP = 0
for r in ROWS:
    if r[1] in BY[r[0]]: DUP += 1
    BY[r[0]][r[1]] = r
DAYS = sorted(BY)

def px(d, m):
    x = BY[d]
    for mm in range(m, 935):
        if mm in x: return x[mm][2]
    return None
def last_close(d):
    x = BY[d]; return x[max(x)][5]

def bars(n):
    """n분봉 (날, 끝 분, 시, 고, 저, 종) · 끝 분 = 다음 봉 첫 분 · 15:15(914분)까지 1분봉만 묶음."""
    out = []
    for d in DAYS:
        g = {}
        for m in sorted(BY[d]):
            if m > 914: continue
            k = (m - 540) // n; r = BY[d][m]
            if k not in g: g[k] = [r[2], r[3], r[4], r[5]]
            else: g[k][1] = max(g[k][1], r[3]); g[k][2] = min(g[k][2], r[4]); g[k][3] = r[5]
        out += [(d, 540 + (k + 1) * n, *g[k]) for k in sorted(g)]
    return out
def ind(B, L, A=14):
    """봉 끝까지의 EMA(L) · ATR 근사(봉 폭의 EMA 14) · 날 넘어 이어짐."""
    e = a = None; res = []
    for b in B:
        c, tr = b[5], b[3] - b[4]
        e = c if e is None else e + (c - e) * 2 / (L + 1); a = tr if a is None else a + (tr - a) * 2 / (A + 1); res.append((e, a))
    return res
B15 = bars(15); E10 = ind(B15, 10); E20 = ind(B15, 20)
BYD = collections.defaultdict(list)
for j, b in enumerate(B15): BYD[b[0]].append(j)

def execute(d, sigs, delay=0, maxn=2, log=None):
    """신호 (봉 끝 분 m, 방향, 목표 또는 None, 손절 폭, 정리 분) → 그날 비용 뒤 손익.
    진입 = m+지연 분부터 처음 있는 1분봉의 시가(그 분 = 실제 진입 분). 손절값은 남은 하루 예산 안 · 남은 예산 3p 미만이면 새 진입 없음(정책 조건).
    진입한 분도 손절 검사(분 안 순서 모름 → 나쁜 쪽). 그 분 끝 실현 + 평가 ≤ −12 → 다음 분 시가.
    다음 진입 가능 시각: 시가에 정리(정리 분 · 하루 멈춤 · 15:15)했으면 그 분 시가부터 · 분 도중(손절 · 목표)이면 다음 분부터(RLK-0002 round 2 · GPT 결함 1)."""
    x = BY[d]; real = 0.0; cnt = 0; free_at = 0; stopped = False
    for (m0, side, tg, sd, m_exit) in sigs:
        if stopped or cnt >= maxn or CAP + real < 3.0: continue
        me = next((mm for mm in range(m0 + delay, 935) if mm in x), None)
        if me is None or me < free_at or me >= m_exit + delay: continue
        ent = x[me][2]; sd = min(sd, max(0.5, CAP + real - 2 * COST)); stop = ent - side * sd; cnt += 1; out = None
        for m in range(me, 935):
            if m not in x: continue
            o, h, l, c = x[m][2], x[m][3], x[m][4], x[m][5]
            if m == me: o = ent
            if m >= m_exit + delay: out = (o, m, "정리분" if m_exit < 915 else "15:15", m); break
            if (l <= stop) if side > 0 else (h >= stop): out = (min(o, stop) if side > 0 else max(o, stop), m, "손절", m + 1); break
            if tg is not None and ((h >= tg) if side > 0 else (l <= tg)): out = (max(o, tg) if side > 0 else min(o, tg), m, "목표", m + 1); break
            if real + side * (c - ent) - 2 * COST <= -CAP:
                nm = next((mm for mm in range(m + 1, 935) if mm in x), None); out = (x[nm][2] if nm else c, nm or m, "하루멈춤", 999); stopped = True; break
        if out is None: out = (last_close(d), 935, "끝", 999)
        r = side * (out[0] - ent) - 2 * COST; real += r; free_at = out[3]
        if log is not None: log.append({"d": d, "신호분": m0, "진입분": me, "방향": side, "진입가": ent, "정리분": out[1], "정리가": out[0], "사유": out[2], "손익": round(r, 4)})
        if real <= -CAP: stopped = True
    return real

def sig_r0(d, k=1.0, s=1.0):
    """R0: 15분 종가가 EMA10에서 k×ATR 이상 벌어지면 반대로 · 목표 = 신호 때 EMA10 · 손절 s×ATR · 15:15 정리."""
    out = []
    for j in BYD[d]:
        b = B15[j]; e, a = E10[j]
        if b[1] > 900 or a <= 0: continue
        if abs(b[5] - e) >= k * a: out.append((b[1], -1 if b[5] > e else 1, e, s * a, 915))
    return out
def sig_t(d, kind, N=8, s=1.0):
    """T1: EMA10 · EMA20 배열과 EMA20 4봉 기울기가 같은 방향 + 앞 N봉 고가(저가) 돌파 종가 → 따라감.
    T2: 같은 방향 + 앞 봉 종가가 EMA10 반대편 · 이번 봉 종가가 다시 방향 쪽 → 따라감.
    정리: 뒤 15분 종가가 EMA10을 거꾸로 건너면 그 봉 끝 · 아니면 15:15 · 손절 s×ATR."""
    js = BYD[d]; out = []
    for t, j in enumerate(js):
        b = B15[j]; e10, a = E10[j]; e20 = E20[j][0]
        if b[1] > 900 or j < 4: continue
        slope = e20 - E20[j - 4][0]; up = e10 > e20 and slope > 0; dn = e10 < e20 and slope < 0
        if not (up or dn): continue
        if kind == "T1":
            prev = [B15[q] for q in range(max(0, j - N), j)]
            if len(prev) < N or not ((b[5] > max(p[3] for p in prev)) if up else (b[5] < min(p[4] for p in prev))): continue
        else:
            pb, pe = B15[j - 1], E10[j - 1][0]
            if not ((pb[5] < pe and b[5] > e10) if up else (pb[5] > pe and b[5] < e10)): continue
        m_exit = 915
        for q in js[t + 1:]:
            bb = B15[q]
            if bb[1] > 915: break
            if (bb[5] < E10[q][0]) if up else (bb[5] > E10[q][0]): m_exit = bb[1]; break
        out.append((b[1], 1 if up else -1, None, s * a, m_exit))
    return out

# 자체 조용함: 그날 뺀 앞 20일 하루 폭(%) 가운데 값 → 그 앞 날들의 같은 값과만 견준 순위 ≤ q
RNGP = {d: (max(r[3] for r in BY[d].values()) - min(r[4] for r in BY[d].values())) / last_close(d) * 100 for d in DAYS}
MED20 = {d: st.median(RNGP[q] for q in DAYS[i - 20:i]) for i, d in enumerate(DAYS) if i >= 20}
def quiet_state(q):
    """{날: True(조용) / False(조용하지 않음)} · 순위를 셀 수 없는 날(앞 MED20이 20개 미만)은 빠짐(준비 안 됨 · 거래 안 함 · GPT 결함 2)."""
    out, hist = {}, []
    for d in DAYS:
        if d not in MED20: continue
        if len(hist) >= 20: out[d] = sum(1 for h in hist if h <= MED20[d]) / len(hist) <= q
        hist.append(MED20[d])
    return out

def summ(p, days, ntr):
    """같은 평가 날짜(days)에서 · 날 끝 누적 MDD · 앞 = 06-01 앞 · 뒤 = 06-01부터(고정 분할 · 같은 길이 아님) · 거래일 = 진입이 1번 이상 있던 날."""
    eq = pk = mdd = 0.0
    for d in days: eq += p[d]; pk = max(pk, eq); mdd = min(mdd, eq - pk)
    return {"합": round(sum(p[d] for d in days), 2), "MDD": round(mdd, 2), "최악": round(min(p[d] for d in days), 2),
            "앞(~05-29)": round(sum(p[d] for d in days if d < "20260601"), 2), "뒤(06-01~)": round(sum(p[d] for d in days if d >= "20260601"), 2),
            "거래일": sum(1 for d in days if ntr.get(d)), "거래수": sum(ntr.get(d, 0) for d in days)}

def main():
    bots = {"R0": lambda d: sig_r0(d)}
    for N, s in itertools.product((4, 8), (1.0, 1.5)): bots[f"T1_N{N}_s{s}"] = (lambda N, s: lambda d: sig_t(d, "T1", N, s))(N, s)
    for s in (1.0, 1.5): bots[f"T2_s{s}"] = (lambda s: lambda d: sig_t(d, "T2", s=s))(s)
    SIG = {k: {d: f(d) for d in DAYS} for k, f in bots.items()}
    Qs = {q: quiet_state(q) for q in (0.4, 0.5, 0.6)}
    EVAL = [d for d in DAYS if d in Qs[0.4]]                     # 공통 평가 날짜 = 조용함 순위가 준비된 날(세 q 같음)
    choosers = {f"{k} · 늘": (lambda k: lambda d: k)(k) for k in bots}
    for q, Z in Qs.items():
        choosers[f"R0 · 자체 조용 q{q}"] = (lambda Z: lambda d: "R0" if Z.get(d) is True else None)(Z)
        for k in bots:
            if k == "R0": continue
            choosers[f"{k} · 조용하지 않은 날(q{q})"] = (lambda Z, k: lambda d: k if Z.get(d) is False else None)(Z, k)
            choosers[f"합침 R0(조용 q{q}) + {k}(조용하지 않은 날)"] = (lambda Z, k: lambda d: "R0" if Z.get(d) is True else (k if Z.get(d) is False else None))(Z, k)
    KEEP_TRADES = {"T2_s1.5 · 조용하지 않은 날(q0.6)", "합침 R0(조용 q0.6) + T2_s1.5(조용하지 않은 날)", "R0 · 자체 조용 q0.5", "R0 · 자체 조용 q0.6"}
    rows, daily, trades = [], {}, {}
    for label, ch in choosers.items():
        ss = []; daily[label] = {}
        for dl in (0, 1, 2):
            log = []; p = {}; ntr = collections.Counter()
            for d in EVAL:
                k = ch(d)
                if not k: p[d] = 0.0; continue
                n0 = len(log); p[d] = execute(d, SIG[k][d], delay=dl, log=log); ntr[d] = len(log) - n0
            ss.append(summ(p, EVAL, ntr)); daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}
            if dl == 0 and label in KEEP_TRADES: trades[label] = log
        rows.append({"봇": label, "합": [s["합"] for s in ss], "MDD": [s["MDD"] for s in ss], "장 끝 하루 최악": [s["최악"] for s in ss],
                     "앞(~05-29)": [s["앞(~05-29)"] for s in ss], "뒤(06-01~)": [s["뒤(06-01~)"] for s in ss], "거래일": ss[0]["거래일"], "거래수": ss[0]["거래수"],
                     "나쁜 합": min(s["합"] for s in ss), "나쁜 MDD": min(s["MDD"] for s in ss)})
    short15 = sum(1 for b in B15 if b[1] <= 915 and sum(1 for m in range(b[1] - 15, b[1]) if m in BY[b[0]]) < 15)
    meta = {"days": len(DAYS), "eval_days": len(EVAL), "eval_first": EVAL[0], "eval_last": EVAL[-1], "warmup_excluded": [DAYS[0], DAYS[len(DAYS) - len(EVAL) - 1]],
            "rows": len(ROWS), "duplicate_minutes": DUP, "short_15m_bars": short15, "quiet_days": {str(q): sum(1 for v in Z.values() if v) for q, Z in Qs.items()},
            "data_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (MINI, FUT, F1M)}}
    out = ROOT / "research"; sfx = os.getenv("KMF_OUT_SUFFIX", "")
    (out / f"kmf_nb_out{sfx}.json").write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=1))
    (out / f"kmf_nb_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    if not sfx: (out / "kmf_nb_trades.json").write_text(json.dumps(trades, ensure_ascii=False))
    print(json.dumps(meta, ensure_ascii=False)); print("판", len(rows))

def cut_test(cuts=("20260401", "20260504", "20260701", "20260803", "20260915", "20261001")):   # 평가 첫날(03-06) 뒤
    """자르기 시험: 자른 날 앞까지 날별 손익(지연 0 · 1 · 2 · 모든 판)이 전체 자료로 셈한 값과 같아야 함 · 자른 셈은 새 프로세스(처음부터 안 읽음)."""
    import subprocess
    full = json.loads((ROOT / "research/kmf_nb_daily.json").read_text()); bad = 0; res = {}
    for c in cuts:
        env = dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_cut")
        subprocess.run([sys.executable, __file__], env=env, check=True, capture_output=True)
        part = json.loads((ROOT / "research/kmf_nb_daily_cut.json").read_text())
        n = sum(1 for k in full for dl in full[k] for d, v in part[k][dl].items() if d < c and abs(v - full[k][dl][d]) > 1e-9); res[c] = n; bad += n
    (ROOT / "research/kmf_nb_daily_cut.json").unlink(missing_ok=True); (ROOT / "research/kmf_nb_out_cut.json").unlink(missing_ok=True)
    print("자르기 시험 다른 칸", res, "모두", bad); return bad

if __name__ == "__main__":
    if sys.argv[1:] == ["--cut-test"]: sys.exit(1 if cut_test() else 0)
    main()
