"""ENG-BULL-0019 판정 — 판마다 날마다 NAV(Z_OUT CSV)로 앞 · 뒤 반 CAGR · 하루 · 달 최악 · 두 달 연속 최악 · MDD(보고만).
사전등록: 앞 반에서 'CAGR > F이고 하루 · 달 최악이 F보다 0.5%p 넘게 깊지 않은' 판 가운데 CAGR 최고를 고름.
뒤 반 PASS = CAGR > F · 하루 · 달 최악이 F보다 0.5%p 넘게 깊지 않음 · 하루 · 달 > −15%.
python3 research/z095_eval.py <판 CSV 폴더>   (F.csv가 폴더 안에 있어야 함)"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

FRONT = ("20170201", "20201231")
BACK = ("20210101", "20260916")


def load(p):
    return [(r["날"], float(r["NAV"])) for r in csv.DictReader(open(p, encoding="utf-8"))]


def stats(navs, lo, hi):
    prev = [v for d, v in navs if d < lo]
    sel = [(d, v) for d, v in navs if lo <= d <= hi]
    base = prev[-1] if prev else 1e8
    rets, last = [], base
    for d, v in sel:
        rets.append((d, v / last - 1))
        last = v
    month = defaultdict(lambda: 1.0)
    for d, r in rets:
        month[d[:6]] *= 1 + r
    ms = [month[m] for m in sorted(month)]
    two = min(ms[i] * ms[i + 1] for i in range(len(ms) - 1))
    peak, mdd, eq = 1.0, 0.0, 1.0
    for _, r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    yrs = len(rets) / 245
    return {"cagr": round(((sel[-1][1] / base) ** (1 / yrs) - 1) * 100, 2), "worst_day": round(min(r for _, r in rets) * 100, 2),
            "worst_month": round((min(ms) - 1) * 100, 2), "worst_2month": round((two - 1) * 100, 2), "mdd": round(mdd * 100, 2)}


def main():
    folder = Path(sys.argv[1])
    out = {p.stem: {"front": stats(load(p), *FRONT), "back": stats(load(p), *BACK)} for p in sorted(folder.glob("*.csv"))}
    F = out["F"]

    def ok_front(v):
        f, b = v["front"], F["front"]
        return f["cagr"] > b["cagr"] and f["worst_day"] >= b["worst_day"] - 0.5 and f["worst_month"] >= b["worst_month"] - 0.5
    elig = {k: v for k, v in out.items() if k != "F" and ok_front(v)}
    pick = max(elig, key=lambda k: (elig[k]["front"]["cagr"], k)) if elig else None
    res = {"all": out, "eligible": sorted(elig), "pick": pick}
    if pick:
        b, fb = out[pick]["back"], F["back"]
        res["judge"] = {"back_cagr_better": b["cagr"] > fb["cagr"], "back_day_ok": b["worst_day"] >= fb["worst_day"] - 0.5,
                        "back_month_ok": b["worst_month"] >= fb["worst_month"] - 0.5, "back_limits": b["worst_day"] > -15 and b["worst_month"] > -15}
        res["judge"]["pass"] = all(res["judge"].values())
    for k, v in out.items():
        print(f"{k:16s} 앞 {v['front']} | 뒤 {v['back']}")
    print("앞 반 자격:", sorted(elig), "· 고른 판:", pick, "· 판정:", res.get("judge"))
    (folder / "eval.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
