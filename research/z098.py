"""Z1-DELISTED-0023 — 참 시총 순위 효과(B1 − B0) · 사전등록 v3(PREREG.md) + 실행 전 정오표(ERRATA-PRE-RUN.md).
B0 = z081.ledgers("뒤", holds_b0) 그대로(살아남은 507종목끼리의 caps.tag 순위).
B1 = 같은 셈에서 '100위 안' 판정만 public-daily 시가총액(그날 상장 전체 · 6자리 숫자 · 끝자리 5/7/9 제외)의 참 순위로 바꿈.
     행은 복사본(순위 칸만 바꿈) · 시장 폭 BR · 월별 조용함 문턱 · 수급 · 목표가 · 비용 · 계좌는 B0 값 그대로(정오표 E1).
자르기 시험: T = 20231231까지 원자료를 잘라 가격 · 선 · 모양 · 시장 폭 · 수급 · 목표가 · 문턱 · 후보를 다시 만들어 B1을 다시 돌리고 T − 5거래일까지 비교.
python3 research/z098.py   (NRL_CACHE=/tmp/nrl-cache.pkl · Z_OUT)"""
import bisect
import csv
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
import caps  # noqa: E402
import final_group  # noqa: E402
import final_study as F  # noqa: E402
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402
import z077  # noqa: E402
import z081  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", str(ROOT / "research-exchange/claude-to-gpt/Z1-DELISTED-0023/evidence")))
T = "20231231"
KEEP_FROM = "20201201"                       # 뒤 반(2021-01-01 ~) 후보 행 · 시장 폭에 쓰는 날만 남김(자르기 판 다시 만들기용)
MISSING = ["091990", "003410", "012510", "008560", "032500", "079440", "031430", "003000", "084990", "095700",
           "036490", "235980", "268600", "010620", "042670", "000060", "278280", "005420", "319660"]   # PREREG v3 1절 · 6절


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------- 참 순위(public-daily) ----------
def in_population(code):
    return bool(re.fullmatch(r"[0-9]{6}", code)) and not code.endswith(("5", "7", "9"))


def true_ranks():
    """{(날, 코드): 참 순위}. 그날 public-daily(위 400) 가운데 모집단만 시가총액 순으로 줄 세움."""
    by_day = defaultdict(list)
    for f in sorted((ROOT / "public-daily").glob("*.csv")):
        with f.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if in_population(r["코드"]):
                    by_day[r["날"]].append((float(r["시가총액(억)"]), r["코드"]))
    out = {}
    for d, xs in by_day.items():
        for k, (_, c) in enumerate(sorted(xs, key=lambda x: (-x[0], x[1])), 1):
            out[(d, c)] = k
    return out, sorted(by_day)


# ---------- 표를 흘려 읽기(4GB를 한 번에 풀지 않음) ----------
def stream(path=lab.CACHE, block=1 << 24):
    dec = json.JSONDecoder()
    with open(path, encoding="utf-8") as fh:
        buf = fh.read(block)
        pos = buf.index("[") + 1
        while True:
            while True:
                while pos < len(buf) and buf[pos] in " \n\r\t,":
                    pos += 1
                if pos < len(buf):
                    break
                more = fh.read(block)
                if not more:
                    return
                buf, pos = buf[pos:] + more, 0
            if buf[pos] == "]":
                return
            try:
                obj, end = dec.raw_decode(buf, pos)
            except ValueError:
                more = fh.read(block)
                if not more:
                    raise
                buf, pos = buf[pos:] + more, 0
                continue
            pos = end
            if pos > block:
                buf, pos = buf[pos:], 0
            obj["ahead"] = {int(k): v for k, v in obj["ahead"].items()}
            yield obj


def load_rows():
    """(KEEP_FROM부터의 행들, 모든 행의 (날, 변동성)) — nrl이 lab.load()로 한 것과 같은 원천."""
    rows, vols = [], []
    for r in stream():
        if r.get("변동성") is not None:
            vols.append((r["date"], r["변동성"]))
        if r["date"] >= KEEP_FROM:
            rows.append(r)
    return rows, vols


def calm_by_month(vols, upto=None):
    """nrl._calm_by_month와 같은 셈(그 달 첫날 앞의 모든 행) · upto면 그날까지의 행만."""
    class _R(dict):
        pass
    got = [{"date": d, "변동성": v} for d, v in vols if upto is None or d <= upto]
    return nrl._calm_by_month(got)


# ---------- 판 돌리기 ----------
def run_ledgers(pool):
    keep = nrl.inside
    nrl.inside = pool
    try:
        return z081.ledgers("뒤", z081.holds_b0)
    finally:
        nrl.inside = keep


def summary(gs):
    ev = z081.evaluate(gs, {})
    navs = {}
    for g in gs:
        _, nv = z081.z080.account(g["led"], g["still"], g["since"], g["end"], want_navs=True)
        navs[g["seed"]] = nv
    return ev, navs


def trades_key(g):
    return sorted((t["code"], t["산 날"], t.get("판 날"), round(float(t["손익"]), 9)) for t in g["led"])


def with_rank(rows, ranks):
    out = []
    for r in rows:
        x = dict(r)
        x[caps.RANK] = ranks.get((r["date"], r["code"]))
        x.pop(caps.SIZE, None)
        out.append(x)
    return out


def cut_env(T, rows_b0, rows_b1, vols):
    """T까지 잘라 다시 만든 nrl 바탕들. 돌려줌: 바꿀 이름 → 값, 끝 5관측 경계 날."""
    prices = {c: dict(b, rows=[x for x in b["rows"] if x[0] <= T]) for c, b in nrl.prices.items()}
    prices = {c: b for c, b in prices.items() if b["rows"]}
    lanes = lab.lanes(prices)
    # lab.build는 종목마다 끝 5관측(뒤 값 없음)을 표에 넣지 않음 → 잘린 판에서도 같은 행을 뺌
    last_ok = {c: b["rows"][-6][0] for c, b in prices.items() if len(b["rows"]) > 5}
    keep = lambda r: r["date"] <= T and r["date"] <= last_ok.get(r["code"], "")
    b0c = [r for r in rows_b0 if keep(r)]                   # 자른 끝에서 순번(i)은 같음(뒤만 자름) → 복사 없이 씀
    b1c = [r for r in rows_b1 if keep(r)]
    assert all(r["i"] < len(prices[r["code"]]["rows"]) for r in b1c)
    shape = F.shapes(lanes, {r["code"] for r in b0c})
    br = F.breadth_by_day(b0c, shape)                        # 정오표 E1: B1도 B0 순위로 센 시장 폭
    flow = {}
    for code in {r["code"] for r in b1c}:
        fr = [x for x in (final_group.flow_rows(code) or []) if x["date"] <= T]
        if fr:
            flow[code] = nrl.flow_entry(fr)
    targets = {}
    for code in {r["code"] for r in b1c}:
        got = [x for x in (study.target_timeline(code) or []) if x[0] <= T]
        if got:
            targets[code] = nrl.target_entry(got)
    env = {"prices": prices, "lanes": lanes, "shape": shape, "BR": br, "kin": rule.apart(prices), "FLOW": flow,
           "TARGETS": targets, "CALM_MONTH": calm_by_month(vols, T), "inside": [r for r in b1c if caps.inside(r, rule.TOP)]}
    cal = lab.trading_days(lanes)
    t5 = cal[bisect.bisect_right(cal, T) - 6]                 # T − 5거래일(그날까지 비교)
    return env, t5


def run_cut(env):
    saved = {k: getattr(nrl, k) for k in env}
    saved_lanes = z077.LANES["now"]
    try:
        for k, v in env.items():
            setattr(nrl, k, v)
        z077.LANES["now"] = env["lanes"]
        return z081.ledgers("뒤", z081.holds_b0)
    finally:
        for k, v in saved.items():
            setattr(nrl, k, v)
        z077.LANES["now"] = saved_lanes


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    out = {"task": "Z1-DELISTED-0023", "round": 3, "T": T}
    out["hashes"] = {p: sha(ROOT / p) for p in ["research/z077.py", "research/z078.py", "research/z080.py", "research/z081.py",
                                                  "research/z098.py", "nrl.py", "rule.py", "lab.py", "caps.py", "final_group.py",
                                                  "final_study.py"]}
    out["hashes"].update({f"public-daily/{f.name}": sha(f) for f in sorted((ROOT / "public-daily").glob("*.csv"))})
    out["nrl_cache"] = {"path": str(nrl.CACHE), "sha256": sha(nrl.CACHE)}

    log("참 순위 만들기")
    ranks, pdays = true_ranks()
    log("표 흘려 읽기(몇 분)")
    rows, vols = load_rows()
    log(f"행 {len(rows):,} · 변동성 {len(vols):,}")

    # 바탕 점검 1: 월별 문턱을 같은 원천으로 다시 세면 nrl과 같아야 함
    cm = calm_by_month(vols)
    out["check_calm_month_equal"] = all(abs(cm[k] - nrl.CALM_MONTH[k]) < 1e-12 for k in nrl.CALM_MONTH if k in cm) and set(cm) == set(nrl.CALM_MONTH)
    # B0 순위(caps.tag)를 흘려 읽은 행에 다시 붙여 nrl.inside와 같은지 · 시장 폭이 같은지
    rows_b0 = rows                                           # 메모리 아끼려고 복사하지 않음(B0 순위를 그대로 붙임 · B1은 아래 복사본)
    caps.tag(rows_b0, rule.TOP)
    rows_b0 = lab.realign(rows_b0, nrl.prices)
    del rows
    ins = {(r["code"], r["date"]): r for r in nrl.inside if r["date"] >= KEEP_FROM}
    mine = {(r["code"], r["date"]): r for r in rows_b0 if caps.inside(r, rule.TOP)}
    out["check_inside_same_keys"] = set(ins) == set(mine)
    skip = {"ahead"}
    bad = sum(1 for k in ins if k in mine and any(ins[k].get(f) != mine[k].get(f) for f in ins[k] if f not in skip))
    out["check_inside_same_fields_mismatch"] = bad
    br_mine = F.breadth_by_day(rows_b0, nrl.shape)
    out["check_breadth_equal"] = all(abs(br_mine[d] - nrl.BR[d]) < 1e-12 for d in br_mine if d >= "20210101") and \
        all(d in br_mine for d in nrl.BR if d >= "20210101")
    log("바탕 점검", {k: out[k] for k in out if k.startswith("check")})

    # B1 행: 순위 칸만 참 순위로 바꾼 복사본(nrl.inside 쪽 원본은 그대로)
    pool_b1 = with_rank([r for r in rows_b0 if (ranks.get((r["date"], r["code"])) or 999) <= rule.TOP], ranks)
    # 수급 · 목표가: nrl은 B0 후보 종목만 미리 읽음 → B1 후보 종목도 같은 원천에서 읽어 둠(값은 같은 원천 · 계약 그대로)
    added = 0
    for code in {r["code"] for r in pool_b1}:
        if code not in nrl.FLOW:
            fr = final_group.flow_rows(code)
            if fr:
                nrl.FLOW[code] = nrl.flow_entry(fr)
                added += 1
        if code not in nrl.TARGETS:
            got = study.target_timeline(code)
            if got:
                nrl.TARGETS[code] = nrl.target_entry(got)
    out["flow_targets_loaded_for_b1_only_codes"] = added
    pool_b0 = [r for r in nrl.inside]
    k0 = {(r["code"], r["date"]) for r in pool_b0 if r["date"] >= rule.MID}
    k1 = {(r["code"], r["date"]) for r in pool_b1 if r["date"] >= rule.MID}
    out["pool"] = {"B0": len(k0), "B1": len(k1), "both": len(k0 & k1), "only_B0": len(k0 - k1), "only_B1": len(k1 - k0)}
    miss_days = sum(1 for (d, c), k in ranks.items() if c in MISSING and k <= rule.TOP and rule.MID <= d)
    out["missing19_top100_stockdays_from_2021"] = miss_days
    out["true_top100_stockdays_from_2021"] = sum(1 for (d, c), k in ranks.items() if k <= rule.TOP and rule.MID <= d <= max(pdays))
    log("후보 모음", out["pool"])

    log("B0 돌리기(1)")
    g0 = run_ledgers(pool_b0)
    log("B1 돌리기")
    g1 = run_ledgers(pool_b1)
    log("B0 돌리기(2 · 순서 독립 확인)")
    g0b = run_ledgers(pool_b0)
    out["check_b0_order_independent"] = all(trades_key(a) == trades_key(b) and a["end"] == b["end"] for a, b in zip(g0, g0b))
    e0, n0 = summary(g0)
    e1, n1 = summary(g1)
    seeds = []
    for a, b in zip(e0["seeds"], e1["seeds"]):
        seeds.append({"seed": a["seed"], "B0_cagr": a["cagr"], "B1_cagr": b["cagr"], "diff": round(b["cagr"] - a["cagr"], 2),
                      "B0_worst_day": a["worst_day"], "B1_worst_day": b["worst_day"], "B0_worst_month": a["worst_month"],
                      "B1_worst_month": b["worst_month"], "B0_mdd": a["mdd_daily"], "B1_mdd": b["mdd_daily"],
                      "B0_trades": len(g0[a["seed"]]["led"]), "B1_trades": len(g1[b["seed"]]["led"])})
    for s, g in zip(seeds, zip(g0, g1)):
        b0buys = {(t["code"], t["산 날"]) for t in g[0]["led"] + g[0]["still"]}
        b1buys = {(t["code"], t["산 날"]) for t in g[1]["led"] + g[1]["still"]}
        s["buys_only_B0"], s["buys_only_B1"] = len(b0buys - b1buys), len(b1buys - b0buys)
    out["seeds"] = seeds
    out["B0"] = {k: e0[k] for k in ("cagr", "cagr_spread", "worst_day", "worst_month", "mdd")}
    out["B1"] = {k: e1[k] for k in ("cagr", "cagr_spread", "worst_day", "worst_month", "mdd")}
    diffs = sorted(s["diff"] for s in seeds)
    out["diff_median"] = diffs[len(diffs) // 2]
    out["diff_ge_minus3_count"] = sum(1 for x in diffs if x >= -3)
    for name, nv in (("B0", n0), ("B1", n1)):
        with (OUT / f"nav_{name}.csv").open("w", encoding="utf-8") as fh:
            fh.write("seed,date,nav\n")
            for s, rows_ in nv.items():
                fh.writelines(f"{s},{d},{v!r}\n" for d, v in rows_)
    log("B0", out["B0"], "B1", out["B1"], "짝 차 가운데", out["diff_median"])

    log("자르기 판 만들기 · 돌리기")
    env, t5 = cut_env(T, rows_b0, pool_b1, vols)
    out["cut_t5"] = t5
    out["check_cut_calm_month_equal"] = all(abs(env["CALM_MONTH"][k] - nrl.CALM_MONTH[k]) < 1e-12 for k in env["CALM_MONTH"] if k <= T[:6])
    out["check_cut_breadth_equal_to_t5"] = all(abs(env["BR"].get(d, -1) - nrl.BR[d]) < 1e-12 for d in nrl.BR if "20210101" <= d <= t5)
    gc = run_cut(env)
    cut = []
    for g, c in zip(g1, gc):
        full = [(d, v) for d, v in n1[g["seed"]] if d <= t5]
        _, nc = z081.z080.account(c["led"], c["still"], c["since"], c["end"], want_navs=True, lanes=env["lanes"])
        part = [(d, v) for d, v in nc if d <= t5]
        same_days = [d for d, _ in full] == [d for d, _ in part]
        maxdiff = max((abs(a[1] - b[1]) for a, b in zip(full, part)), default=None)
        buys_full = sorted((t["code"], t["산 날"]) for t in g["led"] + g["still"] if t["산 날"] <= t5)
        buys_cut = sorted((t["code"], t["산 날"]) for t in c["led"] + c["still"] if t["산 날"] <= t5)
        tail = [(d, v) for d, v in n1[g["seed"]] if t5 < d <= T]
        tail_c = dict(nc)
        cut.append({"seed": g["seed"], "same_days": same_days, "nav_maxdiff_to_t5": maxdiff, "buys_same_to_t5": buys_full == buys_cut,
                    "tail_days_diff": sum(1 for d, v in tail if d not in tail_c or abs(tail_c[d] - v) > 1e-12)})
    out["cut"] = cut
    out["cut_ok"] = all(c["same_days"] and c["nav_maxdiff_to_t5"] is not None and c["nav_maxdiff_to_t5"] < 1e-12 and c["buys_same_to_t5"]
                        for c in cut) and out["check_cut_calm_month_equal"] and out["check_cut_breadth_equal_to_t5"]
    log("자르기", out["cut_ok"], cut)

    checks_ok = all(out[k] for k in ("check_calm_month_equal", "check_inside_same_keys", "check_breadth_equal",
                                     "check_b0_order_independent")) and out["check_inside_same_fields_mismatch"] == 0
    limits = out["B1"]["worst_day"][1] > -15 and out["B1"]["worst_month"][1] > -15
    small = limits and out["diff_median"] >= -3 and out["diff_ge_minus3_count"] >= 6
    out["checks_ok"], out["limits_ok"] = checks_ok, limits
    out["verdict"] = ("판정 보류" if not (checks_ok and out["cut_ok"]) else "RANK_EFFECT_SMALL" if small else "RANK_EFFECT_LARGE")
    (OUT / "result.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    log("판정", out["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
