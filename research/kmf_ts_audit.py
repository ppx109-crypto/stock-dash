"""RLK-0008 독립 검산(감사) — kmf_ts.run()을 부르지 않고 docstring 규칙만으로 다시 셈.
검사 1: 날마다 n · 사후 평균 · 사후 표준편차 · θ · 선택 · 채택 손익을 장부(_decisions.json) · 날별(_daily.json)과 대조.
검사 2: 장부 '반사실'이 kmf_rl4.arm_pnl과 같은지 · '늘 H' 합(599.56 / 557.05 / 576.4).
검사 3: 집중도 판정 다시 셈. 검사 4: 사후 평균 < 0 팔 고른 날 · 손익.
검사 5: 미래 흔들기(자른 날부터 팔 손익 × −3 + 잡음) → 자른 날 앞 θ · 선택 · 손익 한 칸도 안 바뀌는지.
검사 6: meta 해시 = 실제 파일 해시 · 잠근 커밋(f5877b22)의 kmf_ts.py 해시.
python3 research/kmf_ts_audit.py → research/kmf_ts_audit.out(JSON)"""
import json, sys, math, random, hashlib, subprocess, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "research"))
import kmf_rl4 as R                       # 팔 손익과 EVAL · WARM만 씀(kmf_ts는 안 부름)
EVAL, WARM, Zq = R.EVAL, R.WARM, R.Z; S = EVAL[WARM:]
A2 = ("S3", "R0"); TOL = 1e-9
def sd_(h):                               # 표본 표준편차(두 번 훑기 · statistics와 따로 셈)
    m = math.fsum(h) / len(h); return math.sqrt(math.fsum((x - m) ** 2 for x in h) / (len(h) - 1))
def ts(P, n0, seed):
    g = random.Random(seed); H = {"S3": [], "R0": []}; out = {}
    for i, d in enumerate(EVAL):
        row = {}
        for a in A2:
            h = H[a]; n = len(h); s = max(sd_(h), 1.0) if n >= 2 else 10.0
            pm = math.fsum(h) / (n + n0); ps = s / math.sqrt(n + n0); row[a] = (n, pm, ps, g.gauss(pm, ps))
        t3, t0 = row["S3"][3], row["R0"][3]
        b = "S3" if t3 >= t0 else "R0"
        c = "쉼" if i < WARM or row[b][3] <= 0 else b
        out[d] = (row, c, 0.0 if c == "쉼" else P[c][d])
        for a in A2: H[a].append(P[a][d])
    return out
def close(x, y): return abs(x - y) <= TOL * max(1.0, abs(x), abs(y))
def main():
    rep = {}
    Ps = {dl: R.arm_pnl(dl) for dl in (0, 1, 2)}
    led = json.loads((ROOT / "research/kmf_ts_decisions.json").read_text()); daily = json.loads((ROOT / "research/kmf_ts_daily.json").read_text())
    out = json.loads((ROOT / "research/kmf_ts_out.json").read_text())
    rows = {r["판"]: r for r in out["rows"]}
    # 검사 1 · 2 · 4
    c1 = {"비교 칸": 0, "n 다름": 0, "사후 평균 다름": 0, "사후 표준편차 다름": 0, "θ 다름": 0, "선택 다름": 0, "채택 손익 다름(장부)": 0, "워밍업 표시 다름": 0, "날별 손익 다름(daily)": 0, "날 수 다름": 0}
    c2 = {"반사실 비교 칸": 0, "반사실 다름": 0}; c4 = {"비교": 0, "다름": 0}
    RES = {}
    for n0 in (5, 20):
        for seed in range(10):
            lab = f"TS n0{n0} 씨앗{seed}"; negs = []
            for dl in (0, 1, 2):
                r = ts(Ps[dl], n0, seed); RES[(n0, seed, dl)] = r; L = led[lab][str(dl)]; D = daily[lab][str(dl)]
                if len(L) != len(EVAL) or len(D) != len(EVAL): c1["날 수 다름"] += 1
                for i, d in enumerate(EVAL):
                    row, c, p = r[d]; l = L[d]; c1["비교 칸"] += 1
                    for a in A2:
                        n, pm, ps, th = row[a]; la = l["팔"][a]
                        c1["n 다름"] += la["n"] != n; c1["사후 평균 다름"] += not close(la["사후 평균"], pm)
                        c1["사후 표준편차 다름"] += not close(la["사후 표준편차"], ps); c1["θ 다름"] += not close(la["θ"], th)
                    c1["선택 다름"] += l["선택"] != c; c1["채택 손익 다름(장부)"] += l["채택 손익"] != round(p, 4)
                    c1["워밍업 표시 다름"] += l["워밍업"] != (i < WARM); c1["날별 손익 다름(daily)"] += D[d] != round(p, 4)
                    for a in ("S3", "R0", "H"):
                        c2["반사실 비교 칸"] += 1; c2["반사실 다름"] += l["반사실"][a] != round(Ps[dl][a][d], 4)
                neg = [d for d in S if r[d][1] != "쉼" and r[d][0][r[d][1]][1] < 0]
                negs.append([len(neg), round(sum(r[d][2] for d in neg), 2)])
            c4["비교"] += 1; c4["다름"] += negs != rows[lab]["사후 평균<0 팔 고른 날 · 손익(지연별)"]
            c4.setdefault("다시 셈 값", {})[lab] = negs
    # H 정의(H = 조용 → R0 · 아니면 S3) 와 늘 H 합
    hdef = sum(1 for dl in (0, 1, 2) for d in EVAL if Ps[dl]["H"][d] != (Ps[dl]["R0"][d] if Zq[d] else Ps[dl]["S3"][d]))
    hs = [round(math.fsum(Ps[dl]["H"][d] for d in S), 2) for dl in (0, 1, 2)]
    c2.update({"H 정의 어긋난 칸": hdef, "늘 H 합(다시 셈)": hs, "늘 H 합(보고)": rows["대조 늘 H(손 합침)"]["합"], "늘 H 합 기대(599.56/557.05/576.4)와 다름": int(hs != [599.56, 557.05, 576.4]),
               "늘 S3 · 늘 R0 합(다시 셈)": [[round(math.fsum(Ps[dl][a][d] for d in S), 2) for dl in (0, 1, 2)] for a in A2]})
    # 행 합 · TS−H 합 검산(덤)
    c1x = {"합 다름": 0, "TS−H 합 다름": 0}
    for (n0, seed, dl), r in RES.items():
        lab = f"TS n0{n0} 씨앗{seed}"; sm = round(math.fsum(r[d][2] for d in EVAL), 2)
        c1x["합 다름"] += sm != rows[lab]["합"][dl]; c1x["TS−H 합 다름"] += round(sm - math.fsum(Ps[dl]["H"][d] for d in S), 2) != rows[lab]["TS−H 합"][dl]
    rep["검사1 결정 다시 셈"] = {**c1, **c1x}; rep["검사2 반사실 · 대조"] = c2
    # 검사 3 집중도
    c3 = {"비교 항목": 0, "다름": 0, "다른 곳": []}; conc = {c["설정"]: c for c in out["집중도 판정"]}
    for n0 in (5, 20):
        cj = conc[f"TS n0{n0}"]; verd = []
        for dl in (0, 1, 2):
            dl_ = [{d: RES[(n0, s, dl)][d][2] - Ps[dl]["H"][d] for d in S} for s in range(10)]
            sums = [round(math.fsum(x.values()), 4) for x in dl_]; md = {d: math.fsum(x[d] for x in dl_) / 10 for d in S}
            top5 = sorted(S, key=lambda d: (-md[d], d))[:5]; ms = math.fsum(md.values()); ex = math.fsum(v for d, v in md.items() if d not in top5)
            v = "통과" if ms > 0 and ex > 0 else "개선 지지 안 됨"; verd.append(v); rp = cj["지연별"][str(dl)]
            chk = {"씨앗별 Δ 합": sums == rp["씨앗별 Δ 합"], "평균 Δ 합": abs(round(ms, 4) - rp["평균 Δ 합"]) <= 1e-4,
                   "양수 씨앗 수": sum(1 for x in sums if x > 0) == rp["양수 씨앗 수"], "최소 · 중앙 · 최대": [min(sums), round(st.median(sums), 4), max(sums)] == rp["최소 · 중앙 · 최대"],
                   "공통 상위 5일(날짜 · 순서)": top5 == list(rp["공통 상위 5일"]), "공통 상위 5일 값": all(abs(round(md[d], 4) - rp["공통 상위 5일"][d]) <= 1e-4 for d in top5),
                   "상위 5일 뺀 합": abs(round(ex, 4) - rp["공통 상위 5일 뺀 평균 Δ 합"]) <= 1e-4, "판정": v == rp["판정"],
                   "날별 평균 Δ": all(abs(round(md[d], 4) - rp["날별 평균 Δ"][d]) <= 1e-4 for d in S) and len(rp["날별 평균 Δ"]) == len(S)}
            for k, ok in chk.items():
                c3["비교 항목"] += 1
                if not ok: c3["다름"] += 1; c3["다른 곳"].append(f"n0{n0} 지연{dl} {k}")
            c3.setdefault("다시 셈", {})[f"n0{n0} 지연{dl}"] = {"평균 Δ 합": round(ms, 4), "상위5 뺀": round(ex, 4), "양수 씨앗": sum(1 for x in sums if x > 0), "판정": v}
        sv = "개선 지지(개발 진단)" if all(x == "통과" for x in verd) else "개선 지지 안 됨"
        c3["비교 항목"] += 1
        if sv != cj["설정 판정"]: c3["다름"] += 1; c3["다른 곳"].append(f"n0{n0} 설정 판정")
    rep["검사3 집중도 판정"] = c3; rep["검사4 사후 평균<0 팔"] = {k: v for k, v in c4.items() if k != "다시 셈 값"}
    # 검사 5 미래 흔들기
    c5 = {}
    for cut in ("20260504", "20260701", "20260915"):
        k = {"자른 날 앞 비교 칸": 0, "앞 다름": 0, "자른 날 뒤 바뀐 칸(검정력 확인 · 0보다 커야 함)": 0}
        for dl in (0, 1, 2):
            g = random.Random(int(cut) * 10 + dl)
            Q = {a: {d: (v * -3 + g.gauss(0, 20) if d >= cut else v) for d, v in Ps[dl][a].items()} for a in ("S3", "R0", "H")}
            for n0 in (5, 20):
                for seed in range(10):
                    a0, b0 = RES[(n0, seed, dl)], ts(Q, n0, seed)
                    for d in EVAL:
                        if d < cut: k["자른 날 앞 비교 칸"] += 1; k["앞 다름"] += a0[d] != b0[d]
                        else: k["자른 날 뒤 바뀐 칸(검정력 확인 · 0보다 커야 함)"] += a0[d][1:] != b0[d][1:]
        c5[cut] = k
    rep["검사5 미래 흔들기"] = c5
    # 검사 6 해시
    h = lambda b: hashlib.sha256(b).hexdigest(); m = out["meta"]; c6 = {"비교": 0, "다름": 0, "다른 파일": []}
    for f, v in {**m["code_sha256"], **m["data_sha256"]}.items():
        c6["비교"] += 1
        if h((ROOT / f).read_bytes()) != v: c6["다름"] += 1; c6["다른 파일"].append(f)
    locked = h(subprocess.run(["git", "-C", str(ROOT), "show", "f5877b22:research/kmf_ts.py"], capture_output=True, check=True).stdout)
    c6["잠근 커밋 f5877b22의 kmf_ts.py = meta 해시"] = locked == m["code_sha256"]["research/kmf_ts.py"]
    c6["의존 파일이 잠근 커밋과 같음"] = {f: h(subprocess.run(["git", "-C", str(ROOT), "show", f"f5877b22:research/{f}"], capture_output=True, check=True).stdout) == m["code_sha256"][f"research/{f}"] for f in ("kmf_rl4.py", "kmf_rlk4.py", "kmf_nb.py")}
    rep["검사6 해시"] = c6
    # 설계 참고: 왜 H보다 못한가
    ref = {}
    for dl in (0, 1, 2):
        P = Ps[dl]; q = [d for d in S if Zq[d]]; nq = [d for d in S if not Zq[d]]
        f = lambda a, ds: round(math.fsum(P[a][d] for d in ds), 2)
        same = [sum(1 for d in S if RES[(n0, s, dl)][d][1] == ("R0" if Zq[d] else "S3")) / len(S) for n0 in (5, 20) for s in range(10)]
        last = RES[(5, 0, dl)][EVAL[-1]][0]
        ref[f"지연{dl}"] = {"조용한 날 수 · 아닌 날 수": [len(q), len(nq)], "조용한 날 S3 · R0 합": [f("S3", q), f("R0", q)], "조용하지 않은 날 S3 · R0 합": [f("S3", nq), f("R0", nq)],
                          "TS 선택이 H와 같은 팔인 날 비율(20판 평균)": round(st.mean(same), 3),
                          "마지막 날 사후(n0 5 · 씨앗0) S3 · R0 평균 / 표준편차": [[round(last[a][1], 3), round(last[a][2], 3)] for a in A2]}
    rep["설계 참고(H 대비 지는 까닭)"] = ref
    tot = sum(v for k, v in rep["검사1 결정 다시 셈"].items() if k != "비교 칸") + c2["반사실 다름"] + c2["H 정의 어긋난 칸"] + c2["늘 H 합 기대(599.56/557.05/576.4)와 다름"] + c3["다름"] + c4["다름"] + sum(x["앞 다름"] for x in c5.values()) + c6["다름"] + (not c6["잠근 커밋 f5877b22의 kmf_ts.py = meta 해시"]) + sum(not x for x in c6["의존 파일이 잠근 커밋과 같음"].values())
    rep["어긋남 모두"] = int(tot)
    (ROOT / "research/kmf_ts_audit.out").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps(rep, ensure_ascii=False, indent=1))
if __name__ == "__main__": main()
