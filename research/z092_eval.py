"""ACC-IMPROVE-0014 판정 — 판마다 날마다 NAV(Z_OUT CSV)로 앞 반 · 뒤 반 CAGR · 하루 · 달 최악 · MDD(보고만)를 세고, 사전등록대로 앞 반에서 고르고 뒤 반에서 시험.
python3 research/z092_eval.py <판 CSV 폴더> <F 기준 CSV>"""
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
    peak, mdd, eq = 1.0, 0.0, 1.0
    for _, r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    yrs = len(rets) / 245
    return {"cagr": round(((sel[-1][1] / base) ** (1 / yrs) - 1) * 100, 2), "worst_day": round(min(r for _, r in rets) * 100, 2),
            "worst_month": round((min(month.values()) - 1) * 100, 2), "mdd": round(mdd * 100, 2)}


def main():
    folder, fbase = Path(sys.argv[1]), sys.argv[2]
    out = {}
    for p in sorted(folder.glob("*.csv")):
        n = load(p)
        out[p.stem] = {"front": stats(n, *FRONT), "back": stats(n, *BACK)}
    F = load(fbase)
    out["F기준"] = {"front": stats(F, *FRONT), "back": stats(F, *BACK)}
    ok = {k: v for k, v in out.items() if k != "F기준" and v["front"]["worst_day"] > -15 and v["front"]["worst_month"] > -15}
    def devices(k):                     # 이름 꼴 cap{0|10|15|20}_park{0|1}_m{1.0|1.5|2.0}
        c, pk, m = k.split("_")
        return (c != "cap0") + (pk == "park1") + (m != "m1.0"), float(m[1:])
    # 앞 반 CAGR(0.1%p 반올림)이 가장 높은 판 · 같으면 장치 수가 적은 판 · 그다음 배수가 작은 판
    pick = max(ok, key=lambda k: (round(ok[k]["front"]["cagr"], 1), -devices(k)[0], -devices(k)[1])) if ok else None
    res = {"all": out, "pick": pick}
    if pick:
        b, fb = out[pick]["back"], out["F기준"]["back"]
        res["judge"] = {"back_limits": b["worst_day"] > -15 and b["worst_month"] > -15, "back_cagr_better": b["cagr"] > fb["cagr"]}
        res["judge"]["pass"] = all(res["judge"].values())
    for k, v in out.items():
        print(f"{k:28s} 앞 {v['front']} | 뒤 {v['back']}")
    print("고른 판(앞 반):", pick, "· 판정:", res.get("judge"))
    Path(folder / "eval.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
