"""REPLAY-0001 골든 시험 실행기.

사용: python3 -I tests/run_golden.py <REPLAY-0001 폴더> <결과 json 경로>
- 네트워크 연결을 막고, KIS/DART/PAPER/DISCORD 환경변수를 지운 뒤 실행합니다.
- 운영 폴더 모듈을 import하지 않았는지 확인합니다.
- 기대값은 fixtures/golden.json(PREREG-LOCK과 같은 손셈 값)이며, 이 파일은 기대값을 고치지 않습니다.
"""
import os, sys, json, time, socket, resource, hashlib, importlib.util
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction

for k in list(os.environ):
    if any(w in k.upper() for w in ("KIS", "DART", "PAPER", "DISCORD")):
        del os.environ[k]


def _blocked(*a, **k):
    raise OSError("network blocked in REPLAY-0001 tests")


socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked

ROOT = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
OPS = "/home/user/stock-dash"
spec = importlib.util.spec_from_file_location("account_kernel", os.path.join(ROOT, "account_kernel.py"))
K = importlib.util.module_from_spec(spec)
spec.loader.exec_module(K)

Q = Decimal("1e-12")


def ratio(s):
    f = Fraction(s)
    return (Decimal(f.numerator) / Decimal(f.denominator)).quantize(Q, rounding=ROUND_HALF_EVEN)


def cmp(exp, act, path, bad):
    if exp is None:
        if act is not None:
            bad.append({"path": path, "expected": None, "actual": str(act)})
    elif isinstance(exp, bool):
        if act is not exp:
            bad.append({"path": path, "expected": exp, "actual": str(act)})
    elif isinstance(exp, int):
        ok = isinstance(act, (int, Decimal)) and not isinstance(act, bool) and Decimal(act) == Decimal(exp) \
            and Decimal(act) == Decimal(act).to_integral_value()
        if not ok:
            bad.append({"path": path, "expected": exp, "actual": str(act)})
    elif isinstance(exp, str):
        if isinstance(act, Decimal):
            if ratio(exp) != act.quantize(Q, rounding=ROUND_HALF_EVEN):
                bad.append({"path": path, "expected": exp, "actual": str(act)})
        elif act != exp:
            bad.append({"path": path, "expected": exp, "actual": str(act)})
    elif isinstance(exp, dict):
        if not isinstance(act, dict):
            bad.append({"path": path, "expected": "dict", "actual": str(act)})
            return
        for k, v in exp.items():
            if k not in act:
                bad.append({"path": path + "." + k, "expected": v, "actual": "<없음>"})
            else:
                cmp(v, act[k], path + "." + k, bad)
        if path.endswith("positions") or path.endswith("navs") and not exp:
            extra = [k for k in act if k not in exp]
            if extra:
                bad.append({"path": path, "expected": "키 " + str(sorted(exp)), "actual": "추가 키 " + str(extra)})
    elif isinstance(exp, list):
        if not isinstance(act, list) or len(act) != len(exp):
            bad.append({"path": path, "expected": "길이 %d" % len(exp),
                        "actual": "길이 %s" % (len(act) if isinstance(act, list) else type(act).__name__)})
            return
        for i, (e, a) in enumerate(zip(exp, act)):
            cmp(e, a, "%s[%d]" % (path, i), bad)


def invariants(out):
    """모든 사례 공통 불변식(PREREG-LOCK 2장). 체결 목록 · 입출금으로 따로 셈."""
    if out.get("status") != "OK":
        return {"applicable": False}
    res = {"applicable": True}
    res["cash_nonneg"] = out["min_cash"] is None or out["min_cash"] >= 0
    res["qty_int_nonneg"] = all(v >= 0 and v == v.to_integral_value() for v in out["positions"].values())
    c = sum((f["amount"] for f in out["flows"]), Decimal(0))
    for f in out["fills"]:
        if f["side"] == "BUY":
            c -= f["notional"] + f["fee"] + f["tax"]
        else:
            c += f["notional"] - f["fee"] - f["tax"]
    res["cash_conservation"] = (c == out["cash"])
    res["cash_conservation_error_won"] = str(out["cash"] - c)
    ok_id = True
    for d, n in out["navs"].items():
        if n["cash_td"] != n["settled"] + n["receivable"] - n["payable"]:
            ok_id = False
        if n["nav"] is not None and n["nav"] != n["cash_td"] + n["mv"]:
            ok_id = False
    res["nav_identity"] = ok_id
    res["no_hidden_borrow"] = out["max_gross_exposure"] <= 1
    res["all"] = all(v for k, v in res.items() if isinstance(v, bool))
    return res


def derived(out):
    if out.get("status") == "OK":
        out["fills_count"] = len(out["fills"])
        out["trades_count"] = len(out["trades"])
        out["total_qty"] = sum(out["positions"].values(), Decimal(0))
    return out


# ---- 원본 a_mtm.account()의 정의만 옮긴 대조용(numpy 대신 list, 식은 같게) ----
def asis_account(days, ledger, base, prices):
    D = list(days); n = len(D); idx = {d: i for i, d in enumerate(D)}
    px, buys, sells = {}, {}, {}
    for t, (c, b, e, p, k) in enumerate(ledger):
        if b not in idx or e not in idx:
            continue
        if c not in px:
            px[c] = dict(prices.get(c, {}).get("rows") or [])
        buys.setdefault(idx[b], []).append(t)
        sells.setdefault(idx[e], []).append(t)
    E = [1.0] * n; val, last, units = {}, {}, {}
    min_cash, max_exp, entered = 1.0, 0.0, 0
    for i in range(1, n):
        e_prev = E[i - 1]
        cash = e_prev - sum(val.values())
        for t in list(val):
            v = px[ledger[t][0]].get(D[i])
            if v:
                val[t] *= v / last[t]; last[t] = v
        for t in sells.get(i, []):
            if t in val:
                cash += units[t] * (1 + ledger[t][3] / 100); val.pop(t)
        eq = cash + sum(val.values()) + base[i] * e_prev
        for t in buys.get(i, []):
            c, b, e, p, k = ledger[t]; v = px[c].get(D[i])
            if v and idx[e] > i:
                units[t] = eq * k / 10; val[t] = units[t]; last[t] = v; entered += 1
        E[i] = eq
        # 계측(원본에 없는 관측만): 산 뒤 현금 = 계좌 − 들고 있는 몫
        min_cash = min(min_cash, eq - sum(val.values()))
        if eq > 0:
            max_exp = max(max_exp, sum(val.values()) / eq)
    rets = [0.0] + [E[i] / E[i - 1] - 1 for i in range(1, n)]
    return rets, min_cash, max_exp, entered


def close(a, b):
    return abs(float(a) - float(Fraction(b))) < 1e-12


def main():
    t0 = time.time()
    g = json.load(open(os.path.join(ROOT, "fixtures", "golden.json"), encoding="utf-8"))
    results, kernel_out = [], {}
    for c in g["cases"]:
        subs = []
        for s in c["subs"]:
            out = derived(K.run(s["config"], s["events"]))
            kernel_out[s["sub"]] = out
            bad = []
            cmp(s["expect"], out, s["sub"], bad)
            inv = invariants(out)
            ok = not bad and (not inv["applicable"] or inv["all"])
            subs.append({"sub": s["sub"], "pass": ok, "mismatches": bad, "invariants": inv})
        results.append({"case": c["case"], "pass": all(x["pass"] for x in subs), "subs": subs})
    asis = []
    for x in g["asis_contrast"]:
        rets, mc, me, ent = asis_account(x["days"], x["ledger"], [0.0] * len(x["days"]), x["prices"])
        ex = x["expect_defect"]
        got = {"returns": rets, "min_cash_rel": mc, "max_exposure": me, "entered": ent}
        hit = True
        if "returns" in ex:
            hit &= all(close(a, b) for a, b in zip(rets, ex["returns"])) and len(rets) == len(ex["returns"])
        if "min_cash_rel" in ex:
            hit &= close(mc, ex["min_cash_rel"])
        if "max_exposure" in ex:
            hit &= close(me, ex["max_exposure"])
        k = kernel_out.get(x["pairs_with"])
        kern = None
        if x["id"] == "X8":
            kern = {"min_cash": str(k["min_cash"]), "max_gross_exposure": str(k["max_gross_exposure"])}
        elif x["id"] == "X9":
            kern = {"day_return": str(k["returns"]["2026-01-05"])}
            hit &= ratio(ex["kernel_day_return"]) == k["returns"]["2026-01-05"].quantize(Q)
        elif x["id"] == "X14":
            tot = k["navs"]["2026-01-06"]["nav"] / Decimal(1000000) - 1
            kern = {"total_return": str(tot)}
            hit &= ratio(ex["kernel_total_return"]) == tot.quantize(Q)
        asis.append({"id": x["id"], "pairs_with": x["pairs_with"], "asis": got, "kernel": kern,
                     "result": "DEFECT_EXPOSED" if hit else "NOT_AS_EXPECTED",
                     "note": "원본 as-is 결함 노출 시험. 신규 커널 판정과 따로 셈"})
    secs = time.time() - t0
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    ops_mods = sorted(m for m, v in sys.modules.items()
                      if getattr(v, "__file__", None) and os.path.abspath(v.__file__).startswith(OPS + os.sep))
    n_pass = sum(r["pass"] for r in results)
    verdict = "VERIFIED_SYNTHETIC" if n_pass == len(results) == 20 else "NOT_VERIFIED"
    doc = {"task": "REPLAY-0001", "kernel_version": K.KERNEL_VERSION,
           "golden_sha256": hashlib.sha256(open(os.path.join(ROOT, "fixtures", "golden.json"), "rb").read()).hexdigest(),
           "kernel_sha256": hashlib.sha256(open(os.path.join(ROOT, "account_kernel.py"), "rb").read()).hexdigest(),
           "cases_total": len(results), "cases_pass": n_pass, "kernel_verdict": verdict,
           "cases": results, "asis_contrast": asis,
           "budget": {"seconds": round(secs, 3), "max_rss_mb": round(rss_mb, 1), "limit_seconds": 120, "limit_mb": 256,
                      "within": secs <= 120 and rss_mb <= 256},
           "isolation": {"network": "socket connect blocked", "env_removed": ["KIS*", "DART*", "PAPER*", "DISCORD*"],
                         "ops_modules_imported": ops_mods},
           "scope_note": "합성 회계 시험만. 전략 수익성 · 모의 준비 · 실전 합격을 뜻하지 않음"}
    json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(verdict, "%d/%d" % (n_pass, len(results)), "%.2fs" % secs, "%.0fMB" % rss_mb, "ops_mods", ops_mods)
    for r in results:
        if not r["pass"]:
            for s in r["subs"]:
                if not s["pass"]:
                    print(" FAIL", s["sub"], s["mismatches"][:4], {k: v for k, v in s["invariants"].items() if v is False})
    for a in asis:
        print(" ASIS", a["id"], a["result"])


main()
