"""CLEAN-0001 — 깨끗한 자료(분이 빠진 15분봉이 있는 날을 통째로 뺌 · 계약은 달력 근월물)에서 기본 성적 다시 재기.
새 규칙 아님 · 기존 팔(R0 · S3) · H를 그대로 다시 잼. 엔진은 kmf_hdd_fc.load_engine()(잠근 kmf_nb 원문에서 두 줄만 바꾼 사본) 그대로.
체결 지연 0(사용자 2026-10-14) · 비용 0.04 · CAP 12 · 1계약. 조용함 = 원판 식(앞 20일 폭 가운데 값의 순위 ≤ 0.6 · 준비 문턱 10개).
판: R0 매일 · S3 매일 · R0 조용한 날만 · S3 안 조용한 날만 · H(조용 → R0 · 아님 → S3) · 쉼.
보고: 합 · MDD · 최악 · 나쁜 달 · 앞 반 · 뒤 반 · 연속 손실 · 회복 최장 · −15 넘은 날 · 거래한 날 · 달별 손익.
python3 research/kmf_clean_base.py → research/kmf_clean_base_out.json · _daily.json · --cut-test"""
import sys, os, json, hashlib, collections, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import kmf_hdd_fc as FC
K, P = FC.load_engine()
from kmf_hdd_base import DAYS, Z, stat, R4

def plans():
    return {"R0 매일": lambda d: K.sig_r0(d), "S3 매일": lambda d: R4.s3(d),
            "R0 조용한 날만": lambda d: K.sig_r0(d) if Z[d] else [], "S3 안 조용한 날만": lambda d: [] if Z[d] else R4.s3(d),
            "H(조용 R0 · 아님 S3)": lambda d: K.sig_r0(d) if Z[d] else R4.s3(d)}

def main():
    rows, daily = {}, {}
    for name, f in plans().items():
        p = {d: K.execute(d, f(d)) for d in DAYS}; s = stat(p)
        mon = collections.defaultdict(float)
        for d, v in p.items(): mon[d[:6]] += v
        s.update({"−15 넘은 날": sum(1 for v in p.values() if v < -15.0), "거래한 날": sum(1 for v in p.values() if v != 0), "달별": {m: round(v, 1) for m, v in sorted(mon.items())}})
        rows[name] = s; daily[name] = {d: round(v, 4) for d, v in p.items()}
    data_sha = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
    if not K.CUT: assert data_sha == P.DATA_EXPECT
    meta = {"days": len(DAYS), "first": DAYS[0], "last": DAYS[-1], "quiet_days": sum(Z[d] for d in DAYS), "engine_days": len(K.DAYS), "rows_read": len(K.ROWS),
            "excluded_days": sorted(FC.SHORT["detail"]), "data_sha256": data_sha, "KMF_CUT": K.CUT,
            "code_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ("kmf_clean_base.py", "kmf_hdd_fc.py", "kmf_hdd_pre.py", "kmf_hdd_base.py", "kmf_nb.py", "kmf_rlk4.py", "kmf_rl4.py")}}
    sfx = os.getenv("KMF_OUT_SUFFIX", "")
    (HERE / f"kmf_clean_base_out{sfx}.json").write_text(json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=1))
    (HERE / f"kmf_clean_base_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    for k, s in rows.items(): print(k, {x: s[x] for x in ("합", "MDD", "최악", "나쁜달", "앞반", "뒤반", "연속손실", "회복최장", "−15 넘은 날", "거래한 날")})
    print("평가", len(DAYS), DAYS[0], DAYS[-1], "조용", meta["quiet_days"], "뺀 날", meta["excluded_days"])

def cut_test(cuts=("20260415", "20260701", "20260901", "20261001")):
    full = json.loads((HERE / "kmf_clean_base_daily.json").read_text()); bad = 0
    for c in cuts:
        subprocess.run([sys.executable, __file__], env=dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_cut"), check=True, capture_output=True)
        part = json.loads((HERE / "kmf_clean_base_daily_cut.json").read_text())
        bad += sum(1 for k in full for d, v in part[k].items() if d < c and abs(v - full[k][d]) > 1e-9)
    for f in ("kmf_clean_base_daily_cut.json", "kmf_clean_base_out_cut.json"): (HERE / f).unlink(missing_ok=True)
    (HERE / "kmf_clean_base_cut.out").write_text(json.dumps({"cuts": list(cuts), "다른 칸": bad}, ensure_ascii=False)); print("자르기 다른 칸", bad); return bad

if __name__ == "__main__":
    if sys.argv[1:] == ["--cut-test"]: sys.exit(1 if cut_test() else 0)
    main()
