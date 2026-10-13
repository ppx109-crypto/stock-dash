"""RLK-0008 — GPT 가설 2(#331): 중복 팔을 없앤 두 팔 Thompson 샘플링 · 148일 개발 진단(독립 검증 아님 · RLK-0007 20일에 합류 안 함).
계산 전에 이 파일을 커밋으로 고정합니다(설정 2 · 씨앗 10 · 결과 보고 안 바꿈).
팔: S3(T2 s1.5 + 15분 기울기 ÷ ATR ≤ 0.5) · R0(15분 이격 되돌림 L10 k1.0) · 게이트 없음 · 상태 없음. H(손 합침)는 팔이 아니라 대조.
방식 이름(GPT #333): 평균을 0으로 축소한 정규 근사 Thompson 방식(완전한 베이즈 사후 아님 · 표본 분산을 끼워 넣음 · 두꺼운 꼬리 · 날 사이 의존 미반영 · θ > 0은 기대값 > 0 증명 아님).
보상 모형(연속 p 손익 · 승률 모형 아님): 팔마다 평균 = 정규 근사 · 사전 N(0, ·) · 사전 강도 n0(가짜 관측 n0개의 0)
  사후 평균 = 합 ÷ (n + n0) · 사후 표준편차 = s ÷ √(n + n0) · s = 그 팔 지난 손익 표준편차(n ≥ 2 · 최소 1.0) · n < 2이면 s = 10.0
고르기: 날마다 두 팔에서 θ ~ N(사후 평균, 사후 표준편차) 하나씩 뽑음(난수는 날마다 늘 2개 소비 · 워밍업 포함 · 자르기에도 같은 흐름) → θ 큰 팔 · 둘 다 θ ≤ 0이면 쉼(공통 사전 고정 규칙) · θ가 정확히 같으면 ARMS 순서대로 S3(max의 첫 값) · 장부의 θ · 사후 평균 · 표준편차는 원정밀도.
배움: 고른 뒤 그날 두 팔 손익을 모두 더함(전체 정보 재생 · 시장 충격 없음 가정). 워밍업: 148일 중 앞 20일 배움만(대조도 같은 날부터).
설정: n0 {5, 20} = 2 · 씨앗 0 ~ 9(10개 전부 공개 · 평균 · 표준편차로 보고 · 좋은 씨앗 고르지 않음).
대조: 늘 H · 늘 S3 · 늘 R0 · 쉼.
집중도 · 판정(GPT #333 보완 · 결과 보기 전 고정): 설정 · 지연마다 채점 128일 Δ[d] = TS[d] − H[d]를 씨앗별로 공개.
  씨앗 평균 Δ가 가장 큰 5일(동률은 이른 날 먼저)을 공통으로 빼고 남은 날 평균 Δ 합을 보고. 씨앗별 Δ 합 · 양수 씨앗 수 · 최소 · 중앙 · 최대 공개.
  '평균 Δ 합 ≤ 0 또는 공통 상위 5일 뺀 평균 Δ 합 ≤ 0'이면 그 지연은 '개선 지지 안 됨'. 세 지연(0 · 1 · 2) 모두 통과해야 설정이 '개선 지지(개발 진단)'.
  씨앗 10개는 같은 시장 128일을 다시 돌린 것이라 독립 표본 1,280일이 아님. 통과해도 후보 채택 · 독립 시험 아님.
  사후 평균 < 0인 팔을 고른 날 수와 그 손익(탐색 비용)도 씨앗 · 지연마다 보고.
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
            arms[a] = {"n": n, "사후 평균": pm, "사후 표준편차": ps, "θ": th[a]}
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
    S = EVAL[WARM:]; conc = []
    for n0 in (5, 20):
        per = []; delta = {dl: [] for dl in (0, 1, 2)}
        for seed in range(10):
            label = f"TS n0{n0} 씨앗{seed}"; ss = []; daily[label] = {}; negs = []
            for dl in (0, 1, 2):
                p, pick, dec = run(Ps[dl], n0, seed); ss.append(summ(p)); delta[dl].append({d: p[d] - Ps[dl]["H"][d] for d in S})
                neg = [d for d in S if pick[d] != "쉼" and dec[d]["팔"][pick[d]]["사후 평균"] < 0]; negs.append([len(neg), round(sum(p[d] for d in neg), 2)])
                daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}; decs.setdefault(label, {})[str(dl)] = dec
                if dl == 0:
                    picks = dict(collections.Counter(pick[d] for d in EVAL[WARM:])); top = sorted(EVAL, key=lambda d: -p[d])[:5]; ex5 = round(sum(p[d] for d in EVAL if d not in top), 2)
            r = {"판": label, "합": [s["합"] for s in ss], "MDD": [s["MDD"] for s in ss], "장 끝 하루 최악": [s["최악"] for s in ss], "TS−H 합": [round(ss[k]["합"] - hsum[k], 2) for k in range(3)],
                 "고른 팔(지연0 · 채점 날)": picks, "상위5일 뺀 합(지연0)": ex5, "사후 평균<0 팔 고른 날 · 손익(지연별)": negs}
            rows.append(r); per.append(r)
        cj = {"설정": f"TS n0{n0}", "지연별": {}}
        for dl in (0, 1, 2):
            sums = [round(sum(x.values()), 4) for x in delta[dl]]; md = {d: st.mean(x[d] for x in delta[dl]) for d in S}
            top5 = sorted(S, key=lambda d: (-md[d], d))[:5]; mean_sum = sum(md.values()); ex = sum(v for d, v in md.items() if d not in top5)
            ok = mean_sum > 0 and ex > 0
            cj["지연별"][str(dl)] = {"씨앗별 Δ 합": sums, "평균 Δ 합": round(mean_sum, 4), "양수 씨앗 수": sum(1 for v in sums if v > 0), "최소 · 중앙 · 최대": [min(sums), round(st.median(sums), 4), max(sums)],
                                    "공통 상위 5일": {d: round(md[d], 4) for d in top5}, "공통 상위 5일 뺀 평균 Δ 합": round(ex, 4), "판정": "통과" if ok else "개선 지지 안 됨",
                                    "날별 평균 Δ": {d: round(md[d], 4) for d in S}}
        cj["설정 판정"] = "개선 지지(개발 진단)" if all(v["판정"] == "통과" for v in cj["지연별"].values()) else "개선 지지 안 됨"; conc.append(cj)
        rows.append({"판": f"TS n0{n0} 씨앗 10개 요약", "TS−H 합 평균": [round(st.mean(x["TS−H 합"][k] for x in per), 2) for k in range(3)], "TS−H 합 표준편차": [round(st.stdev(x["TS−H 합"][k] for x in per), 2) for k in range(3)],
                     "TS−H > 0 씨앗 수": [sum(1 for x in per if x["TS−H 합"][k] > 0) for k in range(3)], "합 평균": [round(st.mean(x["합"][k] for x in per), 2) for k in range(3)], "MDD 평균": [round(st.mean(x["MDD"][k] for x in per), 2) for k in range(3)]})
    for label, a in (("대조 늘 H(손 합침)", "H"), ("대조 늘 S3(게이트 없음)", "S3"), ("대조 늘 R0(게이트 없음)", "R0"), ("대조 쉼(0)", "쉼")):
        ss = []; daily[label] = {}
        for dl in (0, 1, 2):
            p = {d: (Ps[dl][a][d] if (i >= WARM and a != "쉼") else 0.0) for i, d in enumerate(EVAL)}; ss.append(summ(p)); daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}
        rows.append({"판": label, "합": [s["합"] for s in ss], "MDD": [s["MDD"] for s in ss], "장 끝 하루 최악": [s["최악"] for s in ss]})
    sfx = os.getenv("KMF_OUT_SUFFIX", ""); out = ROOT / "research"
    hsh = lambda q: hashlib.sha256(q.read_bytes()).hexdigest()
    meta = {"eval_days": len(EVAL), "warm_days": WARM, "scored_from": EVAL[WARM], "scored_days": len(S), "DEV_END(이날부터 안 읽음)": K.DEV_END, "KMF_CUT": K.CUT,
            "code_sha256": {f"research/{f}": hsh(ROOT / "research" / f) for f in ("kmf_ts.py", "kmf_rl4.py", "kmf_rlk4.py", "kmf_nb.py")},
            "data_sha256": {str(q.relative_to(ROOT)): hsh(q) for q in (K.MINI, K.FUT, K.F1M)}}
    (out / f"kmf_ts_out{sfx}.json").write_text(json.dumps({"meta": meta, "rows": rows, "집중도 판정": conc}, ensure_ascii=False, indent=1))
    (out / f"kmf_ts_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    (out / f"kmf_ts_decisions{sfx}.json").write_text(json.dumps(decs, ensure_ascii=False))
    for r in rows:
        if "요약" in r["판"] or r["판"].startswith("대조"): print(json.dumps(r, ensure_ascii=False))
    for c in conc: print(c["설정"], c["설정 판정"], {dl: {k: v[k] for k in ("평균 Δ 합", "공통 상위 5일 뺀 평균 Δ 합", "양수 씨앗 수", "판정")} for dl, v in c["지연별"].items()})
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
