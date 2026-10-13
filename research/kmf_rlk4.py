"""RLK-0004 — GPT #328 설정 상한 6개 중 사용자 승인(2026-10-13 "해")으로 계산하는 3개(1 · 2 · 4는 계산 전 서술표에서 H1 반증으로 뺌).
규칙은 결과 보기 전에 고정(이 파일 첫 커밋):
  S3: T2 s1.5 · 조용하지 않은 날(q0.6) + 신호 봉의 |15분 EMA20 4봉 기울기| ÷ ATR ≤ 0.5 일 때만(경계 0.5는 이미 결과를 본 탐색 경계 · GPT 명시)
  S5: R0 · 자체 조용 q0.6 · 신호 봉 끝 분에 끝나 있던 마지막 30분봉과 60분봉 RNA가 **둘 다** R0가 거스르는 15분 이동 방향(= −진입 방향)이면 그 신호 건너뜀
  S6: 같은 R0 · 30분 · 60분 중 **하나라도** 그 방향이면 건너뜀
  RNA 방향: EMA10 > EMA20 이고 EMA20 4봉 기울기 > 0 → 위 · 반대 → 아래 · 그 밖 평평(kmf_nb_diag2와 같은 정의)
기준선: T2 s1.5 · q0.6 / R0 · q0.6(RLK-0002 round 2 그대로). 체결 · 날짜 · 잣대는 kmf_nb.execute · 148일 · 지연 0 / 1 / 2 · 장 끝 −15p.
python3 research/kmf_rlk4.py → research/kmf_rlk4_out.json · _daily.json · _trades.json · --cut-test"""
import json, os, sys, bisect, collections, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "research"))
import kmf_nb as K
TF = {}
for n in (30, 60):
    B = K.bars(n); E10 = K.ind(B, 10); E20 = K.ind(B, 20); TF[n] = (B, E10, E20, [(b[0], b[1]) for b in B])
def rna_dir(n, d, m):
    B, E10, E20, keys = TF[n]; i = bisect.bisect_right(keys, (d, m)) - 1
    if i < 4: return 0
    e10, e20 = E10[i][0], E20[i][0]; sl = e20 - E20[i - 4][0]
    return 1 if (e10 > e20 and sl > 0) else (-1 if (e10 < e20 and sl < 0) else 0)
J15 = {(K.B15[j][0], K.B15[j][1]): j for j in range(len(K.B15))}
def slope15(d, m):
    j = J15[(d, m)]; a = K.E10[j][1]
    return abs(K.E20[j][0] - K.E20[j - 4][0]) / a if a else 99.0
Z = K.quiet_state(0.6); EVAL = [d for d in K.DAYS if d in K.quiet_state(0.4)]
def t2(d): return K.sig_t(d, "T2", s=1.5)
def s3(d): return [s for s in t2(d) if slope15(d, s[0]) <= 0.5]
def r0(d): return K.sig_r0(d)
def s5(d): return [s for s in r0(d) if not (rna_dir(30, d, s[0]) == -s[1] and rna_dir(60, d, s[0]) == -s[1])]
def s6(d): return [s for s in r0(d) if not (rna_dir(30, d, s[0]) == -s[1] or rna_dir(60, d, s[0]) == -s[1])]
PLANS = {"기준 T2 s1.5 · 조용하지 않은 날(q0.6)": (False, t2), "S3 T2 + 15분 기울기/ATR ≤ 0.5": (False, s3),
         "기준 R0 · 자체 조용 q0.6": (True, r0), "S5 R0 − 30 · 60 둘 다 거스르는 방향이면 건너뜀": (True, s5), "S6 R0 − 30 · 60 하나라도 거스르는 방향이면 건너뜀": (True, s6)}
def main():
    rows, daily, trades = [], {}, {}
    for label, (quiet, f) in PLANS.items():
        ss = []; daily[label] = {}
        for dl in (0, 1, 2):
            log = []; p = {}; ntr = collections.Counter()
            for d in EVAL:
                if Z.get(d) is not quiet: p[d] = 0.0; continue
                n0 = len(log); p[d] = K.execute(d, f(d), delay=dl, log=log); ntr[d] = len(log) - n0
            ss.append(K.summ(p, EVAL, ntr)); daily[label][str(dl)] = {d: round(p[d], 4) for d in EVAL}
            trades.setdefault(label, {})[str(dl)] = log
        top = sorted(EVAL, key=lambda d: -daily[label]["0"][d])[:5]
        rows.append({"판": label, "합": [s["합"] for s in ss], "MDD": [s["MDD"] for s in ss], "장 끝 하루 최악": [s["최악"] for s in ss],
                     "앞(~05-29)": [s["앞(~05-29)"] for s in ss], "뒤(06-01~)": [s["뒤(06-01~)"] for s in ss], "거래일": [s["거래일"] for s in ss], "거래수": [s["거래수"] for s in ss],
                     "상위5일 합(지연0)": round(sum(daily[label]["0"][d] for d in top), 2), "상위5일 뺀 합(지연0)": round(sum(daily[label]["0"].values()) - sum(daily[label]["0"][d] for d in top), 2)})
    sfx = os.getenv("KMF_OUT_SUFFIX", ""); out = ROOT / "research"
    meta = {"eval_days": len(EVAL), "eval_first": EVAL[0], "eval_last": EVAL[-1], "kmf_nb_sha256": hashlib.sha256((ROOT / "research/kmf_nb.py").read_bytes()).hexdigest()}
    (out / f"kmf_rlk4_out{sfx}.json").write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=1))
    (out / f"kmf_rlk4_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    if not sfx: (out / "kmf_rlk4_trades.json").write_text(json.dumps(trades, ensure_ascii=False))
    for r in rows: print(json.dumps(r, ensure_ascii=False))
def cut_test(cuts=("20260401", "20260504", "20260701", "20260803", "20260915", "20261001")):
    import subprocess
    full = json.loads((ROOT / "research/kmf_rlk4_daily.json").read_text()); res = {}
    for c in cuts:
        subprocess.run([sys.executable, __file__], env=dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_cut"), check=True, capture_output=True)
        part = json.loads((ROOT / "research/kmf_rlk4_daily_cut.json").read_text())
        res[c] = sum(1 for k in full for dl in full[k] for d, v in part[k][dl].items() if d < c and abs(v - full[k][dl][d]) > 1e-9)
    for f in ("kmf_rlk4_daily_cut.json", "kmf_rlk4_out_cut.json"): (ROOT / "research" / f).unlink(missing_ok=True)
    print("자르기 시험 다른 칸", res, "모두", sum(res.values())); return sum(res.values())
if __name__ == "__main__":
    if sys.argv[1:] == ["--cut-test"]: sys.exit(1 if cut_test() else 0)
    main()
