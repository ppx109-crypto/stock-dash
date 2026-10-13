"""RLK-0006 RL-4 — 더 단순한 보수형 밴딧(RL-3에서 칸이 많아 표본이 모자랐던 점을 줄임 · 사용자 2026-10-13 "계속 RL로 진행해").
계산 전에 이 파일을 커밋으로 고정합니다(설정 4개 · 결과 보고 안 바꿈).
팔(고정 규칙 · 게이트 없음 · 모든 날 실행 가능): 쉼 / S3 / R0 / H(손 합침 = 조용 → R0 · 조용하지 않음 → S3 · RLK-0004 게이트 재현).
  팔 정의는 kmf_rl3 · kmf_rlk4 그대로(S3 = T2 s1.5 + 15분 기울기 ÷ ATR ≤ 0.5 · R0 = 15분 이격 되돌림 L10 k1.0).
상태: N = 없음(한 칸 · 문맥 없는 밴딧) · A = 자체 조용함(q0.6) 2칸.
배움 · 고르기 · 동점 · 워밍업은 RL-3과 같음: 그날 끝난 뒤 모든 팔 손익을 그 칸에 넣음(전체 정보 재생) · 보수 점수 = 평균 − z × 표준편차 ÷ √n(n ≥ 10) ·
  점수 최대 팔 · 0 이하면 쉼 · 동점이면 쉼 · 148일 가운데 앞 20일은 배움만. 보수 점수는 통계적 신뢰하한이 아님.
설정: 상태 {N, A} × z {0.5, 1.0} = 4. 대조: 늘 H(손 합침) · 늘 S3 · 늘 R0 · 쉼(0) · 같은 채점 날(EVAL[20]부터).
결정 장부: research/kmf_rl4_decisions.json(상태 · 팔별 n · 평균 · 표준편차 · 점수 · 선택 · 반사실 · 채택 손익) · 자르기 시험은 손익 + 결정 장부 비교 → research/kmf_rl4_cut.out.
질문: 문맥을 줄인 RL이 손 합침(H)을 '배워서' 따라잡거나 넘는가. H를 팔로 넣었으므로 RL이 H를 고르는 횟수 자체가 결과의 일부.
python3 research/kmf_rl4.py → research/kmf_rl4_out.json · _daily.json · _decisions.json · --cut-test"""
import json, os, sys, math, collections, hashlib, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "research"))
import kmf_nb as K, kmf_rlk4 as R4
Z = K.quiet_state(0.6); EVAL = [d for d in K.DAYS if d in K.quiet_state(0.4)]; WARM = 20
ARMS = ("S3", "R0", "H")
def arm_pnl(dl):
    P = {"S3": {d: K.execute(d, R4.s3(d), delay=dl) for d in EVAL}, "R0": {d: K.execute(d, R4.r0(d), delay=dl) for d in EVAL}}
    P["H"] = {d: (P["R0"][d] if Z[d] else P["S3"][d]) for d in EVAL}
    return P
def state(d, kind): return ("-",) if kind == "N" else (Z[d],)
def run(P, kind, z):
    hist = collections.defaultdict(list); pnl = {}; dec = {}; pick = {}
    for i, d in enumerate(EVAL):
        s = state(d, kind); arms = {}; best = None
        for a in ARMS:
            h = hist[(s, a)]; n = len(h)
            sc = round(st.mean(h) - z * st.stdev(h) / math.sqrt(n), 4) if n >= 10 else None
            arms[a] = {"n": n, "평균": round(st.mean(h), 4) if n else None, "표준편차": round(st.stdev(h), 4) if n >= 2 else None, "보수 점수": sc, "n≥10": n >= 10}
            if i >= WARM and sc is not None and sc > 0:
                if best is None or sc > best[0]: best = (sc, a)
                elif sc == best[0]: best = (sc, "쉼")
        choice = best[1] if best else "쉼"; pick[d] = choice; pnl[d] = P[choice][d] if choice != "쉼" else 0.0
        dec[d] = {"상태": list(s), "워밍업": i < WARM, "팔": arms, "선택": choice, "반사실": {a: round(P[a][d], 4) for a in ARMS}, "채택 손익": round(pnl[d], 4)}
        for a in ARMS: hist[(s, a)].append(P[a][d])          # 고른 뒤 그날 손익을 배움
    return pnl, pick, dec
def summ(p): return K.summ(p, EVAL, {d: 1 for d in EVAL if p[d] != 0})
def row(label, ss, extra=None):
    r = {"판": label, "합": [s["합"] for s in ss], "MDD": [s["MDD"] for s in ss], "장 끝 하루 최악": [s["최악"] for s in ss], "앞(~05-29)": [s["앞(~05-29)"] for s in ss], "뒤(06-01~)": [s["뒤(06-01~)"] for s in ss]}
    if extra: r.update(extra)
    return r
def main():
    rows, daily, decs = [], {}, {}
    Ps = {dl: arm_pnl(dl) for dl in (0, 1, 2)}
    for k in ("N", "A"):
        for z in (0.5, 1.0):
            label = f"RL-4 상태{k} z{z}"; ss = []; daily[label] = {}
            for dl in (0, 1, 2):
                p, pick, dec = run(Ps[dl], k, z); ss.append(summ(p)); daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}; decs.setdefault(label, {})[str(dl)] = dec
                if dl == 0: picks = dict(collections.Counter(pick[d] for d in EVAL[WARM:]))
            rows.append(row(label, ss, {"고른 팔(지연0 · 채점 날)": picks}))
    for label, a in (("대조 늘 H(손 합침)", "H"), ("대조 늘 S3(게이트 없음)", "S3"), ("대조 늘 R0(게이트 없음)", "R0"), ("대조 쉼(0)", "쉼")):
        ss = []; daily[label] = {}
        for dl in (0, 1, 2):
            p = {d: (Ps[dl][a][d] if (i >= WARM and a != "쉼") else 0.0) for i, d in enumerate(EVAL)}; ss.append(summ(p)); daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}
        rows.append(row(label, ss))
    sfx = os.getenv("KMF_OUT_SUFFIX", ""); out = ROOT / "research"
    meta = {"eval_days": len(EVAL), "warm_days": WARM, "scored_from": EVAL[WARM], "kmf_nb_sha256": hashlib.sha256((ROOT / "research/kmf_nb.py").read_bytes()).hexdigest(), "kmf_rlk4_sha256": hashlib.sha256((ROOT / "research/kmf_rlk4.py").read_bytes()).hexdigest()}
    (out / f"kmf_rl4_out{sfx}.json").write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=1))
    (out / f"kmf_rl4_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    (out / f"kmf_rl4_decisions{sfx}.json").write_text(json.dumps(decs, ensure_ascii=False))
    for r in rows: print(json.dumps(r, ensure_ascii=False))
def cut_test(cuts=("20260504", "20260701", "20260803", "20260915", "20261001")):
    import subprocess
    full = json.loads((ROOT / "research/kmf_rl4_daily.json").read_text()); fdec = json.loads((ROOT / "research/kmf_rl4_decisions.json").read_text()); res = {}
    for c in cuts:
        subprocess.run([sys.executable, __file__], env=dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_cut"), check=True, capture_output=True)
        part = json.loads((ROOT / "research/kmf_rl4_daily_cut.json").read_text()); pdec = json.loads((ROOT / "research/kmf_rl4_decisions_cut.json").read_text())
        nd = {k: sum(1 for d in full[k]["0"] if d < c) for k in full}; npd = {k: len(part[k]["0"]) for k in part}
        res[c] = {"손익 다른 칸": sum(1 for k in full for dl in full[k] for d, v in part[k][dl].items() if d < c and abs(v - full[k][dl][d]) > 1e-9),
                  "결정 장부 다른 날": sum(1 for k in fdec for dl in fdec[k] for d, v in pdec[k][dl].items() if d < c and v != fdec[k][dl][d]),
                  "날 수 다른 판": sum(1 for k in full if nd[k] != npd.get(k))}
    for f in ("kmf_rl4_daily_cut.json", "kmf_rl4_out_cut.json", "kmf_rl4_decisions_cut.json"): (ROOT / "research" / f).unlink(missing_ok=True)
    tot = sum(sum(v.values()) for v in res.values())
    (ROOT / "research/kmf_rl4_cut.out").write_text(json.dumps({"cuts": res, "모두": tot}, ensure_ascii=False))
    print("자르기 시험", res, "모두", tot); return tot
if __name__ == "__main__":
    if sys.argv[1:] == ["--cut-test"]: sys.exit(1 if cut_test() else 0)
    main()
