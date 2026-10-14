"""R0Q-0001 — GPT #339 가설 1 · 2(R0 조용한 날 되돌림) · 원자료 그대로(날 빼지 않음) · 빈 29분 9구간은 '스트레스판'으로 따로.
자료: kmf_nb 원판(입력 해시 = kmf_hdd_pre.DATA_EXPECT) · 평가 158일(02-19 ~ 10-13 · 조용함 준비 문턱 10) · 체결 지연 0 · 비용 0.04 · CAP 12 · 1계약.
잣대(KMF · 사용자 결정): 1계약 장 끝 하루 ≥ −15p · 달 제한 없음 · p-MDD 보고.
스트레스판(GPT #339 이름 · 실제 하한 아님): 빈 29분 구간(HOLES)이 시작될 때 포지션이 열려 있으면 그 구간 안에서 손절가에 닿았다고 보고
  손절가로 정리(갭 체결 초과 없음 가정)하고, 다음 진입은 빈 구간 뒤 첫 분부터 · 실현 손익 · 하루 예산 · 진입 횟수 · 멈춤 상태를 그대로 이어 엔진 안에서 다시 재생.
  빈 구간 안 분에서 진입하는 일은 자료가 없어 원래도 없음. 지표(EMA · ATR) 잔영향은 한계로 남김. 판정은 스트레스판 · 원판은 함께 보고.
가설 1(설정 0): 고정 R0(조용한 날만 · k1.0 · 손절 1.0ATR) — 전체 · 달 하나씩 뺀 9개(날 손익만 뺌 · 지표 다시 안 만듦 · 가장 좋은 달 고르지 않음):
  합 · 평가 날 평균(분모 = 그 판의 평가 날 전체 · 손익 0인 날 포함) · 조용한 날 평균 · 거래 수 ·
  95% 구간 = 평가 날 순서 그대로의 날 손익(0 포함)을 길이 5 이동 덩어리로 다시 뽑는 재표집(2,000번 · random.Random(0) · 덩어리 시작 균등 · 원래 날 수만큼 이어 붙여 자름)의 날 평균 2.5 · 97.5% 점.
가설 2(4판 + 대조): 조용한 날 R0. 그날 첫 R0 거래가 비용 뒤 손실이면, 다음 R0 신호 봉의 닫힌 15분 ATR ÷ 첫 진입 신호 봉 ATR ≥ r 일 때
  막기 ∈ {그 신호만, 그날 남은 R0}. r ∈ {1.25, 1.50}. 다른 것은 그대로. 지지(결과 전 고정 · 스트레스판 기준 · 원판도 보고):
  대조 대비 초과 손익 합 > 0 · 날별 초과의 5일 덩어리 재표집 합 95% 하한 > 0 · 초과가 가장 큰 한 날 빼도 > 0 · 막은 거래(대조에서의 · 원판 거래 기록 기준) 손익 합 < 0.
python3 research/kmf_r0q.py → research/kmf_r0q_out.json · _daily.json · --cut-test"""
import sys, os, json, random, hashlib, subprocess, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from kmf_hdd_base import K, Z, DAYS, stat
import kmf_hdd_pre as P
HOLES = {"20260304": (680, 708), "20260309": (632, 660), "20260608": (544, 572), "20260623": (874, 902), "20260626": (731, 759),
         "20260707": (832, 860), "20260713": (809, 837), "20260728": (614, 642), "20260729": (753, 781)}
J15 = {(K.B15[j][0], K.B15[j][1]): j for j in range(len(K.B15))}
def atr_at(d, m): return K.E10[J15[(d, m)]][1]

def execute2(d, sigs, rule=None, log=None, stress=False):
    """K.execute와 같은 규칙(지연 0 · maxn 2) + rule(state, sig)이 거짓이면 그 신호 건너뜀 · 'stop_day'면 그날 남은 신호 모두 건너뜀.
    거래마다 실제 손절폭 sd와 진입 · 정리 분을 log에 남김."""
    x = K.BY[d]; real = 0.0; cnt = 0; free_at = 0; stopped = False; st = {"trades": [], "first_atr": None, "dead": False}
    for (m0, side, tg, sd, m_exit) in sigs:
        if stopped or cnt >= 2 or K.CAP + real < 3.0: continue
        me = next((mm for mm in range(m0, 935) if mm in x), None)
        if me is None or me < free_at or me >= m_exit: continue
        if st["dead"]: continue
        if rule is not None:
            v = rule(st, (m0, side, tg, sd, m_exit))
            if v == "stop_day": st["dead"] = True; continue
            if v is False: continue
        if st["first_atr"] is None: st["first_atr"] = atr_at(d, m0)
        ent = x[me][2]; sd = min(sd, max(0.5, K.CAP + real - 2 * K.COST)); stop = ent - side * sd; cnt += 1; out = None
        for m in range(me, 935):
            if m not in x: continue
            o, h, l, c = x[m][2], x[m][3], x[m][4], x[m][5]
            if m == me: o = ent
            hole = HOLES.get(d) if stress else None
            if hole and m > hole[1] and me < hole[0]:   # 빈 구간을 들고 지나옴 → 그 안에서(정리 분보다 먼저) 손절가 도달로 봄
                out = (stop, hole[0], hole[1] + 1); break
            if m >= m_exit: out = (o, m, m); break
            if (l <= stop) if side > 0 else (h >= stop): out = (min(o, stop) if side > 0 else max(o, stop), m, m + 1); break
            if tg is not None and ((h >= tg) if side > 0 else (l <= tg)): out = (max(o, tg) if side > 0 else min(o, tg), m, m + 1); break
            if real + side * (c - ent) - 2 * K.COST <= -K.CAP:
                nm = next((mm for mm in range(m + 1, 935) if mm in x), None); out = (x[nm][2] if nm else c, nm or m, 999); stopped = True; break
        if out is None: out = (K.last_close(d), 935, 999)
        r = side * (out[0] - ent) - 2 * K.COST; real += r; free_at = out[2]
        st["trades"].append(r)
        if log is not None: log.append({"d": d, "신호분": m0, "진입분": me, "정리분": out[1], "손절폭": sd, "손익": r})
        if real <= -K.CAP: stopped = True
    return real

def block_ci(v, B=2000, L=5, seed=0, stat_fn=lambda x: sum(x) / len(x)):
    rng = random.Random(seed); n = len(v); out = []
    for _ in range(B):
        s = []
        while len(s) < n: i = rng.randrange(0, n - L + 1); s += v[i:i + L]
        out.append(stat_fn(s[:n]))
    out.sort(); return [round(out[int(0.025 * B)], 4), round(out[int(0.975 * B) - 1], 4)]

def run_plan(rule=None, quiet_only=True):
    orig, adv, logs, nadj = {}, {}, {}, 0
    for d in DAYS:
        if quiet_only and not Z[d]: orig[d] = adv[d] = 0.0; logs[d] = []; continue
        lg = []; orig[d] = execute2(d, K.sig_r0(d), rule, lg); ls = []; adv[d] = execute2(d, K.sig_r0(d), rule, ls, stress=True); nadj += int(abs(adv[d] - orig[d]) > 1e-12); logs[d] = lg
    return orig, adv, logs, nadj

def rule_h2(r, mode):
    def f(st, sig):
        if not st["trades"] or st["trades"][0] >= 0 or st["first_atr"] in (None, 0): return True
        if atr_at(sig_day[0], sig[0]) / st["first_atr"] >= r: return "stop_day" if mode == "그날 남은 R0" else False
        return True
    return f
sig_day = [None]

def main():
    for d in DAYS:   # 재현: 규칙 없음 = K.execute
        assert abs(execute2(d, K.sig_r0(d)) - K.execute(d, K.sig_r0(d))) < 1e-9
    data_sha = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
    if not K.CUT: assert data_sha == P.DATA_EXPECT
    out = {"meta": {"days": len(DAYS), "first": DAYS[0], "last": DAYS[-1], "quiet_days": sum(Z[d] for d in DAYS), "holes": HOLES, "data_sha256": data_sha, "KMF_CUT": K.CUT,
                    "code_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ("kmf_r0q.py", "kmf_hdd_base.py", "kmf_hdd_pre.py", "kmf_nb.py", "kmf_rlk4.py", "kmf_rl4.py")}}}
    daily = {}
    o0, a0, lg0, n0 = run_plan(); daily["R0 대조 원판"] = o0; daily["R0 대조 스트레스"] = a0
    # 가설 1
    h1 = {}
    for nm, p in (("원판", o0), ("스트레스판", a0)):
        months = sorted({d[:6] for d in DAYS}); rows = {}
        for mo in [None] + months:
            ds = [d for d in DAYS if mo is None or d[:6] != mo]; v = [p[d] for d in ds]
            qv = [p[d] for d in ds if Z[d]]
            rows["전체" if mo is None else f"{mo} 뺌"] = {"날": len(ds), "합": round(sum(v), 2), "날 평균": round(sum(v) / len(v), 4), "조용한 날 평균": round(sum(qv) / len(qv), 4), "95% 구간(날 평균)": block_ci(v),
                                                       "거래 수": sum(len(lg0[d]) for d in ds)}
        h1[nm] = rows
    out["가설 1"] = h1; out["가설 1"]["스트레스판에서 손익이 바뀐 날 수(대조)"] = n0
    out["가설 1"]["R0 대조 성적"] = {"원판": stat(o0), "스트레스판": stat(a0)}
    # 가설 2
    h2 = {}
    for r in (1.25, 1.50):
        for mode in ("그 신호만", "그날 남은 R0"):
            name = f"r{r} · {mode}"; o, a, lg, n = {}, {}, {}, 0
            for d in DAYS:
                if not Z[d]: o[d] = a[d] = 0.0; lg[d] = []; continue
                sig_day[0] = d; l = []; o[d] = execute2(d, K.sig_r0(d), rule_h2(r, mode), l); a[d] = execute2(d, K.sig_r0(d), rule_h2(r, mode), [], stress=True); lg[d] = l
            res = {}
            for nm, p, base, lb in (("원판", o, o0, lg0), ("스트레스판", a, a0, lg0)):
                ex = [p[d] - base[d] for d in DAYS]; best = max(range(len(ex)), key=lambda i: ex[i])
                kept = {(t["신호분"]) for d in DAYS for t in lg[d]}
                blocked = [t["손익"] for d in DAYS for t in lb[d] if (t["신호분"]) not in {u["신호분"] for u in lg[d]}]
                s = stat(p)
                res[nm] = {"합": s["합"], "MDD": s["MDD"], "최악": s["최악"], "앞반": s["앞반"], "뒤반": s["뒤반"], "초과 합": round(sum(ex), 2),
                           "초과 합 95%": block_ci(ex, stat_fn=sum), "가장 큰 한 날 뺀 초과": round(sum(ex) - ex[best], 2), "막힌 대조 거래 수": len(blocked),
                           "막힌 대조 거래 손익 합": round(sum(blocked), 2), "−15 넘은 날": sum(1 for v in p.values() if v < -15.0),
                           "새로 생긴 거래 수": sum(1 for d in DAYS for t in lg[d] if t["신호분"] not in {u["신호분"] for u in lb[d]})}
                res[nm]["지지"] = res[nm]["초과 합"] > 0 and res[nm]["초과 합 95%"][0] > 0 and res[nm]["가장 큰 한 날 뺀 초과"] > 0 and res[nm]["막힌 대조 거래 손익 합"] < 0
            h2[name] = res; daily[name + " 원판"] = o; daily[name + " 스트레스"] = a
    out["가설 2"] = h2
    sfx = os.getenv("KMF_OUT_SUFFIX", "")
    (HERE / f"kmf_r0q_out{sfx}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (HERE / f"kmf_r0q_daily{sfx}.json").write_text(json.dumps({k: {d: round(v, 4) for d, v in p.items()} for k, p in daily.items()}, ensure_ascii=False))
    print(json.dumps({"R0 대조": out["가설 1"]["R0 대조 성적"], "바꾼 거래": n0}, ensure_ascii=False))
    for nm in ("원판", "스트레스판"):
        print("가설 1", nm, {k: (v["합"], v["95% 구간(날 평균)"]) for k, v in h1[nm].items()})
    for k, v in h2.items(): print("가설 2", k, {nm: {x: v[nm][x] for x in ("합", "MDD", "초과 합", "초과 합 95%", "가장 큰 한 날 뺀 초과", "막힌 대조 거래 손익 합", "지지")} for nm in v})

def cut_test(cuts=("20260415", "20260701", "20260901")):
    full = json.loads((HERE / "kmf_r0q_daily.json").read_text()); bad = 0
    for c in cuts:
        subprocess.run([sys.executable, __file__], env=dict(os.environ, KMF_CUT=c, KMF_OUT_SUFFIX="_cut"), check=True, capture_output=True)
        part = json.loads((HERE / "kmf_r0q_daily_cut.json").read_text())
        bad += sum(1 for k in full for d, v in part[k].items() if d < c and abs(v - full[k][d]) > 1e-9)
    for f in ("kmf_r0q_daily_cut.json", "kmf_r0q_out_cut.json"): (HERE / f).unlink(missing_ok=True)
    (HERE / "kmf_r0q_cut.out").write_text(json.dumps({"cuts": list(cuts), "다른 칸": bad}, ensure_ascii=False)); print("자르기 다른 칸", bad); return bad

if __name__ == "__main__":
    if sys.argv[1:] == ["--cut-test"]: sys.exit(1 if cut_test() else 0)
    main()
