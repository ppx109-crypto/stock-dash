"""XASSET-0060 — 새 봇: 빈 돈으로 해외 · 금 · 달러 · 채권 ETF 추세 바구니(사용자 2026-10-11 "새 봇을 연구해 추가").
출발: MIX-0054 최종(켜 둔 판 · 바탕 d0.5_b0.3_no15m + 덧붙임 n24 · persist 3 · r10m5 · 레버리지 0.4 · 횡보 인버스 0.4).
진단(사전등록 전에 봄 · 공개): 바탕 장부 평균 현금 51% 중 덧붙임이 약 31%를 써서 약 20%가 놂.
  국내 ETF로 사는 해외 · 금 · 달러 · 채권은 계좌 달 수익과 상관이 낮음(나스닥100 0.29 · 금 0.24 · 달러선물 −0.11 · 국고채10년 0.02).
새 봇(덧붙임 · 1일봉 · 국면은 그대로 · 남는 돈만 씀):
  달 첫 거래일 종가에, 전 거래일까지 달 끝 종가로 '종가 > 최근 N달 달끝 종가 평균'인 ETF를 같은 몫으로 삼(나머지는 현금).
  봇 몫 = min(w, 덧붙임을 맞춘 뒤 남는 몫(room − 덧붙임 몫)) × 계좌. 달 중간에 1일봉이 현금을 다시 쓰면 이 봇부터 팖(빚 없음).
python3 research/xasset.py lock   → input_lock.json(성과 셈 없음)
python3 research/xasset.py run    → 잠금 검사 → 고정 13판 + 고르기 + 이웃(기록 evals.jsonl)
python3 research/xasset.py cut    → 자르기 시험"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "XASSET-0060")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402
import regime_rules4 as R4  # noqa: E402

BOX = ROOT / "research-exchange/claude-to-gpt/XASSET-0060"
EVALS = BOX / "evals.jsonl"
LOCK = BOX / "input_lock.json"
BASE = (0.5, 0.3)
FINAL = dict(D.R0, **M.OVERLAYS["L0.4_S0.4"])
UNIVERSE = {"U4": ("133690", "132030", "261240", "148070"),      # 나스닥100 · 금선물 · 달러선물 · 국고채10년
            "U3": ("133690", "132030", "261240")}                # 채권 뺌
SLEEVE_ETF = sorted(set(UNIVERSE["U4"]))
N_MON = [6, 10]
W = [0.1, 0.2, 0.3]
FIRST_FULL, LAST_FULL = "201703", "202608"
DAY_LIM, MONTH_LIM, NB_CAP = -0.15, -0.15, 100
ANN_GAIN, MONTH_SLACK, LOSS_SLACK = 0.01, 0.01, 2
CODE_FILES = ["research/xasset.py", "research/regime_dev.py", "research/mix54_run.py", "research/regime_rules4.py"]
MARKET_FILES = ["market-data/investor_KSP.json", "market-data/index_KOSPI.json"]
SX = None


def check_root():
    roots = {"xasset": ROOT.resolve(), "regime_dev": Path(D.ROOT).resolve(), "mix54_run": Path(M.ROOT).resolve()}
    if len(set(roots.values())) != 1:
        sys.exit("저장소 뿌리가 서로 다름(멈춤): " + json.dumps({k: str(v) for k, v in roots.items()}, ensure_ascii=False))
    return roots["regime_dev"]


def loader_files():
    root = Path(D.ROOT)
    out = {f"etf-data/{c}.json": root / f"etf-data/{c}.json" for c in D.ETF}
    out |= {f"etf-data/{c}.json": root / f"etf-data/{c}.json" for c in SLEEVE_ETF}      # 새 봇 ETF 넷(이 파일이 읽음)
    return out | {f: root / f for f in MARKET_FILES}


def sleeve_px():
    """새 봇 ETF 종가(그날까지 · REG_CUT 자르기 따름)."""
    global SX
    if SX is None:
        SX = {c: {d: float(x) for d, x in json.load(open(Path(D.ROOT) / f"etf-data/{c}.json"))["closes"] if x and D.cut_ok(d)} for c in SLEEVE_ETF}
    return SX


def trend_pick(px, p, n, codes):
    """p일(전 거래일)까지 값만: 달 끝 종가(p가 든 달은 p 종가)로 '마지막 > 최근 n개 평균'인 코드. 자료가 n달 안 되면 고르지 않음."""
    out = []
    for c in codes:
        ds = sorted(d for d in px[c] if d <= p)
        ends = {}
        for d in ds:
            ends[d[:6]] = px[c][d]
        vals = [ends[m] for m in sorted(ends)]
        if len(vals) >= n and vals[-1] > sum(vals[-n:]) / n:
            out.append(c)
    return out


def account_x(cfg, lo=D.LO, hi=D.HI):
    """regime_dev.account와 같은 셈 + 새 봇(cfg에 sleeve 없으면 regime_dev.account와 한 줄도 다르지 않아야 함 · 시험 3)."""
    sl = cfg.get("sleeve")
    base, etf, br, flow = D.data()
    if D.FEAT is None or D.FEAT[0] is not D.DATA:
        D.FEAT = (D.DATA, D.features(etf, br, flow, D.short_breadth() if br else {}))
    feat = D.FEAT[1]
    st = D.states(feat, cfg)
    sx = sleeve_px() if sl else {}
    codes = UNIVERSE[sl["u"]] if sl else ()
    days = [d for d in sorted(base) if lo <= d <= hi and all(d in etf[c] for c in D.ETF)]      # 날 목록은 지금 판과 같음
    last_px = {}

    def px(c, day):                                              # 그날 값이 없으면 앞 값(바뀜 0) · 앞 값도 없으면 None
        if day in sx[c]:
            last_px[c] = sx[c][day]
        return last_px.get(c)
    A, vb, ve, code, cash = 1.0, 1.0, 0.0, None, 0.0
    sv = {}
    navs, nst = {days[0]: 1.0}, {}
    pending = None
    trims = [0, 0, 0]
    slack = [0.0]
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        vb *= base[d][0] / base[p][0]
        if code:
            ve *= etf[code][d] / etf[code][p]
        for c in codes:
            prev_c = last_px.get(c)
            now_c = px(c, d)
            if c in sv and prev_c and now_c:
                sv[c] *= now_c / prev_c
        A = vb + ve + cash + sum(sv.values())
        s_prev = st.get(p, "횡보")
        tgt = D.targets(s_prev, cfg, feat.get(p))
        if pending != s_prev or d[:6] != p[:6]:
            fb, c_new, fe = tgt
            room = fb * base[d][1] + (1 - fb)
            fe = min(fe, room)
            tb, te = fb * A, fe * A
            cost = (D.COST_BASE_DOWN * max(0, vb - tb) + D.COST_BASE_UP * max(0, tb - vb))
            if c_new == code:
                cost += D.COST_ETF * abs(te - ve)
            else:
                cost += D.COST_ETF * (ve + te)
            # 새 봇: 달 첫날만 다시 고름 · 국면만 바뀐 날은 고른 것 그대로 두되 남는 몫을 넘으면 줄임
            if sl:
                cap = max(0.0, room - fe) * A
                if d[:6] != p[:6]:
                    pick = [c for c in trend_pick(sx, p, sl["n"], codes) if last_px.get(c)]
                    want = {c: min(sl["w"] * A, cap) / len(pick) for c in pick} if pick else {}
                else:
                    tot = sum(sv.values())
                    k = min(1.0, cap / tot) if tot > 0 else 0.0
                    want = {c: v * k for c, v in sv.items()}
                cost += D.COST_ETF * sum(abs(want.get(c, 0.0) - sv.get(c, 0.0)) for c in set(want) | set(sv))
                sv = {c: v for c, v in want.items() if v > 0}
            A -= cost
            vb, ve, code = fb * A, fe * A, (c_new if fe > 0 else None)
            if not code:
                ve = 0.0
            if sl and sv:                                        # 비용 뒤 A에 맞춰 봇 몫도 같은 비율로
                tot = sum(sv.values())
                cap = max(0.0, room - fe) * A
                k = min(1.0, cap / tot) if tot > 0 else 0.0
                sv = {c: v * k for c, v in sv.items()}
            cash = A - vb - ve - sum(sv.values())
            pending = s_prev
        elif cash < -vb * base[d][1] - 1e-12:
            need = -vb * base[d][1] - cash
            tot = sum(sv.values())
            if tot > 0:                                          # 새 봇부터 팖(같은 비율)
                cut = min(tot, need / (1 - D.COST_ETF))
                sv = {c: v * (1 - cut / tot) for c, v in sv.items()}
                sv = {c: v for c, v in sv.items() if v > 1e-15}
                cash += cut * (1 - D.COST_ETF)
                trims[2] += 1
                need = -vb * base[d][1] - cash
            if code and need > 1e-12:
                cut = min(ve, need / (1 - D.COST_ETF))
                ve -= cut
                cash += cut * (1 - D.COST_ETF)
                trims[0] += 1
                if ve <= 1e-15:
                    ve, code = 0.0, None
        if cash < -vb * base[d][1] - 1e-12:
            c = base[d][1]
            x = (-c * vb - cash) / (1 - D.COST_BASE_DOWN - c)
            vb -= x
            cash += x * (1 - D.COST_BASE_DOWN)
            trims[1] += 1
        slack[0] = min(slack[0], cash + vb * base[d][1])
        navs[d] = vb + ve + cash + sum(sv.values())
        nst[d] = s_prev
    account_x.trims, account_x.base_trims, account_x.sleeve_trims, account_x.min_slack = trims[0], trims[1], trims[2], slack[0]
    return navs, nst


_ORIG_ACCOUNT = D.account                                        # 시험 3: 새 봇 없으면 이것과 같아야 함
D.account = account_x                                            # D.stats가 읽는 account 속성도 이 함수의 것


def months(navs):
    ds = sorted(navs)
    mo = {}
    for j in range(1, len(ds)):
        mo[ds[j][:6]] = mo.get(ds[j][:6], 1.0) * (navs[ds[j]] / navs[ds[j - 1]])
    return {m: v - 1 for m, v in mo.items()}


def score(navs, nst):
    r = D.stats(navs, nst)
    allm = months(navs)
    mo = {m: v for m, v in allm.items() if FIRST_FULL <= m <= LAST_FULL}
    neg = sorted(m for m, v in mo.items() if v < 0)
    r.update({"loss_months": len(neg), "months": len(mo), "neg_list": neg, "month_pct": {m: round(v * 100, 3) for m, v in mo.items()},
              "worst_full_month_raw": min(mo.values()), "worst_full_month_pct": round(min(mo.values()) * 100, 3),
              "within": all(v["worst_day_raw"] >= DAY_LIM for v in r["by_kind"].values()) and min(mo.values()) >= MONTH_LIM,
              "loss_months_front": sum(1 for m in neg if m < "202201"), "loss_months_back": sum(1 for m in neg if m >= "202201"),
              "partial_months_ref": {m: round(v * 100, 3) for m, v in allm.items() if m not in mo},
              "min_cash_slack": account_x.min_slack, "etf_trims": account_x.trims, "sleeve_trims": account_x.sleeve_trims})
    return r


def log(rec):
    BOX.mkdir(parents=True, exist_ok=True)
    with open(EVALS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def evaluate(cfg, label):
    key = json.dumps(cfg, sort_keys=True, ensure_ascii=False)
    log({"status": "STARTED", "key": key, "label": label, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    try:
        r = score(*account_x(cfg))
    except Exception as e:
        log({"status": "FAILED", "key": key, "error": repr(e)})
        raise
    log({"status": "DONE", "key": key, "annual_pct": r["annual_pct"], "loss_months": r["loss_months"],
         "worst_day_pct": r["worst_day_pct"], "worst_full_month_pct": r["worst_full_month_pct"]})
    return r


def cname(sl):
    return f"{sl['u']}_n{sl['n']}_w{sl['w']}"


def grid():
    out = [("기준(지금 판)", dict(FINAL))]
    for u in ("U4", "U3"):
        for n in N_MON:
            for w in W:
                sl = {"u": u, "n": n, "w": w}
                out.append((cname(sl), dict(FINAL, sleeve=sl)))
    return out


def eligible(x, base):
    """채택 조건(새 봇 · 남는 돈으로 더 벌기): 잣대 안 · 연 ≥ 기준 + 1%p · 가장 나쁜 완료 달 ≥ 기준 − 1%p · 손실 달 ≤ 기준 + 2."""
    return (x["within"] and x["annual_raw"] >= base["annual_raw"] + ANN_GAIN
            and x["worst_full_month_raw"] >= base["worst_full_month_raw"] - MONTH_SLACK and x["loss_months"] <= base["loss_months"] + LOSS_SLACK)


def neighbors(sl):
    """새 봇 이웃: n ± 2달 · w ± 0.1(격자 안) · 바구니 반대쪽."""
    out = [("n", sl["n"] - 2), ("n", sl["n"] + 2)]
    i = W.index(sl["w"])
    out += [("w", W[j]) for j in (i - 1, i + 1) if 0 <= j < len(W)]
    out.append(("u", "U3" if sl["u"] == "U4" else "U4"))
    return out


def lock_body():
    root = check_root()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    body = {"root": str(root)}
    body.update({f: sha(root / f) for f in CODE_FILES})
    body.update({k: sha(v) for k, v in loader_files().items()})
    body["base_ledger:" + M.name(BASE) + ".csv"] = sha(M.BASES / f"{M.name(BASE)}.csv")
    body["snapshot:" + Path(D.SNAP).name] = sha(D.SNAP)
    return body


def verify_inputs(path=None):
    want = json.loads(Path(path or LOCK).read_text())
    have = lock_body()
    bad = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k))
    if bad:
        sys.exit("입력 잠금이 다름(멈춤): " + json.dumps(bad, ensure_ascii=False))
    return want


KEEP = ("annual_pct", "annual_raw", "worst_day_pct", "worst_full_month_pct", "worst_full_month_raw", "mdd_report_pct", "loss_months",
        "loss_months_front", "loss_months_back", "within", "years_pct", "halves_report", "neg_list", "month_pct", "partial_months_ref",
        "min_cash_slack", "etf_trims", "sleeve_trims")


def run():
    verify_inputs()
    D.BASE_CSV = M.BASES / f"{M.name(BASE)}.csv"
    D.DATA, D.FEAT = None, None
    rows = []
    for name, cfg in grid():
        r = evaluate(cfg, "고정")
        rows.append({"name": name, "sleeve": cfg.get("sleeve"), **{k: r[k] for k in KEEP}})
    base = rows[0]
    ok = sorted([x for x in rows[1:] if eligible(x, base)], key=lambda x: (-x["annual_raw"], x["name"]))
    checked, final, used = [], None, 0
    for x in ok:
        nbs = neighbors(x["sleeve"])
        if used + len(nbs) > NB_CAP:
            break
        res, good = {}, True
        for a, v in nbs:
            nr = evaluate(dict(FINAL, sleeve=dict(x["sleeve"], **{a: v})), "이웃")
            used += 1
            keep = nr["within"] and (nr["annual_raw"] - base["annual_raw"]) * 2 >= (x["annual_raw"] - base["annual_raw"]) \
                and nr["worst_full_month_raw"] >= base["worst_full_month_raw"] - MONTH_SLACK and nr["loss_months"] <= base["loss_months"] + LOSS_SLACK
            res[f"{a}={v}"] = {"annual_pct": nr["annual_pct"], "loss_months": nr["loss_months"], "worst_day_pct": nr["worst_day_pct"],
                               "worst_full_month_pct": nr["worst_full_month_pct"], "keep": keep}
            good = good and keep
        checked.append({"name": x["name"], "neighbors": res, "robust": good})
        if good:
            final = x
            break
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(json.dumps({"verdict": "XASSET_CANDIDATE" if final else "NO_IMPROVEMENT", "final": final, "base": base, "checked": checked,
                      "eligible_count": len(ok), "rows_count": len(rows), "neighbor_evals": used,
                      "rules": {"day": DAY_LIM, "month": MONTH_LIM, "ann_gain": ANN_GAIN, "month_slack": MONTH_SLACK, "loss_slack": LOSS_SLACK,
                                "neighbor_cap": NB_CAP},
                      "period": "2017-02-01 ~ 2026-09-15 · 공식 달은 완료 114달(2017-03 ~ 2026-08)"}, ensure_ascii=False))


def cut():
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    code = ("import os,sys,json;sys.path.insert(0,'research');import xasset as X,mix54_run as M,regime_dev as D;"
            "D.BASE_CSV=M.BASES/f'{M.name(X.BASE)}.csv';D.DATA,D.FEAT=None,None;"
            "c=dict(X.FINAL,sleeve=json.loads(os.environ['XX_CFG']));n,s=D.account(c);print(json.dumps([n,s]))")
    res = []
    for extra in ({"u": "U4", "n": 6, "w": 0.3}, {"u": "U3", "n": 10, "w": 0.2}, {"u": "U4", "n": 10, "w": 0.1}):
        env = dict(os.environ, XX_CFG=json.dumps(extra), REG_CUT="")
        fn, fs = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        for c in cuts:
            env["REG_CUT"] = c
            pn, ps = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            ds = [d for d in pn if d < c]
            bad = [d for d in ds if abs(pn[d] - fn[d]) > 1e-12 or ps.get(d) != fs.get(d)]
            res.append({"cfg": extra, "cut": c, "days": len(ds), "diff_days": len(bad)})
    print(json.dumps({"pass": all(r["diff_days"] == 0 for r in res), "runs": res}, ensure_ascii=False))


def write_lock():
    BOX.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock_body(), ensure_ascii=False, indent=1))
    print(LOCK.read_text())


if __name__ == "__main__":
    {"run": run, "cut": cut, "lock": write_lock}[sys.argv[1]]()
