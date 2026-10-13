"""RLK-0005 RL-3 — 보수형 날 고르기 문맥 밴딧(사용자 2026-10-13 "모든걸 RL로 진행" · GPT #325 · #328 권고형: 쉼 허용 · 하한 신뢰값으로 고름).
계산 전에 이 파일을 커밋으로 고정합니다(설정 4개 · 결과 보고 안 바꿈).
팔(고정 규칙 · 아무 날에나 돌 수 있음): 쉼 / S3(T2 s1.5 + 15분 기울기 ÷ ATR ≤ 0.5) / R0(15분 이격 되돌림 L10 k1.0).
상태(장 전에 앎): A = 자체 조용함(q0.6 · 앞 날들과만 견줌) 2칸 · B = A × 전날 효율(|종가 − 시가| ÷ 폭 < 0.5 / ≥ 0.5) 4칸.
배움: 그날 끝난 뒤 모든 팔의 그날 손익을 그 상태 칸에 넣음(팔끼리 서로 영향 없음 · 시장 충격 없음 가정 · 오늘 고를 때는 어제까지만 봄).
고르기: 칸마다 팔 하한 = 평균 − z × 표준편차 ÷ √n(n ≥ 10일 때만 · 아니면 후보 아님) → 하한 최대 팔 · 그 하한이 0 이하이면 쉼.
설정: 상태 {A, B} × z {0.5, 1.0} = 4. 평가: 148일(kmf_nb EVAL) 가운데 앞 20일은 배움만(쉼) · 지연 0 / 1 / 2는 팔 손익을 그 지연으로 셈.
대조: 늘 S3 · 늘 R0 · 손으로 정한 합침(조용 → R0 · 조용하지 않음 → S3) · 쉼.
python3 research/kmf_rl3.py → research/kmf_rl3_out.json · _daily.json · --cut-test"""
import json, os, sys, math, collections, hashlib, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "research"))
import kmf_nb as K, kmf_rlk4 as R4
Z = K.quiet_state(0.6); EVAL = [d for d in K.DAYS if d in K.quiet_state(0.4)]; WARM = 20
ARMS = {"S3": R4.s3, "R0": R4.r0}
def eff_prev(d):
    i = K.DAYS.index(d); p = K.DAYS[i - 1]; x = K.BY[p]; hi = max(r[3] for r in x.values()); lo = min(r[4] for r in x.values())
    o = x[min(x)][2]; c = x[max(x)][5]; return 0 if (hi - lo) <= 0 or abs(c - o) / (hi - lo) < 0.5 else 1
def state(d, kind): return (Z[d],) if kind == "A" else (Z[d], eff_prev(d))
def arm_pnl(dl): return {a: {d: K.execute(d, f(d), delay=dl) for d in EVAL} for a, f in ARMS.items()}
def run(P, kind, z):
    hist = collections.defaultdict(list); pick = {}; pnl = {}
    for i, d in enumerate(EVAL):
        s = state(d, kind); choice = "쉼"
        if i >= WARM:
            best = None
            for a in ARMS:
                h = hist[(s, a)]
                if len(h) < 10: continue
                lcb = st.mean(h) - z * st.stdev(h) / math.sqrt(len(h))
                if lcb > 0 and (best is None or lcb > best[0]): best = (lcb, a)
            if best: choice = best[1]
        pick[d] = choice; pnl[d] = P[choice][d] if choice != "쉼" else 0.0
        for a in ARMS: hist[(s, a)].append(P[a][d])          # 그날 끝난 뒤 배움
    return pnl, pick
def summ(p): return K.summ(p, EVAL, {d: 1 for d in EVAL if p[d] != 0})
def main():
    rows, daily = [], {}
    Ps = {dl: arm_pnl(dl) for dl in (0, 1, 2)}
    cfgs = {f"RL-3 상태{k} z{z}": (k, z) for k in ("A", "B") for z in (0.5, 1.0)}
    for label, (k, z) in cfgs.items():
        ss = []; daily[label] = {}
        for dl in (0, 1, 2):
            p, pick = run(Ps[dl], k, z); ss.append(summ(p)); daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}
            if dl == 0: picks = dict(collections.Counter(pick.values()))
        rows.append({"판": label, "합": [s["합"] for s in ss], "MDD": [s["MDD"] for s in ss], "장 끝 하루 최악": [s["최악"] for s in ss], "앞(~05-29)": [s["앞(~05-29)"] for s in ss], "뒤(06-01~)": [s["뒤(06-01~)"] for s in ss], "고른 팔(지연0)": picks})
    ctl = {"대조 늘 S3": lambda d: "S3", "대조 늘 R0": lambda d: "R0", "대조 손 합침(조용 → R0 · 아님 → S3)": lambda d: "R0" if Z[d] else "S3"}
    for label, ch in ctl.items():
        ss = []; daily[label] = {}
        for dl in (0, 1, 2):
            p = {d: (Ps[dl][ch(d)][d] if i >= WARM else 0.0) for i, d in enumerate(EVAL)}; ss.append(summ(p)); daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}
        rows.append({"판": label, "합": [s["합"] for s in ss], "MDD": [s["MDD"] for s in ss], "장 끝 하루 최악": [s["최악"] for s in ss], "앞(~05-29)": [s["앞(~05-29)"] for s in ss], "뒤(06-01~)": [s["뒤(06-01~)"] for s in ss]})
    sfx = os.getenv("KMF_OUT_SUFFIX", ""); out = ROOT / "research"
    meta = {"eval_days": len(EVAL), "warm_days": WARM, "scored_from": EVAL[WARM], "kmf_nb_sha256": hashlib.sha256((ROOT / "research/kmf_nb.py").read_bytes()).hexdigest(), "kmf_rlk4_sha256": hashlib.sha256((ROOT / "research/kmf_rlk4.py").read_bytes()).hexdigest()}
    (out / f"kmf_rl3_out{sfx}.json").write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=1))
    (out / f"kmf_rl3_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    for r in rows: print(json.dumps(r, ensure_ascii=False))
def cut_test(cuts=("20260504", "20260701", "20260803", "20260915", "20261001")):
    import subprocess
    full = json.loads((ROOT / "research/kmf_rl3_daily.json").read_text()); res = {}
    for c in cuts:
        subprocess.run([sys.executable, __file__], env=dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_cut"), check=True, capture_output=True)
        part = json.loads((ROOT / "research/kmf_rl3_daily_cut.json").read_text())
        res[c] = sum(1 for k in full for dl in full[k] for d, v in part[k][dl].items() if d < c and abs(v - full[k][dl][d]) > 1e-9)
    for f in ("kmf_rl3_daily_cut.json", "kmf_rl3_out_cut.json"): (ROOT / "research" / f).unlink(missing_ok=True)
    print("자르기 시험 다른 칸", res, "모두", sum(res.values())); return sum(res.values())
if __name__ == "__main__":
    if sys.argv[1:] == ["--cut-test"]: sys.exit(1 if cut_test() else 0)
    main()
