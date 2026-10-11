"""MONTH-POS-0055 — 손실 달을 이익 달로 바꾸기(사용자 2026-10-11 "이제 손실달을 양수달로 전환하는 연구해줘").
출발: MIX-0054 최종(15분봉 뺌 · 1일봉 0.5 · 바구니 0.3 · 덧붙임 n24 · persist 3 · r10m5 · 레버리지 0.4 · 횡보 인버스 0.4) — 116달 중 손실 41달.
진단(사전등록 전에 봄 · 공개): 손실 41달 가운데 36달은 바탕(봇) 장부도 손실 · 바탕만 손실 달 46.
새 규칙(그달 지킴이 · 판정 t날 장 끝 그달 누적 손익 → 실행 t+1날 종가 · 그달 남은 날만 · 다음 달 첫날 원래대로):
  손실 멈춤 k: 그달 누적 ≤ −k%이면 · 이익 잠금 g: 그달 누적 ≥ +g%이면 → 행동 a
  a = A0 덧붙임 0 · A1 덧붙임 0 + 바탕 몫 0.5 · A2 덧붙임 0 + 바탕 몫 0(현금)
  내림장 인버스 d(regime_dev down_inv · 0 또는 0.4)도 함께 시험.
계좌 셈은 regime_dev.account와 같은 식(빚 없음 · 비용 ETF 0.05% · 바탕 줄일 때 0.30% · 늘릴 때 0.05%)에 지킴이만 더함.
python3 research/month_guard.py run       → 고정 격자 + 고르기 + 이웃(기록 evals.jsonl)
python3 research/month_guard.py cut       → 자르기 시험(REG_CUT로 자료를 그날까지만 읽고 앞날까지 같아야 함)"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("REG_BOX", "MONTH-POS-0055")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import mix54_run as M  # noqa: E402
import regime_dev as D  # noqa: E402
import regime_rules4 as R4  # noqa: E402

BOX = ROOT / "research-exchange/claude-to-gpt/MONTH-POS-0055"
EVALS = BOX / "evals.jsonl"
BASE = (0.5, 0.3)
FINAL = dict(D.R0, **M.OVERLAYS["L0.4_S0.4"])
KS = [None, 0.02, 0.04, 0.06]
GS = [None, 0.03, 0.06]
ACTS = {"A0": 1.0, "A1": 0.5, "A2": 0.0}          # 지킴이 때 바탕 몫 fb(덧붙임은 늘 0)
DOWN_INV = [0.0, 0.4]
DAY_LIM, MONTH_LIM = -0.15, -0.15
NB_CAP = 300
LOSS_CUT, ANN_FLOOR = 4, 0.9                            # 손실 달 4개 이상 줄고 · 연수익 ≥ 최종 × 0.9


def account_guard(cfg, guard, lo=D.LO, hi=D.HI):
    """regime_dev.account 그대로 + 그달 지킴이. guard = {"k": 손실 문턱 | None, "g": 이익 문턱 | None, "fb": 지킴이 때 바탕 몫}."""
    base, etf, br, flow = D.data()
    if D.FEAT is None or D.FEAT[0] is not D.DATA:
        D.FEAT = (D.DATA, D.features(etf, br, flow, D.short_breadth() if br else {}))
    feat = D.FEAT[1]
    st = D.states(feat, cfg)
    days = [d for d in sorted(base) if lo <= d <= hi and all(d in etf[c] for c in D.ETF)]
    A, vb, ve, code, cash = 1.0, 1.0, 0.0, None, 0.0
    navs, nst = {days[0]: 1.0}, {}
    pending = None
    trims = [0, 0]
    slack = [0.0]
    mstart = 1.0                     # 그달 시작 NAV(전달 마지막 날 종가 NAV)
    guard_on, guard_days = False, 0
    k, g, gfb = guard.get("k"), guard.get("g"), guard.get("fb", 1.0)
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        if d[:6] != p[:6]:
            mstart = navs[p]
            guard_on = False
        vb *= base[d][0] / base[p][0]
        if code:
            ve *= etf[code][d] / etf[code][p]
        A = vb + ve + cash
        s_prev = st.get(p, "횡보")
        tgt = D.targets(s_prev, cfg, feat.get(p))
        # 지킴이 판정: 어제(p) 장 끝 그달 누적(같은 달일 때만) → 오늘(d) 종가에 실행
        trig = False
        if not guard_on and d[:6] == p[:6]:
            mtd = navs[p] / mstart - 1
            if (k is not None and mtd <= -k) or (g is not None and mtd >= g):
                guard_on, trig = True, True
        if guard_on:
            tgt = (gfb, None, 0.0)
        band = cfg.get("band")
        cur_w = 0.0 if code is None else ve / A if A > 0 else 0.0
        same_kind = code is None or code == tgt[1]
        drift = band is not None and same_kind and A > 0 and abs(cur_w - min(tgt[2], tgt[0] * base[d][1] + (1 - tgt[0]))) > band
        key = ("G", d[:6]) if guard_on else s_prev
        if pending != key or d[:6] != p[:6] or drift or trig:
            fb, c_new, fe = tgt
            room = fb * base[d][1] + (1 - fb)
            fe = min(fe, room)
            tb, te = fb * A, fe * A
            cost = (D.COST_BASE_DOWN * max(0, vb - tb) + D.COST_BASE_UP * max(0, tb - vb))
            if c_new == code:
                cost += D.COST_ETF * abs(te - ve)
            else:
                cost += D.COST_ETF * ((ve if code else 0.0) + te)
            A -= cost
            vb, ve, code = fb * A, fe * A, (c_new if fe > 0 else None)
            if not code:
                ve = 0.0
            cash = A - vb - ve
            pending = key
        elif code and cash < -vb * base[d][1] - 1e-12:
            need = -vb * base[d][1] - cash
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
        guard_days += guard_on
        navs[d] = vb + ve + cash
        nst[d] = s_prev
    D.account.trims, D.account.base_trims, D.account.min_slack = trims[0], trims[1], slack[0]
    account_guard.guard_days = guard_days
    return navs, nst


def months(navs):
    ds = sorted(navs)
    mo = {}
    for j in range(1, len(ds)):
        mo[ds[j][:6]] = mo.get(ds[j][:6], 1.0) * (navs[ds[j]] / navs[ds[j - 1]])
    return {m: v - 1 for m, v in mo.items()}


def score(navs, nst):
    r = D.stats(navs, nst)
    mo = months(navs)
    neg = sorted(m for m, v in mo.items() if v < 0)
    r.update({"loss_months": len(neg), "months": len(mo), "neg_list": neg,
              "loss_months_front": sum(1 for m in neg if m < "202201"), "loss_months_back": sum(1 for m in neg if m >= "202201"),
              "within": all(v["worst_day_raw"] >= DAY_LIM and v["worst_month_raw"] >= MONTH_LIM for v in r["by_kind"].values()),
              "guard_days": getattr(account_guard, "guard_days", 0), "min_cash_slack": D.account.min_slack})
    return r


def log(rec):
    BOX.mkdir(parents=True, exist_ok=True)
    with open(EVALS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def evaluate(cfg, guard, label):
    key = json.dumps({"cfg": cfg, "guard": guard}, sort_keys=True, ensure_ascii=False)
    log({"status": "STARTED", "key": key, "label": label, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    try:
        r = score(*account_guard(cfg, guard))
    except Exception as e:
        log({"status": "FAILED", "key": key, "error": repr(e)})
        raise
    log({"status": "DONE", "key": key, "annual_pct": r["annual_pct"], "loss_months": r["loss_months"], "worst_day_pct": r["worst_day_pct"],
         "worst_month_pct": r["worst_month_pct"]})
    return r


def grid():
    out = [("기준", {"down_inv": 0.0}, {})]
    out.append(("내림 인버스만", {"down_inv": 0.4}, {}))
    for di in DOWN_INV:
        for kk in KS:
            for gg in GS:
                if kk is None and gg is None:
                    continue
                for a, fb in ACTS.items():
                    out.append((f"d{di}_k{kk}_g{gg}_{a}", {"down_inv": di}, {"k": kk, "g": gg, "fb": fb}))
    return out


def neighbors(cfg, guard):
    out = [("rule", a, v) for a, v in R4.neighbors(cfg)]
    for name, axis in (("k", KS), ("g", GS)):
        x = guard.get(name)
        if x is not None:
            i = axis.index(x)
            for jj in (i - 1, i + 1):
                if 0 <= jj < len(axis) and axis[jj] is not None:
                    out.append(("guard", name, axis[jj]))
    return out


def run():
    D.BASE_CSV = M.BASES / f"{M.name(BASE)}.csv"
    D.DATA, D.FEAT = None, None
    rows = []
    for name, cx, gd in grid():
        cfg = dict(FINAL, **cx)
        r = evaluate(cfg, gd, "고정")
        rows.append({"name": name, "cfg_extra": cx, "guard": gd, **{k: r[k] for k in ("annual_pct", "annual_raw", "worst_day_pct", "worst_month_pct",
                     "mdd_report_pct", "loss_months", "loss_months_front", "loss_months_back", "within", "years_pct", "halves_report", "guard_days",
                     "min_cash_slack", "neg_list")}})
    base = rows[0]
    floor = base["annual_raw"] * ANN_FLOOR
    ok = sorted([x for x in rows[1:] if x["within"] and x["annual_raw"] >= floor and x["loss_months"] <= base["loss_months"] - LOSS_CUT],
                key=lambda x: (x["loss_months"], -x["annual_raw"], x["name"]))
    checked, final, used = [], None, 0
    for x in ok:
        cfg = dict(FINAL, **x["cfg_extra"])
        nbs = neighbors(cfg, x["guard"])
        if used + len(nbs) > NB_CAP:
            break
        res, good = {}, True
        for kind, a, v in nbs:
            c2, g2 = (dict(cfg, **{a: v}), x["guard"]) if kind == "rule" else (cfg, dict(x["guard"], **{a: v}))
            nr = evaluate(c2, g2, "이웃")
            used += 1
            keep = (base["loss_months"] - nr["loss_months"]) >= (base["loss_months"] - x["loss_months"]) / 2
            w = nr["within"] and nr["annual_raw"] >= floor
            res[f"{a}={v}"] = {"annual_pct": nr["annual_pct"], "loss_months": nr["loss_months"], "worst_day_pct": nr["worst_day_pct"],
                               "worst_month_pct": nr["worst_month_pct"], "within_and_floor": w, "half_cut": keep}
            good = good and w and keep
        checked.append({"name": x["name"], "loss_months": x["loss_months"], "annual_pct": x["annual_pct"], "neighbors": res, "robust": good})
        if good:
            final = x
            break
    (BOX / "evidence").mkdir(parents=True, exist_ok=True)
    (BOX / "evidence/all_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    out = {"verdict": "POS_MONTH_CANDIDATE" if final else "NO_IMPROVEMENT", "final": final, "base": base, "checked": checked,
           "eligible_count": len(ok), "rows_count": len(rows), "neighbor_evals": used,
           "rules": {"loss_cut": LOSS_CUT, "annual_floor_ratio": ANN_FLOOR, "day": DAY_LIM, "month": MONTH_LIM},
           "period": "2017-02-01 ~ 2026-09-15 · 116달(2017-02 · 2026-09는 부분 달)"}
    print(json.dumps(out, ensure_ascii=False))


def cut():
    """자르기 시험: 자른 날 뒤 자료를 처음부터 안 읽은 채(REG_CUT) 돌린 NAV가 자른 날 앞날까지 온 자료와 같아야 함."""
    cuts = ("20181015", "20200320", "20220615", "20240805", "20260701")
    guards = [{"k": 0.02, "g": 0.03, "fb": 0.0}, {"k": 0.04, "g": None, "fb": 0.5}, {"k": None, "g": 0.06, "fb": 1.0}]
    code = ("import os,sys,json;sys.path.insert(0,'research');import month_guard as G,mix54_run as M,regime_dev as D;"
            "D.BASE_CSV=M.BASES/f'{M.name(G.BASE)}.csv';D.DATA,D.FEAT=None,None;"
            "g=json.loads(os.environ['MG_GUARD']);c=dict(G.FINAL,down_inv=float(os.environ['MG_DI']));n,_=G.account_guard(c,g);print(json.dumps(n))")
    res = []
    for gd in guards:
        for di in ("0.0", "0.4"):
            env = dict(os.environ, MG_GUARD=json.dumps(gd), MG_DI=di, REG_CUT="")
            full = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            for c in cuts:
                env["REG_CUT"] = c
                part = json.loads(subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, check=True).stdout)
                ds = [d for d in part if d < c]
                bad = [d for d in ds if abs(part[d] - full[d]) > 1e-12]
                res.append({"guard": gd, "down_inv": di, "cut": c, "days": len(ds), "diff_days": len(bad)})
    print(json.dumps({"pass": all(r["diff_days"] == 0 for r in res), "runs": res}, ensure_ascii=False))


if __name__ == "__main__":
    {"run": run, "cut": cut}[sys.argv[1]]()
