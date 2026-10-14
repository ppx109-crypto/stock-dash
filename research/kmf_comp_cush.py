"""COMP-0002 H1(GPT #344) — P2 v1.3이 그날 더는 진입할 수 없게 된 뒤, P2가 그때까지 번 실현 이익(쿠션) 안에서만 보완 봇이 거래.
입력: research/kmf_p2_done_table.json(비공개 P2 엔진에서 뽑은 파생 표 · 날마다 '끝난 분'(그 분 처리 뒤 앎) · '끝 실현'(= 그날 최종) · '그날 손익').
조건: 끝난 분 < 900(15:00) 이고 끝 실현 ≥ 1.0p인 날만. 보완 신호는 15분봉 끝 m0 > 끝난 분 · 첫 유효 진입 1번(maxn 1) · 15:15(915) 정리 ·
  하루 한도 = 쿠션(엔진 CAP = 끝 실현 · 손절폭 ≤ 쿠션 − 왕복 비용) → 보완 실현 손실 ≤ 쿠션(갭 · 다음 분 체결 초과 가능 · 보장 아님).
판(2 · 고정 규칙 그대로 · 새 문턱 없음): R0 = kmf_nb.sig_r0(k 1.0 · 손절 1.0 ATR · 목표 EMA10) · S3 = kmf_rlk4.s3(T2 손절 1.5 + 15분 기울기/ATR ≤ 0.5).
결합 = P2 그날 손익 + 보완 · 대조 = P2 혼자(같은 날짜 01-08 ~ 10-12). 원판 · 스트레스판(kmf_r0q.execute2 방식 · 빈 29분 9구간).
지지(결과 전 고정 · 원정밀도 · 원판과 스트레스판 둘 다): ① 증분 합 > 0 ② 증분 앞 · 뒤 반(날짜순 n//2) 각각 > 0 ③ 가장 큰 증분 한 날 빼도 > 0
  ④ 결합 날 끝 MDD가 P2 혼자보다 깊지 않음(클로드 개발 조건) ⑤ 결합 장 끝 하루 < −15인 날 0 ⑥ 증분 5일 이동 덩어리 재표집(2,000 · random.Random(0)) 합 95% 하한 > 0
  ⑦ 활성(보완 진입) 날 ≥ 10 — 아니면 WAITING_DATA(표본 부족). 두 판 중 최선 고르기 없음.
python3 research/kmf_comp_cush.py → research/kmf_comp_cush_out.json · _daily.json"""
import sys, os, json, hashlib, random
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import kmf_nb as K, kmf_rlk4 as R4, kmf_r0q as Q, kmf_hdd_pre as P
TAB = json.loads((HERE / "kmf_p2_done_table.json").read_text())
DAYS = [d for d in K.DAYS if "20260108" <= d <= "20261012" and d in TAB]

def comp(d, sigf, stress):
    t = TAB[d]; dm, cush = t["끝난 분"], t["끝 실현"]
    if dm is None or dm >= 900 or cush < 1.0: return 0.0, []
    sig = [s for s in sigf(d) if s[0] > dm]
    if not sig: return 0.0, []
    old = K.CAP; K.CAP = cush
    try:
        lg = []; r = Q.execute2(d, sig[:1], log=lg, stress=stress)   # 첫 유효 신호 1개만
    finally:
        K.CAP = old
    return r, lg

def bci(v, B=2000, L=5):
    rng = random.Random(0); n = len(v); out = []
    for _ in range(B):
        s = []
        while len(s) < n: i = rng.randrange(0, n - L + 1); s += v[i:i + L]
        out.append(sum(s[:n]))
    out.sort(); return [out[int(0.025 * B)], out[int(0.975 * B) - 1]]

def stat(p):
    eq = pk = mdd = 0.0
    for d in DAYS: eq += p[d]; pk = max(pk, eq); mdd = min(mdd, eq - pk)
    return {"합": sum(p[d] for d in DAYS), "MDD": mdd, "최악": min(p[d] for d in DAYS)}

def main():
    data_sha = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
    if not K.CUT: assert data_sha == P.DATA_EXPECT
    p2 = {d: TAB[d]["그날 손익"] for d in DAYS}; out = {"meta": {"days": len(DAYS), "first": DAYS[0], "last": DAYS[-1], "data_sha256": data_sha, "KMF_CUT": K.CUT,
          "쿠션 날(끝난 분 < 900 · 끝 실현 ≥ 1)": sum(1 for d in DAYS if TAB[d]["끝난 분"] is not None and TAB[d]["끝난 분"] < 900 and TAB[d]["끝 실현"] >= 1.0),
          "code_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ("kmf_comp_cush.py", "kmf_p2_done_table.json", "kmf_r0q.py", "kmf_nb.py", "kmf_rlk4.py")}},
          "P2 혼자": {k: round(v, 4) for k, v in stat(p2).items()}, "판": {}}
    daily = {"P2 혼자": p2}
    for name, f in (("R0", lambda d: K.sig_r0(d)), ("S3", lambda d: R4.s3(d))):
        r = {}; ok = True
        for mode in ("원판", "스트레스판"):
            c, logs = {}, {}
            for d in DAYS: c[d], logs[d] = comp(d, f, mode == "스트레스판")
            comb = {d: p2[d] + c[d] for d in DAYS}; inc = [c[d] for d in DAYS]; h = len(DAYS) // 2
            best = max(range(len(inc)), key=lambda i: inc[i]); ci = bci(inc); sc = stat(comb); act = [d for d in DAYS if logs[d]]
            worse = {d: comb[d] for d in DAYS if comb[d] < -15.0}
            over = {d: (c[d], TAB[d]["끝 실현"]) for d in act if -c[d] > TAB[d]["끝 실현"] + 1e-12}
            cond = {"① 증분 > 0": sum(inc) > 0, "② 앞 · 뒤 반 > 0": sum(inc[:h]) > 0 and sum(inc[h:]) > 0, "③ 한 날 빼도 > 0": sum(inc) - inc[best] > 0,
                    "④ MDD 안 깊어짐": sc["MDD"] >= stat(p2)["MDD"], "⑤ −15 나쁜 날 0": not worse, "⑥ 95% 하한 > 0": ci[0] > 0, "⑦ 활성 날 ≥ 10": len(act) >= 10}
            r[mode] = {"결합": {k: round(v, 4) for k, v in sc.items()}, "보완 합": round(sum(inc), 4), "증분 앞 · 뒤 반": [round(sum(inc[:h]), 4), round(sum(inc[h:]), 4)],
                       "한 날 뺀 증분": round(sum(inc) - inc[best], 4), "증분 95%": [round(x, 4) for x in ci], "활성 날": len(act), "이긴 날": sum(1 for d in act if c[d] > 0),
                       "쿠션보다 크게 잃은 날": over, "−15 나쁜 날": worse, "원정밀도": {"증분 합": sum(inc), "95%": ci, "한 날 뺀": sum(inc) - inc[best]}, "조건": cond,
                       "보완 진입 기록": {d: [{k: t[k] for k in ("신호분", "진입분", "정리분", "손익")} for t in logs[d]] for d in act}}
            daily[f"{name} {mode}"] = c
            ok = ok and all(cond.values())
        r["판정"] = "WAITING_DATA" if r["원판"]["활성 날"] < 10 else ("지지" if ok else "지지 안 됨")
        out["판"][name] = r
    sfx = os.getenv("KMF_OUT_SUFFIX", "")
    (HERE / f"kmf_comp_cush_out{sfx}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (HERE / f"kmf_comp_cush_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    print("P2 혼자", out["P2 혼자"])
    for k, r in out["판"].items():
        print(k, r["판정"], {m: {x: r[m][x] for x in ("결합", "보완 합", "증분 앞 · 뒤 반", "한 날 뺀 증분", "증분 95%", "활성 날", "이긴 날", "쿠션보다 크게 잃은 날")} for m in ("원판", "스트레스판")})

if __name__ == "__main__":
    main()
