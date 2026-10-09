"""D1-BEAR-0010 — 하락장 피하기 2: 손실 쿠션(사용자 선택 후보 위) — 전날까지 NAV 고점 대비 손실 dd로 허용 비중 = min(1, m × (15% − dd)), m = 1 ÷ 12%(자료 안 코스피 가장 큰 하루 하락 2026-03-04 −12.1%를 어림).
신호(모두 전날까지 값): A 코스피 전날 종가 < 200거래일 단순 평균 · B 시장 폭(nrl.BR, 전날) < 50%.
사전등록: research-exchange/claude-to-gpt/D1-BEAR-0009/PREREG.md · Z_TAG=raw|adj"""
import bisect
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import nrl  # noqa: E402
import z081  # noqa: E402
import z087  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-BEAR-0010/evidence"))
TAG = os.environ.get("Z_TAG", "raw")
K = json.loads(Path("/home/user/stock-dash/market-data/index_KOSPI.json").read_text())["rows"]
KD = [r["date"] for r in K]
KC = [r["종가"] for r in K]
BRD = sorted(nrl.BR)
CAP = 0.5


def kospi_below_200(d):
    i = bisect.bisect_left(KD, d) - 1          # 전날
    if i < 199:
        return False
    return KC[i] < sum(KC[i - 199:i + 1]) / 200


def breadth_below_50(d):
    i = bisect.bisect_left(BRD, d) - 1         # 전날
    return i >= 0 and nrl.BR[BRD[i]] < 50


CUSHION = (1 / 0.12, 0.15)
VARIANTS = {"B0 후보 ×2": None, "C 손실 쿠션": "cushion"}


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def main():
    out = {"task": "D1-BEAR-0010", "tag": TAG, "cushion": CUSHION}
    for which in ("앞", "뒤"):
        gs = z081.ledgers(which, z081.holds_b0)
        out[which] = {}
        for name, mc in VARIANTS.items():
            seeds = []
            for g in gs:
                a, navs = z087.account(g["led"], g["still"], g["since"], g["end"], want_navs=True, cushion=(CUSHION if mc == "cushion" else None))
                mr = z081.monthly(navs)
                seeds.append({**a, "regime": {k: z081.ann([x for m, x in mr.items() if z081.regime_of(m) == k]) for k in ("상승", "횡보", "하락")},
                              "down_side": z081.ann([x for m, x in mr.items() if z081.regime_of(m) != "상승"])})
            r = {"cagr": med([s["cagr"] for s in seeds]), "cagr_spread": round(max(s["cagr"] for s in seeds) - min(s["cagr"] for s in seeds), 2),
                 "worst_day": min((s["worst_day"] for s in seeds), key=lambda x: x[1]), "worst_month": min((s["worst_month"] for s in seeds), key=lambda x: x[1]),
                 "mdd": min((s["mdd_daily"] for s in seeds), key=lambda x: x[1]),
                 "regime": {k: med([s["regime"][k] for s in seeds]) for k in ("상승", "횡보", "하락")}, "down_side": med([s["down_side"] for s in seeds])}
            out[which][name] = r
            print(f"[{TAG} · {which}] {name}: 연복리 {r['cagr']}(폭 {r['cagr_spread']}) · 하루 {r['worst_day']} · 달 {r['worst_month']} · 고점 대비 {r['mdd']} · "
                  f"장별 {r['regime']} · 횡보+하락 {r['down_side']}", flush=True)
    judge = {}
    for name in list(VARIANTS)[1:]:
        b = {w: out[w]["B0 후보 ×2"] for w in ("앞", "뒤")}
        v = {w: out[w][name] for w in ("앞", "뒤")}
        judge[name] = {"mdd_ok": all(v[w]["mdd"][1] > -15 for w in v),
                       "limits": all(v[w]["worst_day"][1] > -15 and v[w]["worst_month"][1] > -15 for w in v),
                       "bear_not_worse": all(v[w]["regime"]["하락"] >= b[w]["regime"]["하락"] for w in v),
                       "cagr_pos": all(v[w]["cagr"] > 0 for w in v)}
        judge[name]["pass"] = all(judge[name].values())
        print(f"[{TAG}] {name} 판정 {judge[name]}", flush=True)
    out["judge"] = judge
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"cushion_{TAG}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
