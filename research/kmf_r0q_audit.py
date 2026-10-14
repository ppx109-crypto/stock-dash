"""R0Q-0001 독립 점검(감사). kmf_r0q.py(잠금 4d647cce)의 execute2 · rule_h2 · block_ci는 부르지 않고 따로 다시 짬.
쓰는 것: kmf_nb의 자료(BY · B15 · E10 · sig_r0 · COST · CAP · last_close)와 kmf_hdd_base의 Z · DAYS(조용한 날 판단)만.
1) 가설 2 네 판을 내 실행기로 다시 셈 → kmf_r0q_daily.json과 날별 비교 · 규칙이 실제 막은 날 수 · r1.5가 한 번도 안 걸린 까닭(ATR 비 분포).
2) 가설 1(합 · 평가 날 평균 · 조용한 날 평균 · 달 하나씩 뺀 줄 · 이동 덩어리 재표집 95% 구간)을 다시 셈 → out.json과 비교.
3) 빈 29분 9구간 날 가운데 조용한 날이 없는지 · 조용한 날만 R0 판에서 스트레스판 = 원판인지.
4) out.json 가설 2의 '조건'이 '원정밀도' 값에서 나왔는지(반올림 전 값으로 판정했는지).
python3 research/kmf_r0q_audit.py → research/kmf_r0q_audit.out"""
import sys, json, random, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from kmf_hdd_base import K, Z, DAYS

OUT = json.loads((HERE / "kmf_r0q_out.json").read_text()); DAILY = json.loads((HERE / "kmf_r0q_daily.json").read_text())
HOLES_MINE = {"20260304": (680, 708), "20260309": (632, 660), "20260608": (544, 572), "20260623": (874, 902), "20260626": (731, 759),
              "20260707": (832, 860), "20260713": (809, 837), "20260728": (614, 642), "20260729": (753, 781)}
lines = []
def say(*a):
    s = " ".join(str(x) for x in a); lines.append(s); print(s)

# 신호 봉의 닫힌 15분 ATR(그 봉 끝까지의 값) · 날 · 봉 끝 분으로 찾음
ATR = {}
for d, js in K.BYD.items():
    for j in js: ATR[(d, K.B15[j][1])] = K.E10[j][1]

def run_day(d, r=None, mode=None, stress=False, info=None):
    """kmf_nb.execute(지연 0 · 최대 2번)를 그대로 옮기고, 가설 2 막기만 덧붙임.
    막기 판단은 '실제로 들어갈 수 있었던 신호'(횟수 · 예산 · 앞 포지션 정리 뒤 · 정리 분 앞)에서만 함 → 첫 거래가 끝나기 전 신호는 대상 아님."""
    x = K.BY[d]; real = 0.0; cnt = 0; free_at = 0; stopped = False; dead = False
    first_pnl = None; first_atr = None; trades = []; nblock = 0; ratios = []
    hole = HOLES_MINE.get(d) if stress else None
    for (m0, side, tg, sd, m_exit) in K.sig_r0(d):
        if stopped or cnt >= 2 or K.CAP + real < 3.0: continue
        me = next((mm for mm in range(m0, 935) if mm in x), None)
        if me is None or me < free_at or me >= m_exit: continue
        if dead: nblock += 1; continue
        if first_pnl is not None and first_pnl < 0 and first_atr:
            q = ATR[(d, m0)] / first_atr; ratios.append(q)
            if r is not None and q >= r:
                nblock += 1
                if mode == "그날 남은 R0": dead = True
                continue
        if first_atr is None: first_atr = ATR[(d, m0)]
        ent = x[me][2]; sd = min(sd, max(0.5, K.CAP + real - 2 * K.COST)); stop = ent - side * sd; cnt += 1; out = None
        for m in range(me, 935):
            if m not in x: continue
            o, h, l, c = x[m][2], x[m][3], x[m][4], x[m][5]
            if m == me: o = ent
            if hole and me < hole[0] and m > hole[1]: out = (stop, hole[1] + 1); break
            if m >= m_exit: out = (o, m); break
            if (l <= stop) if side > 0 else (h >= stop): out = (min(o, stop) if side > 0 else max(o, stop), m + 1); break
            if tg is not None and ((h >= tg) if side > 0 else (l <= tg)): out = (max(o, tg) if side > 0 else min(o, tg), m + 1); break
            if real + side * (c - ent) - 2 * K.COST <= -K.CAP:
                nm = next((mm for mm in range(m + 1, 935) if mm in x), None); out = (x[nm][2] if nm else c, 999); stopped = True; break
        if out is None: out = (K.last_close(d), 999)
        pnl = side * (out[0] - ent) - 2 * K.COST; real += pnl; free_at = out[1]
        if first_pnl is None: first_pnl = pnl
        trades.append((m0, pnl))
        if real <= -K.CAP: stopped = True
    if info is not None: info.update(trades=trades, nblock=nblock, ratios=ratios, first_pnl=first_pnl)
    return real

def plan(r=None, mode=None, stress=False):
    p, inf = {}, {}
    for d in DAYS:
        if not Z[d]: p[d] = 0.0; inf[d] = {"trades": [], "nblock": 0, "ratios": [], "first_pnl": None}; continue
        i = {}; p[d] = run_day(d, r, mode, stress, i); inf[d] = i
    return p, inf

def boot(v, stat_fn, B=2000, L=5, seed=0):
    rng = random.Random(seed); n = len(v); res = []
    for _ in range(B):
        s = []
        while len(s) < n:
            i = rng.randrange(0, n - L + 1); s.extend(v[i:i + L])
        res.append(stat_fn(s[:n]))
    res.sort(); return [res[int(0.025 * B)], res[int(0.975 * B) - 1]]
mean = lambda s: sum(s) / len(s)

# 0) 재현 확인: 규칙 없는 내 실행기 = kmf_nb.execute
rep_bad = sum(1 for d in DAYS if abs(run_day(d) - K.execute(d, K.sig_r0(d))) > 1e-9)
say("[0] 규칙 없는 내 실행기 vs kmf_nb.execute 다른 날:", rep_bad, "/", len(DAYS))

# 1) 가설 2
o0, i0 = plan(); a0, _ = plan(stress=True)
say("\n[1] 가설 2 다시 셈 (평가", len(DAYS), "일 · 조용한 날", sum(Z[d] for d in DAYS), "일)")
mis_ctrl = sum(1 for d in DAYS if abs(round(o0[d], 4) - DAILY["R0 대조 원판"][d]) > 1e-9) + sum(1 for d in DAYS if abs(round(a0[d], 4) - DAILY["R0 대조 스트레스"][d]) > 1e-9)
say("  대조(원판 + 스트레스) 날별 다른 칸:", mis_ctrl)
first_loss_days = [d for d in DAYS if Z[d] and i0[d]["first_pnl"] is not None and i0[d]["first_pnl"] < 0]
total_mis = 0; h2_field_bad = 0; mine_h2 = {}
for r in (1.25, 1.5):
    for mode in ("그 신호만", "그날 남은 R0"):
        name = f"r{r} · {mode}"; o, inf = plan(r, mode); a, _ = plan(r, mode, stress=True)
        mo = sum(1 for d in DAYS if abs(round(o[d], 4) - DAILY[name + " 원판"][d]) > 1e-9)
        ms = sum(1 for d in DAYS if abs(round(a[d], 4) - DAILY[name + " 스트레스"][d]) > 1e-9)
        total_mis += mo + ms
        trig = [d for d in DAYS if inf[d]["nblock"] > 0]
        chg = [d for d in DAYS if abs(o[d] - o0[d]) > 1e-12]
        ex = [o[d] - o0[d] for d in DAYS]; best = max(range(len(ex)), key=lambda k: ex[k])
        blocked = [p for d in DAYS for (m0, p) in i0[d]["trades"] if m0 not in {t[0] for t in inf[d]["trades"]}]
        newt = sum(1 for d in DAYS for (m0, _) in inf[d]["trades"] if m0 not in {t[0] for t in i0[d]["trades"]})
        raw = {"초과 합": sum(ex), "초과 합 95%": boot(ex, sum), "가장 큰 한 날 뺀 초과": sum(ex) - ex[best], "막힌 대조 거래 손익 합": sum(blocked)}
        mine_h2[name] = raw
        st = OUT["가설 2"][name]["원판"]; fb = 0
        for k in ("초과 합", "가장 큰 한 날 뺀 초과", "막힌 대조 거래 손익 합"): fb += abs(raw[k] - st["원정밀도"][k]) > 1e-9
        fb += any(abs(u - v) > 1e-9 for u, v in zip(raw["초과 합 95%"], st["원정밀도"]["초과 합 95%"]))
        fb += st["막힌 대조 거래 수"] != len(blocked); fb += st["새로 생긴 거래 수"] != newt
        h2_field_bad += fb
        say(f"  {name}: 날별 다른 칸 원판 {mo} · 스트레스 {ms} | 규칙이 실제 막은 날 {len(trig)} {trig} · 손익이 바뀐 날 {len(chg)} | "
            f"초과 합 {raw['초과 합']:.4f} · 95% {[round(x, 4) for x in raw['초과 합 95%']]} · 막힌 대조 거래 {len(blocked)}건 손익 합 {raw['막힌 대조 거래 손익 합']:.4f} · 새 거래 {newt}건 | out.json 원판 원정밀도 · 건수와 다른 칸 {fb}")
say("  가설 2 네 판 날별 다른 칸 합(원판 + 스트레스):", total_mis, "· out.json 원정밀도 · 건수 다른 칸 합:", h2_field_bad)
# r1.5가 안 걸리는 까닭: 대조에서 첫 거래가 손실인 날, 그 뒤 '들어갈 수 있었던' R0 신호의 ATR 비
q_ctrl = [(d, round(q, 4)) for d in first_loss_days for q in i0[d]["ratios"]]
say("  대조: 조용한 날 중 첫 R0 거래가 손실인 날", len(first_loss_days), "일 · 그 뒤 들어갈 수 있던 R0 신호", len(q_ctrl), "개")
say("  그 신호들의 ATR 비(신호 봉 ATR ÷ 첫 진입 신호 봉 ATR):", sorted(q_ctrl, key=lambda t: -t[1]))
qs = sorted(q for _, q in q_ctrl)
if qs: say(f"  ATR 비 분포: 최소 {qs[0]} · 가운데 {qs[len(qs) // 2]} · 최대 {qs[-1]} · ≥1.25 {sum(q >= 1.25 for q in qs)}개 · ≥1.5 {sum(q >= 1.5 for q in qs)}개")
# 참고: 들어갈 수 있었든 없든, 첫 손실 거래 정리 뒤 그날 모든 R0 신호의 ATR 비 최대값(조건을 넓혀도 1.5에 닿는지)
allq = []
for d in first_loss_days:
    fm = i0[d]["trades"][0][0]; fa = ATR[(d, fm)]
    allq += [ATR[(d, s[0])] / fa for s in K.sig_r0(d) if s[0] > fm]
say(f"  참고(넓힌 조건): 첫 손실 날, 첫 신호 뒤 그날 모든 R0 신호 {len(allq)}개의 ATR 비 최대 {max(allq):.4f} · ≥1.5 {sum(q >= 1.5 for q in allq)}개" if allq else "  참고: 없음")
# 왜 1.5에 안 닿나: (가) 하루 최대 2번 → 첫 손실 뒤 '들어갈 수 있는' 신호는 둘째 거래 신호 하나(그 신호만 판에서 막히면 그 뒤 신호도) ·
# (나) 둘째 신호가 첫 거래 정리 직후라 15분 봉이 거의 새로 안 닫힘 · (다) ATR = 봉 폭의 EMA14(가중 2/15) → 한 봉으로 1.5배가 되려면 그 봉 폭이 ATR의 4.75배 이상
gap, after2, before_exit, hi = [], 0, 0, 0
for d in first_loss_days:
    lg = []; K.execute(d, K.sig_r0(d), log=lg); fx = lg[0]["정리분"]; fa = ATR[(d, lg[0]["신호분"])]
    if len(lg) > 1: gap.append(lg[1]["신호분"] - fx)
    for s in K.sig_r0(d):
        if s[0] > lg[0]["신호분"] and ATR[(d, s[0])] / fa >= 1.5:
            hi += 1
            if len(lg) > 1 and s[0] > lg[1]["신호분"]: after2 += 1
            elif s[0] <= fx: before_exit += 1
gap.sort()
say(f"  ATR 비 ≥1.5 신호 {hi}개 중 둘째 거래가 이미 들어간 뒤(하루 2번 다 씀) {after2}개 · 첫 거래 정리 전 {before_exit}개")
say(f"  첫 거래 정리 → 둘째 신호 간격(분) {gap} · 15분 안 {sum(g < 15 for g in gap)}/{len(gap)}")
say("  해석: ATR은 15분 봉 폭의 EMA(가중 2/15)라 한 봉으로 1.5배가 되려면 그 봉 폭이 ATR의 4.75배 이상이어야 함. 둘째 신호는 대부분 첫 거래 정리 15분 안에 와서 새로 닫힌 봉이 0~1개 → 비가 1 근처(최대 1.3748).")

# 2) 가설 1
say("\n[2] 가설 1 다시 셈 (대조 = 조용한 날만 R0 · 날 손익만 뺌)")
h1_bad = 0; h1_cells = 0
for nm, p in (("원판", o0), ("스트레스판", a0)):
    months = sorted({d[:6] for d in DAYS}); st_rows = OUT["가설 1"][nm]
    for mo in [None] + months:
        key = "전체" if mo is None else f"{mo} 뺌"; ds = [d for d in DAYS if mo is None or d[:6] != mo]
        v = [p[d] for d in ds]; qv = [p[d] for d in ds if Z[d]]; ci = boot(v, mean)
        mine = {"날": len(ds), "합": round(sum(v), 2), "날 평균": round(mean(v), 4), "조용한 날 평균": round(mean(qv), 4),
                "95% 구간(날 평균)": [round(x, 4) for x in ci], "거래 수": sum(len(i0[d]["trades"]) for d in ds)}
        diff = [k for k in mine if mine[k] != st_rows[key][k]]; h1_bad += len(diff); h1_cells += len(mine)
        say(f"  {nm} {key}: 날 {mine['날']} · 합 {mine['합']} · 날 평균 {mine['날 평균']} · 조용한 날 평균 {mine['조용한 날 평균']} · 95% {mine['95% 구간(날 평균)']} · 거래 {mine['거래 수']} | 다른 칸 {diff or 0}")
say("  가설 1 다른 칸:", h1_bad, "/", h1_cells)
nchg = sum(1 for d in DAYS if abs(a0[d] - o0[d]) > 1e-12)
say("  스트레스판에서 손익이 바뀐 날(내 셈):", nchg, "· out.json:", OUT["가설 1"]["스트레스판에서 손익이 바뀐 날 수(대조)"])

# 3) 빈 구간 날
say("\n[3] 빈 29분 9구간")
say("  out.json meta.holes = 내 목록:", {k: list(v) for k, v in HOLES_MINE.items()} == OUT["meta"]["holes"])
for d, (a, b) in HOLES_MINE.items():
    miss = sum(1 for m in range(a, b + 1) if m not in K.BY[d])
    say(f"  {d} {a // 60:02d}:{a % 60:02d}~{b // 60:02d}:{b % 60:02d}: 평가 날 {d in Z} · 조용한 날 {Z.get(d)} · 그 구간 빈 분 {miss}/{b - a + 1} · 구간 앞뒤 분 있음 {(a - 1) in K.BY[d]}/{(b + 1) in K.BY[d]}")
nq = sum(1 for d in HOLES_MINE if Z.get(d) is True)
say("  빈 구간 날 가운데 조용한 날:", nq)
eq_bad = sum(1 for k in DAILY if k.endswith(" 원판") for d in DAYS if DAILY[k][d] != DAILY[k[:-3] + " 스트레스"][d])
say("  kmf_r0q_daily.json 다섯 판(대조 + 4판)에서 스트레스 ≠ 원판인 칸:", eq_bad)
say("  내 셈 대조에서 스트레스 ≠ 원판인 날:", nchg)
# 스트레스 장치 자체가 돌기는 하는지: 빈 구간 날(조용하지 않은 날)에 R0를 억지로 돌려 비교(참고 · 판에는 없음)
probe = {d: (round(run_day(d), 4), round(run_day(d, stress=True), 4)) for d in HOLES_MINE if d in Z}
say("  참고(장치 시험): 빈 구간 날에 R0를 억지로 돌린 원판/스트레스:", probe, "· 달라진 날", sum(1 for u, v in probe.values() if u != v))
span = []
for d, (a, b) in HOLES_MINE.items():
    lg = []; K.execute(d, K.sig_r0(d), log=lg); span += [(d, t["진입분"], t["정리분"]) for t in lg if t["진입분"] < a and t["정리분"] > b]
say("  억지로 돌린 R0 거래 중 빈 구간을 들고 지난 거래:", span or 0, "→ 이 R0 규칙에서는 스트레스판 장치가 조용한 날 여부와 상관없이 한 번도 작동하지 않음(판정 영향 0 · 장치 자체 검증은 못 함)")

# 4) 지지 조건이 원정밀도에서 나왔는지
say("\n[4] 가설 2 지지 조건 = 원정밀도에서 판정?")
c_bad = 0; r_bad = 0; s_bad = 0; supp = []
for name, v in OUT["가설 2"].items():
    for nm, st in v.items():
        raw = st["원정밀도"]
        cond = {"초과 합 > 0": raw["초과 합"] > 0, "95% 하한 > 0": raw["초과 합 95%"][0] > 0, "한 날 빼도 > 0": raw["가장 큰 한 날 뺀 초과"] > 0, "막힌 거래 손익 < 0": raw["막힌 대조 거래 손익 합"] < 0}
        c_bad += sum(cond[k] != st["조건"][k] for k in cond) + (set(cond) != set(st["조건"]))
        r_bad += (round(raw["초과 합"], 2) != st["초과 합"]) + ([round(x, 2) for x in raw["초과 합 95%"]] != st["초과 합 95%"]) + \
                 (round(raw["가장 큰 한 날 뺀 초과"], 2) != st["가장 큰 한 날 뺀 초과"]) + (round(raw["막힌 대조 거래 손익 합"], 2) != st["막힌 대조 거래 손익 합"])
        s_bad += st["지지"] != all(st["조건"].values())
        # 반올림 값으로 판정했으면 달라졌을 칸(경계에 걸린 값이 있는지)
        rc = {"초과 합 > 0": st["초과 합"] > 0, "95% 하한 > 0": st["초과 합 95%"][0] > 0, "한 날 빼도 > 0": st["가장 큰 한 날 뺀 초과"] > 0, "막힌 거래 손익 < 0": st["막힌 대조 거래 손익 합"] < 0}
        for k in cond:
            if rc[k] != cond[k]: say(f"  {name} {nm} '{k}': 반올림 값이면 {rc[k]} · 원정밀도면 {cond[k]} (원값 {raw})")
        supp.append((name, nm, st["지지"]))
        if nm == "원판": r_bad += any(abs(raw[k] - mine_h2[name][k]) > 1e-9 for k in ("초과 합", "가장 큰 한 날 뺀 초과", "막힌 대조 거래 손익 합"))
say("  조건 ≠ 원정밀도 재판정:", c_bad, "· 표시값 ≠ 원정밀도 반올림:", r_bad, "· 지지 ≠ 조건 모두:", s_bad)
say("  지지:", supp)
say("  주의: 95% 하한이 정확히 0.0인 판 —", [(n, s) for n, v in OUT["가설 2"].items() for s, st in v.items() if st["원정밀도"]["초과 합 95%"][0] == 0.0 or st["원정밀도"]["초과 합 95%"][1] == 0.0],
    "(막은 날이 적어 재표집 대부분이 0 · '> 0' 엄격 부등호라 지지 아님)")

say("\n[요약] 재현 다른 날", rep_bad, "· 가설 2 날별 다른 칸", total_mis + mis_ctrl, "· 가설 2 원정밀도 · 건수 다른 칸", h2_field_bad,
    "· 가설 1 다른 칸", h1_bad, "· 빈 구간 날 중 조용한 날", nq, "· 스트레스 ≠ 원판 칸", eq_bad, "· 조건 다른 칸", c_bad, "· 표시값 다른 칸", r_bad, "· 지지 다른 칸", s_bad)
(HERE / "kmf_r0q_audit.out").write_text("\n".join(lines) + "\n")
