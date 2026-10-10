"""REV-DOWN-0047 — 내림장에서만 켜는 5일 되돌림 매수를 롱 전용 계좌로 재기(비용 포함 · 날마다 평가 NAV).
- 근거: SIG-MAP-0045(M 2006 ~ 2021 내림 국면 S2 +1.345) · PHASE-SWITCH-0046(T 2022 ~ 2026 내림 국면 S2 +1.091).
  이 신호 · 국면 짝은 두 기간 모두 이미 봤습니다. 그래서 이 과제는 '새 기간 시험'이 아니라 **사고팔 수 있는 꼴로 옮겨도 남는지** 보는 구현 시험입니다.
  설정은 모두 앞 과제 정의 그대로 고정(새로 고르는 값 없음): 국면 문턱 −5% · 10거래일 · 위 20% · 대상 거래대금 상위 100.
- 규칙(t날 장 끝 값으로 판단 · 다음 거래일 종가에 삼):
  ① t날 국면 = 굽기 안 069500 t날까지 60거래일 수익 < −5%(내림)일 때만 삼.
  ② t날 대상(전날까지 20일 평균 거래대금 상위 100) 가운데 S2 = −(5거래일 수익)이 큰 위 20%(n // 5 · 같으면 종목 번호 순) = 그날 무리.
  ③ 무리 몫 = t날 장 끝 NAV의 1/10(현금이 모자라면 남은 현금까지) · 무리 안 종목마다 같은 돈.
  ④ t+1날: 그 종목이 그날 값이 있으면 종가에 삼(값이 없으면 그 종목 몫은 현금으로 남김). 사는 데 0.05% 비용.
  ⑤ 산 줄에서 10줄 뒤(그 종목의 10번째 다음 거래일) 종가에 팖. 파는 데 0.25%(세금 · 수수료 · 미끄러짐 합). 값이 끝나면 마지막 값으로 '기간 끝 정산'.
  ⑥ 내림이 아닌 날에는 사지 않음(현금). 이미 산 것은 10줄을 채움.
- 미래 참조 막기: 살지 말지는 t날까지의 값만 씀. 앞날 줄이 있는지 미리 보지 않음(없으면 그때 정산).
- round 2(GPT #208 6097323248):
  · 기간 끝 정산 돈을 현금에 넣고 마지막 날 NAV를 정산 뒤(파는 비용 뺀) 값으로 고침.
  · 판정 ④는 반올림 전 해 수익으로 셈(출력만 반올림).
  · 같은 날 종가 순서 고정: ㉠ 어제 정한 것 사기(그 시각 현금까지) → ㉡ 팔 것 팔기 → ㉢ 그날 장 끝 판단(판 돈 포함한 현금 · NAV로 무리 크기) → 다음 날 삼.
    즉 그날 판 돈은 같은 날 보류 매수에는 못 쓰고, 그날 장 끝 판단 → 다음 날 매수부터 씀. 계좌 · 대조 8개 모두 같은 함수.
  · round 3(GPT #208 6097363711): 판정 ⑤도 반올림 전 부트스트랩 아래 끝으로 셈.
  · 가격 제한: 그 종목 그날 종가가 앞 줄 종가 대비 하한가(2015-06-15 전 −15% · 그 뒤 −30% · 0.5%p 여유)면 그날 못 팖 → 다음 줄로 미룸.
    상한가(+15% · +30% · 같은 여유)면 그날 못 삼 → 그 몫은 현금.
  · 판정 이름: CLOSE_MODEL_PASS_IN_SEEN_DATA(비용 · 가격 제한 넣은 종가 모형 · 이미 본 자료 안) — 모의 운영 근거로 바로 쓰지 않음.
python3 research/rev_down.py --run      잠금 확인 → O_EXCL 영수증 → 계좌 셈 → 대조 8 → 판정(한 번뿐)
python3 research/rev_down.py --cut-test 자르기 시험(같음 · 다름 수만)
python3 research/rev_down.py --lock     잠금 파일 쓰기(성과 셈 없음)"""
import bisect
import hashlib
import json
import os
import pickle
import random
import sys
import time
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
BOX = ROOT / "research-exchange/claude-to-gpt/REV-DOWN-0047"
FULL = ("/tmp/rev-full.pkl", "20060102", "20260915")
CUT = ("/tmp/rev-cut.pkl", "20060102", "20131230")
LOCK = BOX / "lock.json"
RECEIPT = BOX / "receipt.json"
HOLD, SLICE, TOPQ = 10, 10, 5
BUY_COST, SELL_COST = 0.0005, 0.0025
PH_N, PH_TH = 60, -0.05
SEEDS = tuple(range(1, 9))
BOOT_REPS, BOOT_SEED = 2000, 47
LIMIT_CHANGE, SLACK = "20150615", 0.005


def limit_of(d):
    return 0.15 if d < LIMIT_CHANGE else 0.30


def day_move(ln, k):
    return None if k < 1 else ln["x"][k] / ln["x"][k - 1] - 1


def locked_down(ln, k, d):
    m = day_move(ln, k)
    return m is not None and m <= -(limit_of(d) - SLACK)


def locked_up(ln, k, d):
    m = day_move(ln, k)
    return m is not None and m >= limit_of(d) - SLACK


def load(path):
    s = pickle.load(open(path, "rb"))
    lanes = {c: {"d": [d for d, _ in b["rows"]], "x": [x for _, x in b["rows"]]} for c, b in s["prices"].items()}
    for ln in lanes.values():
        ln["pos"] = {d: k for k, d in enumerate(ln["d"])}
    return s, lanes


def is_down(s, ixd, d):
    k = bisect.bisect_right(ixd, d) - 1
    return k >= PH_N and s["ix"][ixd[k]] / s["ix"][ixd[k - PH_N]] - 1 < PH_TH


def pick_rank(rows, lanes):
    """그날 무리: S2 큰 위 20%(5거래일 값이 있는 종목만)."""
    have = []
    for r in rows:
        x, i = lanes[r["code"]]["x"], r["i"]
        if i >= 5:
            have.append((-(x[i] / x[i - 5] - 1), r["code"]))
    have.sort(key=lambda z: (-z[0], z[1]))
    return [c for _, c in have[:len(have) // TOPQ]]


def pick_random(rows, lanes, n, rnd):
    pool = sorted(r["code"] for r in rows if r["i"] >= 5)
    return rnd.sample(pool, min(n, len(pool)))


def simulate(part, chooser="rank", seed=None):
    """돌려줌: {nav: {날: 값}, cohorts: [...], trades: n, last_day}"""
    path, lo, hi = part
    s, lanes = load(path)
    ixd = sorted(s["ix"])
    byd = {}
    for r in s["rows"]:
        if lo <= r["date"] <= hi:
            byd.setdefault(r["date"], []).append(r)
    days = sorted(byd)
    rnd = random.Random(seed)
    cash, nav_prev = 1.0, 1.0
    held = []          # {code, k(산 줄), sh(주식 수), cost(들인 돈), cohort}
    pending = []       # (code, 돈, cohort) — 어제 정한 오늘 살 것
    cohorts = {}       # 번호 → {day, spent, back}
    navs, trades = {}, 0
    blocked_buy, delayed_sell = 0, 0
    for d in days:
        # ④ 어제 정한 것 사기
        for code, money, cid in pending:
            ln = lanes[code]
            k = ln["pos"].get(d)
            money = min(money, cash)
            if k is None or money <= 0:
                continue
            if locked_up(ln, k, d):          # 상한가 → 못 삼(현금)
                blocked_buy += 1
                continue
            px = ln["x"][k]
            sh = money * (1 - BUY_COST) / px
            cash -= money
            held.append({"code": code, "k": k, "sh": sh, "cost": money, "cohort": cid})
            cohorts[cid]["spent"] += money
            trades += 1
        pending = []
        # ⑤ 10줄 채운 것 팔기
        keep = []
        for h in held:
            ln = lanes[h["code"]]
            k = ln["pos"].get(d)
            if k is not None and k >= h["k"] + HOLD and locked_down(ln, k, d):   # 하한가 → 못 팖 · 다음 줄로
                delayed_sell += 1
                keep.append(h)
            elif k is not None and k >= h["k"] + HOLD:
                back = h["sh"] * ln["x"][k] * (1 - SELL_COST)
                cash += back
                cohorts[h["cohort"]]["back"] += back
            else:
                keep.append(h)
        held = keep
        # 날마다 평가(값이 없는 날은 그 종목의 마지막 값)
        val = cash
        for h in held:
            ln = lanes[h["code"]]
            k = bisect.bisect_right(ln["d"], d) - 1
            val += h["sh"] * ln["x"][k]
        navs[d] = val
        # ①②③ 오늘 장 끝 판단 → 내일 살 것
        if is_down(s, ixd, d):
            names = pick_rank(byd[d], lanes) if chooser == "rank" else pick_random(byd[d], lanes, len(pick_rank(byd[d], lanes)), rnd)
            if names:
                money = min(val / SLICE, cash)
                cid = len(cohorts)
                cohorts[cid] = {"day": d, "spent": 0.0, "back": 0.0, "n": len(names)}
                pending = [(c, money / len(names), cid) for c in names]
    # 기간 끝 정산(마지막 값 · 파는 비용)
    last = days[-1]
    for h in held:
        ln = lanes[h["code"]]
        k = bisect.bisect_right(ln["d"], last) - 1
        back = h["sh"] * ln["x"][k] * (1 - SELL_COST)
        cash += back
        cohorts[h["cohort"]]["back"] += back
        cohorts[h["cohort"]]["end_settled"] = True
    navs[last] = cash                     # 정산 뒤(파는 비용 뺀) 값
    return {"nav": navs, "cohorts": [dict(v, id=k) for k, v in cohorts.items() if v["spent"] > 0], "trades": trades,
            "last_day": last, "end_open": len(held), "blocked_buy_limit_up": blocked_buy, "delayed_sell_limit_down_rows": delayed_sell}


def stats(sim):
    nav = sim["nav"]
    ds = sorted(nav)
    rets = {ds[j]: nav[ds[j]] / nav[ds[j - 1]] - 1 for j in range(1, len(ds))}
    worst_day = min(rets.items(), key=lambda z: z[1])
    months, years = {}, {}
    for d, r in rets.items():
        months[d[:6]] = months.get(d[:6], 1.0) * (1 + r)
        years[d[:4]] = years.get(d[:4], 1.0) * (1 + r)
    worst_month = min(months.items(), key=lambda z: z[1])
    peak, mdd = 0.0, 0.0
    for d in ds:
        peak = max(peak, nav[d])
        mdd = min(mdd, nav[d] / peak - 1)
    n_years = len(ds) / 250
    end = nav[ds[-1]]
    coh = [c["back"] / c["spent"] - 1 for c in sim["cohorts"]]
    return {"end_nav": end, "annual_pct": round((end ** (1 / n_years) - 1) * 100, 3), "worst_day": [worst_day[0], round(worst_day[1] * 100, 3)],
            "worst_month": [worst_month[0], round((worst_month[1] - 1) * 100, 3)], "years_pct": {y: round((v - 1) * 100, 3) for y, v in sorted(years.items())},
            "years_raw": {y: v - 1 for y, v in sorted(years.items())}, "annual_raw": end ** (1 / n_years) - 1,
            "worst_day_raw": worst_day[1], "worst_month_raw": worst_month[1] - 1,
            "mtm_mdd_report_only_pct": round(mdd * 100, 3), "cohorts": len(coh), "trades": sim["trades"],
            "cohort_mean_net_pct": round(sum(coh) / len(coh) * 100, 3) if coh else None}


def boot_cohort(sim):
    """무리 순손익 평균의 95% 구간 · 무리 산 날의 달로 묶어 되뽑기(보고 · 판정 ⑤에 씀)."""
    months = {}
    for c in sim["cohorts"]:
        months.setdefault(c["day"][:6], []).append(c["back"] / c["spent"] - 1)
    blocks = list(months.values())
    rnd = random.Random(BOOT_SEED)
    got = []
    for _ in range(BOOT_REPS):
        flat = [x for b in (blocks[rnd.randrange(len(blocks))] for _ in blocks) for x in b]
        got.append(sum(flat) / len(flat))
    got.sort()
    lo, hi = got[int(BOOT_REPS * 0.025)], got[int(BOOT_REPS * 0.975)]
    return {"lo_raw": lo, "hi_raw": hi, "pct": [round(lo * 100, 3), round(hi * 100, 3)]}      # 판정은 lo_raw(round 3)


def judge(st, ctrl, boot):
    lo = boot["lo_raw"] if isinstance(boot, dict) else boot[0]                               # 판정 ⑤는 반올림 전 아래 끝
    yr = st.get("years_raw", st["years_pct"])          # 판정은 반올림 전 값(round 2)
    active = [y for y, v in yr.items() if v != 0.0]
    pos = sum(1 for y in active if yr[y] > 0)
    med = sorted(ctrl)[len(ctrl) // 2 - 1: len(ctrl) // 2 + 1]
    med = sum(med) / 2
    ann = st["annual_raw"] * 100 if "annual_raw" in st else st["annual_pct"]
    wd = st["worst_day_raw"] * 100 if "worst_day_raw" in st else st["worst_day"][1]
    wm = st["worst_month_raw"] * 100 if "worst_month_raw" in st else st["worst_month"][1]
    c = {"0_cohorts_ge_60": st["cohorts"] >= 60, "1_annual_gt0": ann > 0, "2_beats_random_median": ann > med,
         "3_day_month_ge_-15": wd >= -15 and wm >= -15,
         "4_active_years_pos_ge_60pct": bool(active) and pos / len(active) >= 0.6, "5_boot_lo_gt0": lo > 0}
    verdict = "NEEDS_DATA" if not c["0_cohorts_ge_60"] else ("CLOSE_MODEL_PASS_IN_SEEN_DATA" if all(c.values()) else "REJECTED")
    return c, verdict, med, f"{pos}/{len(active)}"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lock_body():
    return {"research/rev_down.py": sha(__file__), FULL[0]: sha(FULL[0])}


def run():
    want = json.loads(LOCK.read_text())
    have = lock_body()
    if want != have:
        sys.exit("잠금이 다름(멈춤): " + json.dumps({k: (want.get(k), v) for k, v in have.items() if want.get(k) != v}, ensure_ascii=False))
    key = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    import subprocess
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    body = {"status": "STARTED", "lock_key": key, "git_head": head, "at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}
    try:
        fd = os.open(str(RECEIPT), os.O_CREAT | os.O_EXCL | os.O_WRONLY)       # 어떤 성과 셈보다 먼저
    except FileExistsError:
        sys.exit("영수증이 이미 있음(멈춤) — 한 번만 돌림")
    with os.fdopen(fd, "w") as fh:
        fh.write(json.dumps(body, ensure_ascii=False))
        fh.flush()
        os.fsync(fh.fileno())
    sim = simulate(FULL)
    st = stats(sim)
    ctrl_runs = []
    for sd in SEEDS:
        cs = stats(simulate(FULL, "random", sd))
        ctrl_runs.append({"seed": sd, "annual_pct": cs["annual_pct"], "annual_raw_pct": cs["annual_raw"] * 100, "cohorts": cs["cohorts"], "trades": cs["trades"]})
    boot = boot_cohort(sim)
    cond, verdict, med, ypos = judge(st, [x["annual_raw_pct"] for x in ctrl_runs], boot)
    st_out = {k: v for k, v in st.items() if not k.endswith("_raw")}
    out = {"task": "REV-DOWN-0047", "lock_key": key, "receipt": body, "stats": st_out, "annual_raw_pct": st["annual_raw"] * 100, "active_years_pos": ypos, "control": ctrl_runs,
           "control_median_pct": round(med, 3), "boot95_cohort_net_pct": boot["pct"], "boot95_lo_raw": boot["lo_raw"], "conditions": cond, "verdict": verdict,
           "end_open_positions": sim["end_open"], "blocked_buy_limit_up": sim["blocked_buy_limit_up"],
           "delayed_sell_limit_down_rows": sim["delayed_sell_limit_down_rows"], "independent_validation": "WAITING_DATA",
           "verdict_meaning": "비용 · 가격 제한을 넣은 종가 모형 · 이미 본 자료 안 · 모의 운영 근거로 바로 쓰지 않음",
           "cohorts_detail": [{"day": c["day"], "n": c["n"], "net_pct": round((c["back"] / c["spent"] - 1) * 100, 3)} for c in sim["cohorts"]]}
    print(json.dumps(out, ensure_ascii=False))


def cut_test():
    """같은 2006 ~ 2013을 '온 굽기'와 '2013-12-30에서 자른 굽기'로: 자른 날 앞 날마다 NAV · 무리 목록이 같아야 함(자른 날 당일은 정산이라 뺌)."""
    a = simulate((FULL[0], CUT[1], CUT[2]))
    b = simulate(CUT)
    days = [d for d in b["nav"] if d < CUT[2]]
    bad_nav = [d for d in days if abs(a["nav"].get(d, -1) - b["nav"][d]) > 1e-12]
    ca = [(c["day"], c["n"]) for c in a["cohorts"]]
    cb = [(c["day"], c["n"]) for c in b["cohorts"]]
    print(json.dumps({"nav_days_compared": len(days), "nav_differ": len(bad_nav), "first_bad": bad_nav[:3],
                      "cohorts_full": len(ca), "cohorts_cut": len(cb), "cohort_lists_same": ca == cb}, ensure_ascii=False))


def main():
    if "--run" in sys.argv:
        return run()
    if "--cut-test" in sys.argv:
        return cut_test()
    if "--lock" in sys.argv:
        BOX.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1))
        print(LOCK.read_text())
        return
    sys.exit("영수증 없는 성과 셈은 없음 — --run(한 번) · --cut-test · --lock만 됩니다")


if __name__ == "__main__":
    main()
