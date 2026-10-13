"""RLK-0008 — GPT 가설 2(#331): 중복 팔을 없앤 두 팔 Thompson 샘플링 · 148일 개발 진단(독립 검증 아님 · RLK-0007 20일에 합류 안 함).
계산 전에 이 파일을 커밋으로 고정합니다(설정 2 · 씨앗 10 · 결과 보고 안 바꿈).
팔: S3(T2 s1.5 + 15분 기울기 ÷ ATR ≤ 0.5) · R0(15분 이격 되돌림 L10 k1.0) · 게이트 없음 · 상태 없음. H(손 합침)는 팔이 아니라 대조.
보상 모형(연속 p 손익 · 승률 모형 아님): 팔마다 평균의 사후 = 정규 근사 · 사전 N(0, ·) · 사전 강도 n0(가짜 관측 n0개의 0)
  사후 평균 = 합 ÷ (n + n0) · 사후 표준편차 = s ÷ √(n + n0) · s = 그 팔 지난 손익 표준편차(n ≥ 2 · 최소 1.0) · n < 2이면 s = 10.0
고르기: 날마다 두 팔에서 θ ~ N(사후 평균, 사후 표준편차) 하나씩 뽑음(난수는 날마다 늘 2개 소비 · 워밍업 포함 · 자르기에도 같은 흐름) → θ 큰 팔 · 둘 다 θ ≤ 0이면 쉼(공통 사전 고정 규칙).
배움: 고른 뒤 그날 두 팔 손익을 모두 더함(전체 정보 재생 · 시장 충격 없음 가정). 워밍업: 148일 중 앞 20일 배움만(대조도 같은 날부터).
설정: n0 {5, 20} = 2 · 씨앗 0 ~ 9(10개 전부 공개 · 평균 · 표준편차로 보고 · 좋은 씨앗 고르지 않음).
대조: 늘 H · 늘 S3 · 늘 R0 · 쉼. 판정 보조: 씨앗별 (TS − H) 합의 평균 · 양수 씨앗 수 · 상위 5일 뺀 합.
결정 장부: research/kmf_ts_decisions.json(씨앗 · 지연 · 날마다 팔별 n · 사후 평균 · 사후 표준편차 · θ · 선택 · 반사실 · 채택 손익) · 자르기 시험 → research/kmf_ts_cut.out.
python3 research/kmf_ts.py → research/kmf_ts_out.json · _daily.json · _decisions.json · --cut-test"""
import json, os, sys, math, random, collections, hashlib, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "research"))
import kmf_nb as K, kmf_rl4 as R
EVAL, WARM, Z = R.EVAL, R.WARM, R.Z
ARMS = ("S3", "R0")
def run(P, n0, seed):
    rng = random.Random(seed); hist = {a: [] for a in ARMS}; pnl = {}; dec = {}; pick = {}
    for i, d in enumerate(EVAL):
        arms = {}; th = {}
        for a in ARMS:
            h = hist[a]; n = len(h); s = max(st.stdev(h), 1.0) if n >= 2 else 10.0
            pm = sum(h) / (n + n0); ps = s / math.sqrt(n + n0); th[a] = rng.gauss(pm, ps)
            arms[a] = {"n": n, "사후 평균": round(pm, 4), "사후 표준편차": round(ps, 4), "θ": round(th[a], 4)}
        best = max(ARMS, key=lambda a: th[a])
        choice = "쉼" if (i < WARM or th[best] <= 0) else best
        pick[d] = choice; pnl[d] = P[choice][d] if choice != "쉼" else 0.0
        dec[d] = {"워밍업": i < WARM, "팔": arms, "선택": choice, "반사실": {a: round(P[a][d], 4) for a in ARMS + ("H",)}, "채택 손익": round(pnl[d], 4)}
        for a in ARMS: hist[a].append(P[a][d])
    return pnl, pick, dec
def summ(p): return K.summ(p, EVAL, {d: 1 for d in EVAL if p[d] != 0})
def main():
    Ps = {dl: R.arm_pnl(dl) for dl in (0, 1, 2)}
    rows, daily, decs = [], {}, {}
    hsum = {dl: sum(Ps[dl]["H"][d] for d in EVAL[WARM:]) for dl in (0, 1, 2)}
    for n0 in (5, 20):
        per = []
        for seed in range(10):
            label = f"TS n0{n0} 씨앗{seed}"; ss = []; daily[label] = {}
            for dl in (0, 1, 2):
                p, pick, dec = run(Ps[dl], n0, seed); ss.append(summ(p)); daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}; decs.setdefault(label, {})[str(dl)] = dec
                if dl == 0:
                    picks = dict(collections.Counter(pick[d] for d in EVAL[WARM:])); top = sorted(EVAL, key=lambda d: -p[d])[:5]; ex5 = round(sum(p[d] for d in EVAL if d not in top), 2)
            r = {"판": label, "합": [s["합"] for s in ss], "MDD": [s["MDD"] for s in ss], "장 끝 하루 최악": [s["최악"] for s in ss], "TS−H 합": [round(ss[k]["합"] - hsum[k], 2) for k in range(3)],
                 "고른 팔(지연0 · 채점 날)": picks, "상위5일 뺀 합(지연0)": ex5}
            rows.append(r); per.append(r)
        rows.append({"판": f"TS n0{n0} 씨앗 10개 요약", "TS−H 합 평균": [round(st.mean(x["TS−H 합"][k] for x in per), 2) for k in range(3)], "TS−H 합 표준편차": [round(st.stdev(x["TS−H 합"][k] for x in per), 2) for k in range(3)],
                     "TS−H > 0 씨앗 수": [sum(1 for x in per if x["TS−H 합"][k] > 0) for k in range(3)], "합 평균": [round(st.mean(x["합"][k] for x in per), 2) for k in range(3)], "MDD 평균": [round(st.mean(x["MDD"][k] for x in per), 2) for k in range(3)]})
    for label, a in (("대조 늘 H(손 합침)", "H"), ("대조 늘 S3(게이트 없음)", "S3"), ("대조 늘 R0(게이트 없음)", "R0"), ("대조 쉼(0)", "쉼")):
        ss = []; daily[label] = {}
        for dl in (0, 1, 2):
            p = {d: (Ps[dl][a][d] if (i >= WARM and a != "쉼") else 0.0) for i, d in enumerate(EVAL)}; ss.append(summ(p)); daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}
        rows.append({"판": label, "합": [s["합"] for s in ss], "MDD": [s["MDD"] for s in ss], "장 끝 하루 최악": [s["최악"] for s in ss]})
    sfx = os.getenv("KMF_OUT_SUFFIX", ""); out = ROOT / "research"
    meta = {"eval_days": len(EVAL), "warm_days": WARM, "scored_from": EVAL[WARM], "kmf_rl4_sha256": hashlib.sha256((ROOT / "research/kmf_rl4.py").read_bytes()).hexdigest()}
    (out / f"kmf_ts_out{sfx}.json").write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=1))
    (out / f"kmf_ts_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    (out / f"kmf_ts_decisions{sfx}.json").write_text(json.dumps(decs, ensure_ascii=False))
    for r in rows:
        if "요약" in r["판"] or r["판"].startswith("대조"): print(json.dumps(r, ensure_ascii=False))
def cut_test(cuts=("20260504", "20260701", "20260803", "20260915", "20261001")):
    import subprocess
    full = json.loads((ROOT / "research/kmf_ts_daily.json").read_text()); fdec = json.loads((ROOT / "research/kmf_ts_decisions.json").read_text()); res = {}
    for c in cuts:
        subprocess.run([sys.executable, __file__], env=dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_cut"), check=True, capture_output=True)
        part = json.loads((ROOT / "research/kmf_ts_daily_cut.json").read_text()); pdec = json.loads((ROOT / "research/kmf_ts_decisions_cut.json").read_text())
        res[c] = {"손익 다른 칸": sum(1 for k in full for dl in full[k] for d, v in part[k][dl].items() if d < c and abs(v - full[k][dl][d]) > 1e-9),
                  "결정 장부 다른 날": sum(1 for k in fdec for dl in fdec[k] for d, v in pdec[k][dl].items() if d < c and v != fdec[k][dl][d]),
                  "날 수 다른 판": sum(1 for k in full if sum(1 for d in full[k]["0"] if d < c) != len(part[k]["0"]))}
    for f in ("kmf_ts_daily_cut.json", "kmf_ts_out_cut.json", "kmf_ts_decisions_cut.json"): (ROOT / "research" / f).unlink(missing_ok=True)
    tot = sum(sum(v.values()) for v in res.values())
    (ROOT / "research/kmf_ts_cut.out").write_text(json.dumps({"cuts": res, "모두": tot}, ensure_ascii=False))
    print("자르기 시험", res, "모두", tot); return tot
if __name__ == "__main__":
    if sys.argv[1:] == ["--cut-test"]: sys.exit(1 if cut_test() else 0)
    main()
