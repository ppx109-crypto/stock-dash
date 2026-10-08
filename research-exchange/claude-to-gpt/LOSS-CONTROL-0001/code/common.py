"""MAX-RETURN-0001 공통 성적 함수(kernel2.report 위에 회전율 · 종목별 손익 · 최대 이익 종목을 얹음)."""
import kernel2 as KN

CASH = 1e7


def stats(r, periods, cash=CASH):
    KN.START_CASH = cash
    rep = KN.report(r["nav"], r["closed"], r["cal"], periods, r["gross"])
    for name, lo, hi in periods:
        a = rep.get(name)
        if not a:
            continue
        navs = [n for d, n, _ in r["nav"] if lo <= d <= hi]
        fl = [f for f in r["fills"] if lo <= str(f["fill_at"])[:8] <= hi and f["status"] in ("FILLED", "REDUCED")]
        yrs = KN._years(a["from"], a["to"]) or 1
        by = {}
        last = r["nav"][-1][0]
        for p in r["closed"] + r["open"]:
            ex = (p.get("last_exit") or last)[:8]
            if lo <= ex <= hi:
                by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
        tot = sum(by.values())
        top = max(by.items(), key=lambda x: x[1]) if by else (None, 0.0)
        end_nav = [n for d, n, _ in r["nav"] if d <= hi][-1]
        a.update({"turnover_per_year": round(sum(f["notional"] for f in fl) / 2 / (sum(navs) / len(navs)) / yrs, 2),
                  "end_nav_won": round(end_nav), "top_code": top[0],
                  "top_code_share_pct": round(top[1] / tot * 100, 1) if tot > 0 else None,
                  "pnl_by_code_top5": sorted(((c, round(v)) for c, v in by.items()), key=lambda x: -x[1])[:5]})
    return rep


def strip(rep):
    return {p: ({k: v for k, v in a.items() if k != "monthly"} if a else None) for p, a in rep.items()}
