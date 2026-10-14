"""GATE10-0001 — GPT #340 제안 2: 10:00(600분)에 닫힌 RNA로 그날 방향을 고정하면 이후 S3(안 조용한 날)에 도움이 되나 · 같은 158일 개발 진단(후보 · 사전등록 아님).
자료: kmf_nb 원판(입력 해시 = DATA_EXPECT) · 158일(02-19 ~ 10-13) · 지연 0 · 비용 0.04 · CAP 12 · 1계약 · KMF 잣대(장 끝 하루 −15p · 달 제한 없음).
RNA 방향(기존 식 그대로): EMA10 > EMA20 이고 EMA20 4봉 기울기 > 0 → +1 · 반대 → −1 · 아니면 0. 끝 분 ≤ 600인 닫힌 봉만(15분: K.B15 · 30 · 60분: kmf_rlk4.TF).
  60분봉은 09:00 ~ 09:59가 600분에 처음 닫힘. EMA는 앞 날을 이어 받음(그날만의 추세 아님).
게이트 2개(그 이상 없음): G30+60 = 30 · 60분 방향이 같고 0이 아님 · G15+30+60 = 15 · 30 · 60분 모두 같고 0이 아님 → 그 방향을 그날 고정.
  안 조용한 날 S3 신호 중 신호 분 ≥ 600 이고 방향 = 고정 방향인 것만 허용 · 불일치(0 포함)면 그날 S3 쉼 ·
  그날 09:00 ~ 09:59 분 가운데 빠진 분이 있으면(오전 자료 미완결) 게이트 판은 그날 쉼.
대조: 같은 날들에 신호 분 ≥ 600인 S3 전부(게이트 없음 · 오전 미완결 규칙 없음). 조용한 날 R0는 모든 판에서 그대로(참고 H 수준 합계용).
스트레스판: kmf_r0q.execute2(stress=True)(빈 29분을 들고 지나오면 그 안 손절가 도달 가정 · 상태 이어 재생 · 실제 하한 아님).
지지(결과 전 고정 · 게이트마다 · 원판과 스트레스판 둘 다 만족해야 함 · 원정밀도로 판정):
  ① 대조 대비 초과 손익 합 > 0 ② 막힌 대조 거래(대조에 있고 게이트 판에 없는 거래) 손익 합 < 0
  ③ 날별 초과의 5일 덩어리 재표집 합 95% 하한 > 0(158일 순서 · 0 포함 · 2,000번 · random.Random(0)) ④ 초과가 가장 큰 한 날 빼도 > 0.
  작동한(방향이 고정된) 안 조용한 날이 20일 미만이면 WAITING_DATA로 적음. 두 게이트 중 최선 고르기 없음 · 둘 다 보고.
python3 research/kmf_gate10.py → research/kmf_gate10_out.json · _daily.json · --cut-test"""
import sys, os, json, bisect, hashlib, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from kmf_hdd_base import K, R4, Z, DAYS, stat
import kmf_hdd_pre as P, kmf_r0q as Q
T = 600
KEY15 = [(b[0], b[1]) for b in K.B15]

def dir15(d, m):
    i = bisect.bisect_right(KEY15, (d, m)) - 1
    if i < 4: return 0
    e10, e20 = K.E10[i][0], K.E20[i][0]; sl = e20 - K.E20[i - 4][0]
    return 1 if (e10 > e20 and sl > 0) else (-1 if (e10 < e20 and sl < 0) else 0)

def morning_complete(d): return all(m in K.BY[d] for m in range(540, T))

def gate_dir(d, kind):
    if not morning_complete(d): return 0
    a, b = R4.rna_dir(30, d, T), R4.rna_dir(60, d, T)
    if kind == "G30+60": return a if (a != 0 and a == b) else 0
    c = dir15(d, T); return a if (a != 0 and a == b == c) else 0

def sigs(d, kind):
    if Z[d]: return K.sig_r0(d)
    s = [x for x in R4.s3(d) if x[0] >= T]
    if kind == "대조": return s
    g = gate_dir(d, kind); return [x for x in s if g != 0 and x[1] == g]

def main():
    data_sha = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
    if not K.CUT: assert data_sha == P.DATA_EXPECT
    res, daily, logs = {}, {}, {}
    for kind in ("대조", "G30+60", "G15+30+60"):
        for mode in ("원판", "스트레스판"):
            p, lg = {}, {}
            for d in DAYS:
                l = []; p[d] = Q.execute2(d, sigs(d, kind), log=l, stress=(mode == "스트레스판")); lg[d] = l
            daily[f"{kind} {mode}"] = p; logs[(kind, mode)] = lg
    nq = [d for d in DAYS if not Z[d]]
    out = {"meta": {"days": len(DAYS), "first": DAYS[0], "last": DAYS[-1], "nonquiet_days": len(nq), "decision_minute": T, "data_sha256": data_sha, "KMF_CUT": K.CUT,
                    "오전 미완결 안 조용한 날": [d for d in nq if not morning_complete(d)],
                    "code_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ("kmf_gate10.py", "kmf_r0q.py", "kmf_hdd_base.py", "kmf_hdd_pre.py", "kmf_nb.py", "kmf_rlk4.py", "kmf_rl4.py")}}, "판": {}}
    for kind in ("G30+60", "G15+30+60"):
        active = [d for d in nq if gate_dir(d, kind) != 0]
        r = {"작동한 안 조용한 날": len(active), "+1 날": sum(1 for d in active if gate_dir(d, kind) > 0), "−1 날": sum(1 for d in active if gate_dir(d, kind) < 0)}
        ok_all = True
        for mode in ("원판", "스트레스판"):
            p, base = daily[f"{kind} {mode}"], daily[f"대조 {mode}"]; lg, lb = logs[(kind, mode)], logs[("대조", mode)]
            ex = [p[d] - base[d] for d in DAYS]; best = max(range(len(ex)), key=lambda i: ex[i])
            blocked = [t["손익"] for d in DAYS for t in lb[d] if t["신호분"] not in {u["신호분"] for u in lg[d]}]
            raw = {"초과 합": sum(ex), "초과 합 95%": Q.block_ci(ex, stat_fn=sum), "가장 큰 한 날 뺀 초과": sum(ex) - ex[best], "막힌 대조 거래 손익 합": sum(blocked)}
            cond = {"① 초과 합 > 0": raw["초과 합"] > 0, "② 막힌 거래 손익 < 0": raw["막힌 대조 거래 손익 합"] < 0, "③ 95% 하한 > 0": raw["초과 합 95%"][0] > 0, "④ 한 날 빼도 > 0": raw["가장 큰 한 날 뺀 초과"] > 0}
            s = stat(p); sb = stat(base)
            r[mode] = {"H 수준 합(R0 + 게이트 S3)": s["합"], "MDD": s["MDD"], "최악": s["최악"], "앞반": s["앞반"], "뒤반": s["뒤반"], "대조 합": sb["합"], "대조 MDD": sb["MDD"],
                       "안 조용한 날만 합": round(sum(p[d] for d in nq), 2), "대조 안 조용한 날만 합": round(sum(base[d] for d in nq), 2),
                       "초과 합": round(raw["초과 합"], 2), "초과 합 95%": [round(x, 2) for x in raw["초과 합 95%"]], "가장 큰 한 날 뺀 초과": round(raw["가장 큰 한 날 뺀 초과"], 2),
                       "막힌 대조 거래 수": len(blocked), "막힌 대조 거래 손익 합": round(raw["막힌 대조 거래 손익 합"], 2),
                       "새로 생긴 거래 수": sum(1 for d in DAYS for t in lg[d] if t["신호분"] not in {u["신호분"] for u in lb[d]}),
                       "−15 넘은 날": sum(1 for v in p.values() if v < -15.0), "원정밀도": raw, "조건": cond}
            ok_all = ok_all and all(cond.values())
        r["판정"] = "WAITING_DATA" if len(active) < 20 else ("지지" if ok_all else "지지 안 됨")
        out["판"][kind] = r
    sfx = os.getenv("KMF_OUT_SUFFIX", "")
    (HERE / f"kmf_gate10_out{sfx}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (HERE / f"kmf_gate10_daily{sfx}.json").write_text(json.dumps({k: {d: round(v, 4) for d, v in p.items()} for k, p in daily.items()}, ensure_ascii=False))
    for k, r in out["판"].items():
        print(k, r["판정"], {x: r[x] for x in ("작동한 안 조용한 날", "+1 날", "−1 날")}, {m: {x: r[m][x] for x in ("안 조용한 날만 합", "대조 안 조용한 날만 합", "초과 합", "초과 합 95%", "가장 큰 한 날 뺀 초과", "막힌 대조 거래 손익 합", "MDD", "대조 MDD")} for m in ("원판", "스트레스판")})

def cut_test(cuts=("20260415", "20260701", "20260901")):
    full = json.loads((HERE / "kmf_gate10_daily.json").read_text()); bad = 0
    for c in cuts:
        subprocess.run([sys.executable, __file__], env=dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_cut"), check=True, capture_output=True)
        part = json.loads((HERE / "kmf_gate10_daily_cut.json").read_text())
        bad += sum(1 for k in full for d, v in part[k].items() if d < c and abs(v - full[k][d]) > 1e-9)
    for f in ("kmf_gate10_daily_cut.json", "kmf_gate10_out_cut.json"): (HERE / f).unlink(missing_ok=True)
    (HERE / "kmf_gate10_cut.out").write_text(json.dumps({"cuts": list(cuts), "다른 칸": bad}, ensure_ascii=False)); print("자르기 다른 칸", bad); return bad

if __name__ == "__main__":
    if sys.argv[1:] == ["--cut-test"]: sys.exit(1 if cut_test() else 0)
    main()
