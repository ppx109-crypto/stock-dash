"""별도 클로드 검사 담당(RLK-0006): 어느 날 k부터 팔 손익 · 상태를 흔들어도 그 앞 날 결정이 그대로인지. 쓰는 법: python3 research/kmf_rl4_audit_future.py <저장소 뿌리>"""
"""RL-4 감사: 미래 흔들기 시험 + 독립 재계산. 사용: python3 future_test.py <저장소 뿌리>"""
import sys, json, math, random, copy, statistics as st, collections
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve(); sys.path.insert(0, str(ROOT / "research"))
import kmf_rl4 as R, kmf_nb as K
E, W = R.EVAL, R.WARM
print("평가 날", len(E), "워밍업", W, "채점 시작", E[W])
Ps = {dl: R.arm_pnl(dl) for dl in (0, 1, 2)}
# (A) H 팔 = 조용 → R0 · 아니면 S3 (지연 0/1/2)
bad = sum(1 for dl in Ps for d in E if Ps[dl]["H"][d] != (Ps[dl]["R0"][d] if R.Z[d] else Ps[dl]["S3"][d]))
print("A. H 팔 정의 어긋난 칸", bad, "| 조용 날 수", sum(R.Z[d] for d in E))
# (B) 조용함 Z: 어느 날부터 하루 폭(RNGP)을 흔들어도 그 앞 Z는 그대로
orig = dict(K.RNGP); zb = 0
for k in (30, 60, 100, 140):
    cut = K.DAYS[k]; rng = random.Random(k)
    for d in K.DAYS: K.RNGP[d] = orig[d]
    for d in K.DAYS[k:]: K.RNGP[d] = orig[d] * rng.uniform(0.1, 10)
    K.MED20.clear(); K.MED20.update({d: st.median(K.RNGP[q] for q in K.DAYS[i-20:i]) for i, d in enumerate(K.DAYS) if i >= 20})
    Z2 = K.quiet_state(0.6); zb += sum(1 for d in R.Z if d < cut and Z2.get(d) != R.Z[d])
    # 그날(cut) 자체의 폭만 흔들어도 그날 Z는 그대로여야(그날 폭을 안 씀)
for d in K.DAYS: K.RNGP[d] = orig[d]
K.MED20.clear(); K.MED20.update({d: st.median(K.RNGP[q] for q in K.DAYS[i-20:i]) for i, d in enumerate(K.DAYS) if i >= 20})
print("B. 미래 하루 폭 흔든 뒤 앞 Z 달라진 날", zb, "| 원복 확인", K.quiet_state(0.6) == R.Z)
# (C) 독립 재구현으로 결정 장부 · 손익 비교
def mine(P, kind, z):
    hist = collections.defaultdict(list); out = {}
    for i, d in enumerate(E):
        s = "-" if kind == "N" else R.Z[d]; best, cands = None, []
        for a in ("S3", "R0", "H"):
            h = hist[(s, a)]
            if i >= W and len(h) >= 10:
                sc = round(st.mean(h) - z * st.stdev(h) / math.sqrt(len(h)), 4)
                if sc > 0: cands.append((sc, a))
        if cands:
            m = max(c[0] for c in cands); top = [a for sc, a in cands if sc == m]
            ch = top[0] if len(top) == 1 else "쉼"
        else: ch = "쉼"
        out[d] = (ch, 0.0 if ch == "쉼" else P[ch][d])
        for a in ("S3", "R0", "H"): hist[(s, a)].append(P[a][d])
    return out
dec = json.loads((ROOT / "research/kmf_rl4_decisions.json").read_text()); daily = json.loads((ROOT / "research/kmf_rl4_daily.json").read_text())
cb = ties = 0
for k in ("N", "A"):
    for z in (0.5, 1.0):
        lab = f"RL-4 상태{k} z{z}"
        for dl in (0, 1, 2):
            m = mine(Ps[dl], k, z); L = dec[lab][str(dl)]
            for i, d in enumerate(E):
                if L[d]["선택"] != m[d][0] or abs(daily[lab][str(dl)][d] - round(m[d][1], 4)) > 1e-9 or L[d]["채택 손익"] != round(m[d][1], 4): cb += 1
                if (i < W) != L[d]["워밍업"] or (i < W and L[d]["선택"] != "쉼"): cb += 1
                sc = [v["보수 점수"] for v in L[d]["팔"].values() if v["보수 점수"] is not None and v["보수 점수"] > 0]
                if i >= W and sc and sc.count(max(sc)) > 1: ties += 1
print("C. 결정 장부 · 손익 독립 재구현과 다른 칸", cb, "| 동점으로 쉰 날", ties)
# (D) 대조: EVAL[20]부터만 손익
db = 0
for lab, a in (("대조 늘 H(손 합침)", "H"), ("대조 늘 S3(게이트 없음)", "S3"), ("대조 늘 R0(게이트 없음)", "R0"), ("대조 쉼(0)", "쉼")):
    for dl in (0, 1, 2):
        for i, d in enumerate(E):
            want = 0.0 if (i < W or a == "쉼") else round(Ps[dl][a][d], 4)
            if abs(daily[lab][str(dl)][d] - want) > 1e-9: db += 1
print("D. 대조 판 어긋난 칸", db)
# (E) 미래 흔들기: k번째 날부터 팔 손익 · 상태를 흔들어도 앞 결정 · 손익 · 장부 그대로
tot = 0
for k in (20, 21, 30, 50, 75, 100, 128, 147):
    if k >= len(E): continue
    cut = E[k]; diff = 0
    for dl in (0, 1, 2):
        P2 = copy.deepcopy(Ps[dl]); rng = random.Random(k * 10 + dl)
        for d in E[k:]:
            for a in P2: P2[a][d] = rng.uniform(-500, 500)
        Zs = dict(R.Z)
        for d in E[k:]: R.Z[d] = not R.Z[d]          # 미래 상태도 뒤집음
        for kind in ("N", "A"):
            for z in (0.5, 1.0):
                R.Z.clear(); R.Z.update(Zs); a1 = R.run(Ps[dl], kind, z)
                for d in E[k:]: R.Z[d] = not Zs[d]
                a2 = R.run(P2, kind, z)
                diff += sum(1 for d in E[:k] if a1[0][d] != a2[0][d] or a1[1][d] != a2[1][d] or a1[2][d] != a2[2][d])
        R.Z.clear(); R.Z.update(Zs)
    tot += diff; print(f"E. 흔들기 시작 {cut}(k={k}) 앞 날 달라진 칸", diff)
print("E. 모두", tot)
# (F) 요약 줄이 daily에서 다시 나오는지
out = json.loads((ROOT / "research/kmf_rl4_out.json").read_text()); fb = 0
for r in out["rows"]:
    for j, dl in enumerate(("0", "1", "2")):
        p = daily[r["판"]][dl]; s = K.summ(p, E, {})
        fb += (s["합"] != r["합"][j]) + (s["MDD"] != r["MDD"][j]) + (s["최악"] != r["장 끝 하루 최악"][j])
print("F. 요약 줄 재계산 어긋남(일별 4자리 반올림 탓 0.01 차이 가능)", fb, "| meta", out["meta"]["scored_from"], out["meta"]["eval_days"])
