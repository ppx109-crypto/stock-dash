"""RLK-0003 점수 없는 진단표(GPT #328 '먼저 낼 표' · 새 설정 없음 · 문턱 찾기 없음).
고정 판: T2 s1.5 · 조용하지 않은 날(q0.6) / R0 · 자체 조용 q0.6(RLK-0002 round 2 그대로) · 지연 0 · 1 · 2 거래 장부를 다시 만듦.
거래마다: 진입 분 앞에 끝난 마지막 15 · 30 · 60분봉(끝 분 ≤ 진입 분)의 RNA 방향(위 / 아래 / 평평: EMA10 ⋚ EMA20 이고 EMA20 4봉 기울기 같은 부호) ·
기울기 ÷ ATR · 배열 간격 ÷ ATR · 그 봉이 덜 찬 봉인지 · MAE · MFE(1분 고저 · 진입 ~ 정리) · 보유 분 · 그날 몇 번째.
묶음 통계: 거래 수 · 비용 뒤 합 · 평균 · 중앙값 · 승률 · 사유 비율 · 날 단위 재표집 95% 구간(2,000번 · 씨앗 0 · 같은 날 거래는 함께 뽑음).
'신호 방향과 같음'은 R0에서는 R0가 거스르는 15분 이동 방향(= −진입 방향) 기준으로 셈(GPT H3 정의)."""
import json, sys, random, bisect, collections, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "research"))
import kmf_nb as K
TF = {}
for n in (15, 30, 60):
    B = K.B15 if n == 15 else K.bars(n); E10 = K.ind(B, 10); E20 = K.ind(B, 20)
    TF[n] = (B, E10, E20, [(b[0], b[1]) for b in B])
def rna(n, d, m):
    B, E10, E20, keys = TF[n]; i = bisect.bisect_right(keys, (d, m)) - 1
    if i < 4: return None
    e10, a = E10[i]; e20 = E20[i][0]; sl = e20 - E20[i - 4][0]
    dirn = 1 if (e10 > e20 and sl > 0) else (-1 if (e10 < e20 and sl < 0) else 0)
    full = sum(1 for mm in range(B[i][1] - n, B[i][1]) if mm in K.BY[B[i][0]]) == n
    return {"방향": dirn, "기울기/ATR": round(sl / a, 3) if a else None, "간격/ATR": round((e10 - e20) / a, 3) if a else None, "끝분": B[i][1], "날": B[i][0], "덜참": not full}
Z = K.quiet_state(0.6); EVAL = [d for d in K.DAYS if d in K.quiet_state(0.4)]
PLANS = {"T2": (lambda d: Z.get(d) is False, lambda d: K.sig_t(d, "T2", s=1.5)), "R0": (lambda d: Z.get(d) is True, lambda d: K.sig_r0(d))}
def mae_mfe(t):
    x = K.BY[t["d"]]; hi = max(x[m][3] for m in range(t["진입분"], t["정리분"] + 1) if m in x); lo = min(x[m][4] for m in range(t["진입분"], t["정리분"] + 1) if m in x)
    return (round((lo - t["진입가"]) * t["방향"] if t["방향"] > 0 else (t["진입가"] - hi), 2), round((hi - t["진입가"]) if t["방향"] > 0 else (t["진입가"] - lo), 2))
def boot(ts, B=2000):
    by = collections.defaultdict(list)
    for t in ts: by[t["d"]].append(t["손익"])
    days = list(by); R = random.Random(0); vals = []
    if not days: return None
    for _ in range(B):
        s = [v for d in (R.choice(days) for _ in days) for v in by[d]]; vals.append(sum(s) / len(s))
    vals.sort(); return [round(vals[int(0.025 * B)], 2), round(vals[int(0.975 * B)], 2)]
def table(ts):
    if not ts: return {"건": 0}
    v = [t["손익"] for t in ts]; rs = collections.Counter(t["사유"] for t in ts)
    return {"건": len(v), "날": len({t["d"] for t in ts}), "합": round(sum(v), 1), "평균": round(st.mean(v), 2), "중앙값": round(st.median(v), 2), "승률": round(sum(1 for x in v if x > 0) / len(v), 2),
            "사유 비율": {k: round(c / len(v), 2) for k, c in rs.items()}, "평균 MAE": round(st.mean(t["MAE"] for t in ts), 2), "평균 MFE": round(st.mean(t["MFE"] for t in ts), 2),
            "평균 보유 분": round(st.mean(t["정리분"] - t["진입분"] for t in ts), 1), "날 재표집 95%(거래 평균)": boot(ts)}
out = {"계약": {"완결 봉": "끝 분(= 다음 봉 첫 분) ≤ 진입 분인 마지막 봉 · 끝 분에 앎(available_at = 끝 분 시작)", "30 · 60분봉": "kmf_nb.bars(n) · 09:00부터 n분씩 · 15:15(914분)까지 · EMA10 · EMA20 · ATR(봉 폭 EMA14) 날 넘어 이어짐",
               "방향": "위 = EMA10 > EMA20 이고 EMA20 4봉 기울기 > 0 · 아래 = 반대 · 그 밖 평평", "15분": "kmf_nb.B15 · E10 · E20 그대로"}}
for name, (gate, sigf) in PLANS.items():
    out[name] = {}
    for dl in (0, 1, 2):
        ts = []
        for d in EVAL:
            if not gate(d): continue
            log = []; K.execute(d, sigf(d), delay=dl, log=log)
            for k, t in enumerate(log):
                t["몇번째"] = k + 1; t["MAE"], t["MFE"] = mae_mfe(t)
                ref = t["방향"] if name == "T2" else -t["방향"]           # 신호 방향(R0는 거스르는 이동 방향)
                for n in (15, 30, 60):
                    r = rna(n, d, t["진입분"]); t[f"rna{n}"] = r; t[f"일치{n}"] = (None if r is None else ("같음" if r["방향"] == ref else ("반대" if r["방향"] == -ref else "평평")))
                ts.append(t)
        top = set(sorted({t["d"] for t in ts}, key=lambda d: -sum(u["손익"] for u in ts if u["d"] == d))[:5])
        res = {}
        for scope, sel in (("전체", ts), ("상위5일 뺌", [t for t in ts if t["d"] not in top])):
            for half, hs in (("둘 다", sel), ("앞(~05-29)", [t for t in sel if t["d"] < "20260601"]), ("뒤(06-01~)", [t for t in sel if t["d"] >= "20260601"])):
                key = f"{scope} · {half}"; res[key] = {"모두": table(hs)}
                for n in (15, 30, 60):
                    for s in ("같음", "평평", "반대"): res[key][f"{n}분 {s}"] = table([t for t in hs if t[f"일치{n}"] == s])
                res[key]["30 · 60 모두 같음"] = table([t for t in hs if t["일치30"] == "같음" and t["일치60"] == "같음"])
                res[key]["30 · 60 하나라도 같음"] = table([t for t in hs if "같음" in (t["일치30"], t["일치60"])])
                res[key]["첫 거래"] = table([t for t in hs if t["몇번째"] == 1]); res[key]["두 번째"] = table([t for t in hs if t["몇번째"] == 2])
                res[key]["덜 찬 15분봉 위 진입"] = table([t for t in hs if t["rna15"] and t["rna15"]["덜참"]])
        out[name][f"지연{dl}"] = res
(ROOT / "research/kmf_nb_diag2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
for name in ("T2", "R0"):
    for dl in (0, 1, 2):
        r = out[name][f"지연{dl}"]
        for key in ("상위5일 뺌 · 앞(~05-29)", "상위5일 뺌 · 뒤(06-01~)"):
            row = r[key]; f = lambda k: f"{row[k]['건']}건 {row[k].get('합', 0):+.1f}" if row[k]["건"] else "0건"
            print(name, dl, key, "| 모두", f("모두"), "| 30분 같음", f("30분 같음"), "반대", f("30분 반대"), "| 30·60 모두 같음", f("30 · 60 모두 같음"), "| 하나라도 같음", f("30 · 60 하나라도 같음"))
