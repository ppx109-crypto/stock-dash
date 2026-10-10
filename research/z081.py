"""D1-REGIME 공통 평가 도구 + H4(추세 규칙에도 시장 폭 50% 조건) — 사전등록: research-exchange/claude-to-gpt/D1-REGIME-0004/PREREG-H4.md
잣대: 운영과 같은 현금 한도 매수 · 복리 NAV(z080.account) · 씨앗 8 · 두 반 · 코스피 달 등락으로 상승(>+3%) · 횡보 · 하락(<−3%) 장별 연 환산.
python3 research/z081.py   (Z_OUT 환경 변수)"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import caps  # noqa: E402
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
import z077  # noqa: E402
import z080  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-REGIME-0004/evidence"))
SEEDS, NUDGE = 8, 0.05
KOSPI = {}
for r in json.loads(Path("/home/user/stock-dash/market-data/index_KOSPI.json").read_text())["rows"]:
    KOSPI[r["date"][:6]] = r["종가"]
KOSPI_START = 2026.16   # 2016 마지막 거래일 종가가 파일에 없어 2017-01-02 시가 근처 값으로 첫 달만 잼(장 나누기에만 씀)


def regime_of(m):
    ms = sorted(KOSPI)
    i = ms.index(m)
    prev = KOSPI[ms[i - 1]] if i else KOSPI_START
    x = KOSPI[m] / prev - 1
    return "상승" if x > .03 else ("하락" if x < -.03 else "횡보")


_B0 = z077.make_holds(5, rule.SLOPE)


def holds_b0(r):
    return _B0(r)


def holds_h4(r):
    return holds_b0(r) and nrl.BR.get(r["date"], 0) >= 50


def ledgers(which, holds):
    pool, since = (nrl.early, rule.SINCE) if which == "앞" else (nrl.inside, rule.MID)
    kw = dict(slots=nrl.SLOTS, since=since, apart=nrl.kin, realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE)
    out = []
    with z077.use(holds):
        for seed in range(SEEDS):
            rank = rule.order if seed == 0 else lab.jitter(rule.order, NUDGE, seed)
            g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, rank=rank, **kw)
            out.append({"seed": seed, "engine": g["연수익"], "led": g["매매목록"], "still": g["남은자리"], "end": g["끝날"], "since": since})
    return out


def monthly(navs):
    end = {}
    for d, v in navs:
        end[d[:6]] = v
    out, prev = {}, 1.0
    for m in sorted(end):
        out[m] = end[m] / prev - 1
        prev = end[m]
    return out


def ann(xs):
    p = 1.0
    for x in xs:
        p *= 1 + x
    return round((p ** (12 / len(xs)) - 1) * 100, 2) if xs else None


def med(xs):
    xs = sorted(x for x in xs if x is not None)
    return xs[len(xs) // 2] if xs else None


def evaluate(gs, acc_kw):
    seeds = []
    for g in gs:
        a, navs = z080.account(g["led"], g["still"], g["since"], g["end"], want_navs=True, **acc_kw)
        mr = monthly(navs)
        reg = {k: [x for m, x in mr.items() if regime_of(m) == k] for k in ("상승", "횡보", "하락")}
        down = [x for m, x in mr.items() if regime_of(m) != "상승"]
        seeds.append({"seed": g["seed"], **a, "regime": {k: ann(v) for k, v in reg.items()}, "down_side": ann(down),
                      "months": {k: len(v) for k, v in reg.items()}})
    return {"seeds": seeds,
            "cagr": med([s["cagr"] for s in seeds]), "cagr_spread": round(max(s["cagr"] for s in seeds) - min(s["cagr"] for s in seeds), 2),
            "worst_day": min((s["worst_day"] for s in seeds), key=lambda v: v[1]),
            "worst_month": min((s["worst_month"] for s in seeds), key=lambda v: v[1]),
            "mdd": min((s["mdd_daily"] for s in seeds), key=lambda v: v[1]),
            "regime": {k: med([s["regime"][k] for s in seeds]) for k in ("상승", "횡보", "하락")},
            "down_side": med([s["down_side"] for s in seeds]),
            "down_side_spread": round(max(s["down_side"] for s in seeds) - min(s["down_side"] for s in seeds), 2),
            "months": seeds[0]["months"]}


DEVICE = {"cap": z080.CAP, "vol": z080.VOL_DAY * 2}       # H2 + 흔들림 상한 × 2(사용자 표에서 고른 판 · 비교 기준 C0)
VARIANTS = {"R0 장치 없음": (holds_b0, {}), "C0 지금 규칙 + 장치": (holds_b0, DEVICE), "C1 H4 + 장치": (holds_h4, DEVICE)}


def main():
    out = {"task": "D1-REGIME-0004 H4", "device": {"cap": z080.CAP, "vol_day": z080.VOL_DAY * 2}}
    cache = {}
    for which in ("앞", "뒤"):
        out[which] = {}
        for name, (holds, kw) in VARIANTS.items():
            key = (which, holds.__name__)
            if key not in cache:
                cache[key] = ledgers(which, holds)
            r = evaluate(cache[key], kw)
            out[which][name] = r
            print(f"[{which}] {name}: 연복리 {r['cagr']}(폭 {r['cagr_spread']}) · 하루 {r['worst_day']} · 달 {r['worst_month']} · 고점 대비 {r['mdd']} · "
                  f"장별 연 {r['regime']} · 횡보+하락 연 {r['down_side']}(폭 {r['down_side_spread']}) · 달 수 {r['months']}", flush=True)
    c0 = {w: out[w]["C0 지금 규칙 + 장치"] for w in ("앞", "뒤")}
    c1 = {w: out[w]["C1 H4 + 장치"] for w in ("앞", "뒤")}
    limits = all(c1[w]["worst_day"][1] > -15 and c1[w]["worst_month"][1] > -15 for w in c1)
    down_better = all(c1[w]["down_side"] > c0[w]["down_side"] for w in c1)
    total_ok = all(c1[w]["cagr"] >= c0[w]["cagr"] - c0[w]["cagr_spread"] for w in c1)
    verdict = "ADOPT_CANDIDATE" if limits and down_better and total_ok else "REJECTED"
    out.update({"limits_ok": limits, "down_side_better_both": down_better, "total_within_spread": total_ok, "verdict": verdict})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "h4.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"판정: 한도 {limits} · 횡보+하락 두 반 모두 나음 {down_better} · 전체 연복리 폭 안 {total_ok} → {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
