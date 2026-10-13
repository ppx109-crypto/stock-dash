"""HDD-0001 round 2 — H 낙폭 줄이기 계산 전 잠금(개발 진단 · 같은 158일 · 후보 · 사전등록 아님).
가족 3개 × 설정 4 = 12판 + H 대조. 가족 사이 조합은 만들지 않음. 체결 지연 0 · 비용 0.04 · CAP 12 · 엔진 kmf_nb.execute 그대로(신호만 바꿈).
 가족 GA(GPT 가설 A · R0 역추세 감속 확인): R0 신호 시각에 닫힌 30분봉(· 60분봉) 정규화 기울기 |ΔEMA20(4봉)| ÷ ATR가 바로 앞 봉보다 작을 때만 진입.
   설정: k ∈ {1.0, 1.25} × 확인 ∈ {30분만, 30분 + 60분 모두}.
 가족 GB(GPT 가설 B · S3 다중시간 합치 + 과열 밴드): S3 신호 중 닫힌 30분(· 60분) RNA 방향(kmf_rlk4.rna_dir)이 같은 방향이고,
   신호 봉 15분 종가의 EMA10 이격 ÷ ATR ≤ 밴드일 때만. 설정: 합치 ∈ {15+30, 15+30+60} × 밴드 ∈ {1.5, 2.0}.
 가족 GM(클로드 · R0 최대 보유): R0 정리 분 = min(15:15, 신호 봉 끝 + 15 × N분)(목표 · 손절 그대로). 설정 N ∈ {3, 4, 5, 6}.
   (탐색 장부: 서브에이전트가 같은 158일에서 N 2 · 3 · 4를 이미 봄 → 공개)
개발 승격(결과 전 고정 · GPT #337): 합 ≥ 476.0 · MDD ≥ −36.1 · 비용 뒤 하루 < −15 없음 · 앞 · 뒤 반 모두 > 0 · 같은 가족 인접 설정 2개 이상 통과 ·
   한 날 효과 < 50%(그 판의 한 날 손익만 H에 바꿔 넣었을 때 얻는 MDD 개선의 최대가 전체 개선의 50% 이상이면 탈락).
   인접: GA·GB는 2 × 2 격자의 가로 · 세로 이웃 · GM은 N ± 1.
   여럿 통과면 MDD가 가장 얕은 가족 → 그 가족에서 합이 큰 통과 설정 하나만 새 자료 후보(사용자 승인 뒤).
python3 research/kmf_hdd_pre.py → research/kmf_hdd_pre_out.json · _daily.json · --cut-test"""
import sys, os, json, bisect, hashlib, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from kmf_hdd_base import K, R4, R, Z, DAYS, stat, quiet
TF = R4.TF

def nslope(n, d, m, back=0):
    """닫힌 n분봉(끝 분 ≤ m) 기준 back봉 앞의 |EMA20 4봉 변화| ÷ ATR · 셀 수 없으면 None."""
    B, E10, E20, keys = TF[n]; i = bisect.bisect_right(keys, (d, m)) - 1 - back
    if i < 4 or E20[i][1] <= 0: return None
    return abs(E20[i][0] - E20[i - 4][0]) / E20[i][1]

def decel(n, d, m):
    a, b = nslope(n, d, m), nslope(n, d, m, 1)
    return a is not None and b is not None and a < b

J15 = R4.J15
def stretch15(d, m):
    j = J15[(d, m)]; e, a = K.E10[j]
    return abs(K.B15[j][5] - e) / a if a > 0 else 99.0

def sig_h(d, fam=None, cfg=None):
    if Z[d]:
        k = cfg["k"] if fam == "GA" else 1.0
        sig = K.sig_r0(d, k=k)
        if fam == "GA": sig = [x for x in sig if decel(30, d, x[0]) and (cfg["tf"] == "30" or decel(60, d, x[0]))]
        if fam == "GM": sig = [(m0, sd_, tg, st_, min(915, m0 + 15 * cfg["N"])) for (m0, sd_, tg, st_, _) in sig]
        return sig
    sig = R4.s3(d)
    if fam == "GB":
        sig = [x for x in sig if R4.rna_dir(30, d, x[0]) == x[1] and (cfg["tf"] == "15+30" or R4.rna_dir(60, d, x[0]) == x[1]) and stretch15(d, x[0]) <= cfg["band"]]
    return sig

FAM = {"GA": [{"k": k, "tf": tf} for k in (1.0, 1.25) for tf in ("30", "30+60")],
       "GB": [{"tf": tf, "band": b} for tf in ("15+30", "15+30+60") for b in (1.5, 2.0)],
       "GM": [{"N": n} for n in (3, 4, 5, 6)]}
def label(f, c): return f + " " + " ".join(f"{k}{v}" for k, v in c.items())
def neighbors(f, i):
    if f == "GM": return [j for j in (i - 1, i + 1) if 0 <= j < 4]
    r, c = divmod(i, 2); return [rr * 2 + cc for rr, cc in ((1 - r, c), (r, 1 - c))]

def one_day_share(p, h):
    base = stat(h)["MDD"]; full = stat(p)["MDD"] - base
    if full <= 0: return None
    best = max(stat({**h, d: p[d]})["MDD"] - base for d in DAYS if p[d] != h[d]) if any(p[d] != h[d] for d in DAYS) else 0.0
    return round(best / full, 3)

def main():
    H = {d: K.execute(d, sig_h(d)) for d in DAYS}
    if not K.CUT: assert abs(sum(H.values()) - 595.0) < 0.05, sum(H.values())
    rows = {"H(대조)": {**stat(H), "통과": None}}; daily = {"H(대조)": {d: round(v, 4) for d, v in H.items()}}; res = {}
    for f, cfgs in FAM.items():
        for i, c in enumerate(cfgs):
            p = {d: K.execute(d, sig_h(d, f, c)) for d in DAYS}; s = stat(p)
            s["−15 넘은 날"] = sum(1 for v in p.values() if v < -15.0); s["한 날 효과"] = one_day_share(p, H)
            s["기본 통과"] = (s["합"] >= 476.0 and s["MDD"] >= -36.1 and s["−15 넘은 날"] == 0 and s["앞반"] > 0 and s["뒤반"] > 0
                          and s["한 날 효과"] is not None and s["한 날 효과"] < 0.5)
            res[(f, i)] = s; rows[label(f, c)] = s; daily[label(f, c)] = {d: round(v, 4) for d, v in p.items()}
    for (f, i), s in res.items():
        s["통과"] = s["기본 통과"] and sum(1 for j in neighbors(f, i) if res[(f, j)]["기본 통과"]) >= 1 and \
            sum(1 for j in [i] + neighbors(f, i) if res[(f, j)]["기본 통과"]) >= 2
    passed = [(f, i) for (f, i), s in res.items() if s["통과"]]
    pick = None
    if passed:
        fam_best = min({f for f, _ in passed}, key=lambda f: -max(res[(f, i)]["MDD"] for g, i in passed if g == f))
        i = max((i for g, i in passed if g == fam_best), key=lambda i: res[(fam_best, i)]["합"]); pick = label(fam_best, FAM[fam_best][i])
    sfx = os.getenv("KMF_OUT_SUFFIX", "")
    meta = {"days": len(DAYS), "first": DAYS[0], "last": DAYS[-1], "trials_this_lock": 12,
            "code_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ("kmf_hdd_pre.py", "kmf_hdd_base.py", "kmf_nb.py", "kmf_rlk4.py", "kmf_rl4.py")}}
    (HERE / f"kmf_hdd_pre_out{sfx}.json").write_text(json.dumps({"meta": meta, "rows": rows, "통과": [label(f, FAM[f][i]) for f, i in passed], "새 자료 후보(사용자 승인 뒤)": pick}, ensure_ascii=False, indent=1))
    (HERE / f"kmf_hdd_pre_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    for k, s in rows.items(): print(k, {x: s.get(x) for x in ("합", "MDD", "최악", "앞반", "뒤반", "−15 넘은 날", "한 날 효과", "기본 통과", "통과")})
    print("통과", [label(f, FAM[f][i]) for f, i in passed], "후보", pick)

def cut_test(cuts=("20260401", "20260701", "20260915", "20261001")):
    full = json.loads((HERE / "kmf_hdd_pre_daily.json").read_text()); bad = 0
    for c in cuts:
        subprocess.run([sys.executable, __file__], env=dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_cut"), check=True, capture_output=True)
        part = json.loads((HERE / "kmf_hdd_pre_daily_cut.json").read_text())
        bad += sum(1 for k in full for d, v in part[k].items() if d < c and abs(v - full[k][d]) > 1e-9)
    for f in ("kmf_hdd_pre_daily_cut.json", "kmf_hdd_pre_out_cut.json"): (HERE / f).unlink(missing_ok=True)
    (HERE / "kmf_hdd_pre_cut.out").write_text(json.dumps({"cuts": list(cuts), "다른 칸": bad}, ensure_ascii=False)); print("자르기 다른 칸", bad); return bad

if __name__ == "__main__":
    if sys.argv[1:] == ["--cut-test"]: sys.exit(1 if cut_test() else 0)
    main()
