"""REGIME-SW-0048 — 국면 판정기 + 장별 선수 바꾸기를 최근 10년(2017-02 ~ 2026-09) 백테스트로 깊게 개발(사용자 2026-10-10 새 방식).
- 바탕: 1일봉 운영 장부(base_m1.csv · USINV-0039 · 날마다 NAV · 현금) — 지금 운영 조합 그대로의 계좌.
- 선수: 상승 = 1일봉 장부 + 남는 현금으로 레버리지(122630) · 하락 = 1일봉 줄이고 인버스(114800 또는 2배 252670) · 횡보 = 1일봉 + 남는 현금으로 인버스 조금.
- 판정 재료(그날 장 끝까지 나온 값만 · 수급은 장 끝 뒤 나오므로 '판정 다음 날 종가'에 바꿈 → 판정 t · 바꿈 t+1 종가):
  069500 종가 · 이동평균 · 20일 흔들림 · 시장 폭(거래대금 상위 100 가운데 50일선 > 200일선 몫) · 코스피 외국인 · 기관 순매수 / 거래대금.
- 계좌: 총자산 A = 1일봉 몫(장부 날 수익을 그대로 받음) + ETF 몫 + 놀리는 현금.
  · 1일봉 몫 비율 fb(국면별) · ETF 몫 = 국면별 비율 × A. 다만 ETF는 '1일봉 몫 안의 현금 + 1일봉에서 뺀 돈'까지만(빚 없음).
  · 비용: ETF 사고팔 때 각 0.05% · 1일봉 몫을 줄일 때 줄인 돈의 0.30%(주식 팔기) · 늘릴 때 0.05%.
  · 바꿈은 국면이 바뀐 다음 날 종가(장중 값 안 씀). 국면이 그대로면 몫을 다시 맞추지 않음(달 첫날만 다시 맞춤).
- 잣대(사용자): 10년 연수익 최대 · 계좌 하루 · 달 손실 −15% 이내(상승 · 하락 · 횡보 해 각각에서) · 이웃 설정 고원 · 미래 참조 차단.
python3 research/regime_dev.py --eval '{설정 JSON}' "메모"     한 판 평가(STARTED 기록 · 상한 300)
python3 research/regime_dev.py --cut-test                     자르기 시험(2022-06-15에서 자른 자료로 국면 · 계좌가 그 앞까지 같아야 함)"""
import bisect
import csv
import hashlib
import json
import math
import os
import pickle
import sys
import time
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
BOX = ROOT / "research-exchange/claude-to-gpt/REGIME-SW-0048"
BASE_CSV = BOX / "base_m1.csv"
SNAP = os.getenv("REG_SNAP", "/tmp/rev-full.pkl")
CUT = os.getenv("REG_CUT", "")
LO, HI = "20170201", "20260915"
EVALS = BOX / "evals.jsonl"
EVAL_CAP = 300
ETF = ("069500", "114800", "252670", "122630")
YEAR_KIND = {"2017": "상승", "2018": "하락", "2019": "횡보", "2020": "상승", "2021": "상승", "2022": "하락",
             "2023": "횡보", "2024": "횡보", "2025": "상승", "2026": "상승"}      # 사용자 2026-10-10 나눔 그대로
COST_ETF, COST_BASE_DOWN, COST_BASE_UP = 0.0005, 0.0030, 0.0005
R0 = {"n": 60, "confirm": "none", "persist": 1, "down_base": 1.0, "down_inv": 0.0, "inv": "114800",
      "up_lev": 0.0, "side_inv": 0.0, "up_need": "ma_rising"}


def cut_ok(d):
    return not CUT or d <= CUT


def load():
    base = [(r["날"], float(r["NAV"]), float(r["현금"])) for r in csv.DictReader(open(BASE_CSV))]
    base = {d: (nav, cash / nav) for d, nav, cash in base if cut_ok(d)}
    etf = {}
    for c in ETF:
        etf[c] = {d: float(x) for d, x in json.load(open(ROOT / f"etf-data/{c}.json"))["closes"] if x and cut_ok(d)}
    s = pickle.load(open(SNAP, "rb"))
    br = {d: v for d, v in s["br"].items() if cut_ok(d)}
    inv = [r for r in json.load(open(ROOT / "market-data/investor_KSP.json"))["rows"] if cut_ok(r["date"])]
    idx = {r["date"]: r for r in json.load(open(ROOT / "market-data/index_KOSPI.json"))["rows"] if cut_ok(r["date"])}
    flow = {}
    for r in inv:
        tv = idx.get(r["date"], {}).get("거래대금")
        if tv:
            flow[r["date"]] = {"F": r["외국인"] / tv, "I": r["기관"] / tv}
    return base, etf, br, flow


DATA = None


def data():
    global DATA
    if DATA is None:
        DATA = load()
    return DATA


def features(etf, br, flow):
    """날 → 판정 재료(그날 장 끝까지 값만)."""
    px = etf["069500"]
    ds = sorted(px)
    xs = [px[d] for d in ds]
    fd = sorted(flow)
    out = {}
    for k, d in enumerate(ds):
        f = {"close": xs[k]}
        for n in (20, 60, 120, 200):
            if k >= n - 1:
                f[f"ma{n}"] = sum(xs[k - n + 1:k + 1]) / n
            if k >= n - 1 + 20:
                f[f"ma{n}_20ago"] = sum(xs[k - n + 1 - 20:k + 1 - 20]) / n
        if k >= 250:
            rets = [xs[j] / xs[j - 1] - 1 for j in range(k - 249, k + 1)]
            v20 = math.sqrt(sum(r * r for r in rets[-20:]) / 20)
            vols = sorted(math.sqrt(sum(r * r for r in rets[j - 20:j]) / 20) for j in range(20, 251, 5))
            if vols[len(vols) // 2] > 0:
                f["vol_ratio"] = v20 / vols[len(vols) // 2]
        if d in br:
            f["breadth"] = br[d]
        j = bisect.bisect_right(fd, d)
        if j >= 20:
            f["F20"] = sum(flow[fd[i]]["F"] for i in range(j - 20, j))
            f["I20"] = sum(flow[fd[i]]["I"] for i in range(j - 20, j))
        out[d] = f
    return out


def raw_state(f, cfg):
    n = cfg["n"]
    ma = f.get(f"ma{n}")
    if ma is None:
        return "횡보"
    c = cfg["confirm"]
    conf = {"none": True, "br40": f.get("breadth", 100) < 40, "br30": f.get("breadth", 100) < 30,
            "F20neg": f.get("F20", 0) < 0, "FI20neg": f.get("F20", 0) + f.get("I20", 0) < 0,
            "vol15": f.get("vol_ratio", 0) > 1.5}[c]
    if f["close"] < ma and conf:
        return "하락"
    up = f["close"] > ma
    if cfg["up_need"] == "ma_rising":
        up = up and f.get(f"ma{n}_20ago") is not None and ma > f[f"ma{n}_20ago"]
    elif cfg["up_need"] == "br50":
        up = up and f.get("breadth", 0) >= 50
    return "상승" if up else "횡보"


def states(feat, cfg):
    """판정(t날 장 끝) → 버팀 날 수 persist를 채워야 바뀜."""
    out, cur, run, last = {}, "횡보", 0, None
    for d in sorted(feat):
        s = raw_state(feat[d], cfg)
        run = run + 1 if s == last else 1
        last = s
        if s != cur and run >= cfg["persist"]:
            cur = s
        out[d] = cur
    return out


def targets(state, cfg):
    """국면 → (1일봉 몫 fb, ETF 코드, ETF 몫 fe)."""
    if state == "하락":
        return cfg["down_base"], cfg["inv"], cfg["down_inv"]
    if state == "상승":
        return 1.0, "122630", cfg["up_lev"]
    return 1.0, cfg["inv"], cfg["side_inv"]


FEAT = None


def account(cfg, lo=LO, hi=HI):
    global FEAT
    base, etf, br, flow = data()
    if FEAT is None or FEAT[0] is not DATA:
        FEAT = (DATA, features(etf, br, flow))
    feat = FEAT[1]
    st = states(feat, cfg)
    days = [d for d in sorted(base) if lo <= d <= hi and all(d in etf[c] for c in ETF)]
    A, vb, ve, code, cash = 1.0, 1.0, 0.0, None, 0.0
    navs, nst = {days[0]: 1.0}, {}
    pending = None
    trims = [0]
    for j in range(1, len(days)):
        p, d = days[j - 1], days[j]
        # 오늘 수익(어제 몫 그대로)
        vb *= base[d][0] / base[p][0]
        if code:
            ve *= etf[code][d] / etf[code][p]
        A = vb + ve + cash
        # 바꿈: 어제 장 끝 판정이 그 전과 다르면 오늘 종가에 맞춤 · 달 첫날도 맞춤
        s_prev = st.get(p, "횡보")
        if pending != s_prev or d[:6] != p[:6]:
            fb, c_new, fe = targets(s_prev, cfg)
            room = fb * base[d][1] + (1 - fb)                # 1일봉 몫 안 현금 + 1일봉에서 뺀 돈
            fe = min(fe, room)
            tb, te = fb * A, fe * A
            cost = (COST_BASE_DOWN * max(0, vb - tb) + COST_BASE_UP * max(0, tb - vb))
            if c_new == code:
                cost += COST_ETF * abs(te - ve)
            else:
                cost += COST_ETF * (ve + te)
            A -= cost
            vb, ve, code = fb * A, fe * A, (c_new if fe > 0 else None)
            if not code:
                ve = 0.0
            cash = A - vb - ve
            pending = s_prev
        elif code and cash < -vb * base[d][1] - 1e-12:
            # 1일봉이 현금을 다시 쓰면 ETF가 1일봉의 놀던 현금을 넘음(cash < −1일봉 현금) → 넘친 만큼 오늘 종가에 팖(빚 없음)
            need = -vb * base[d][1] - cash
            cut = min(ve, need / (1 - COST_ETF))
            ve -= cut
            cash += cut * (1 - COST_ETF)
            trims[0] += 1
        navs[d] = vb + ve + cash
        nst[d] = s_prev
    account.trims = trims[0]
    return navs, nst


def stats(navs, nst):
    ds = sorted(navs)
    rets = {ds[j]: navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))}
    mo, yr = {}, {}
    for d, r in rets.items():
        mo[d[:6]] = mo.get(d[:6], 1) * (1 + r)
        yr[d[:4]] = yr.get(d[:4], 1) * (1 + r)
    n = len(ds) / 250
    ann = navs[ds[-1]] ** (1 / n) - 1
    pk, mdd = 0, 0
    for d in ds:
        pk = max(pk, navs[d])
        mdd = min(mdd, navs[d] / pk - 1)
    kind = {}
    for d, r in rets.items():
        k = YEAR_KIND[d[:4]]
        g = kind.setdefault(k, {"worst_day": 0.0, "months": {}})
        g["worst_day"] = min(g["worst_day"], r)
    for m, v in mo.items():
        kind[YEAR_KIND[m[:4]]]["months"][m] = v - 1
    kinds = {k: {"worst_day_pct": round(g["worst_day"] * 100, 3), "worst_month_pct": round(min(g["months"].values()) * 100, 3)} for k, g in kind.items()}
    half = {}
    for name, a, b in (("2017~2021", "20170101", "20211231"), ("2022~2026", "20220101", "20261231")):
        sub = [d for d in ds if a <= d <= b]
        half[name] = round(((navs[sub[-1]] / navs[sub[0]]) ** (250 / len(sub)) - 1) * 100, 2)
    share = {s: round(sum(1 for v in nst.values() if v == s) / len(nst) * 100, 1) for s in ("상승", "횡보", "하락")}
    wd = min(rets.values())
    wm = min(mo.values()) - 1
    return {"annual_pct": round(ann * 100, 3), "annual_raw": ann, "worst_day_pct": round(wd * 100, 3), "worst_month_pct": round(wm * 100, 3),
            "loss_ok": wd >= -0.15 and wm >= -0.15, "mdd_report_pct": round(mdd * 100, 2),
            "years_pct": {y: round((v - 1) * 100, 2) for y, v in sorted(yr.items())}, "by_kind": kinds, "halves_report": half, "state_share_pct": share}


def _started():
    if not EVALS.exists():
        return 0
    return sum(1 for l in EVALS.read_text().splitlines() if json.loads(l)["status"] == "STARTED")


def _log(rec):
    with open(EVALS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def evaluate(cfg, note=""):
    n = _started()
    if n >= EVAL_CAP:
        sys.exit("평가 상한 300 도달(멈춤)")
    key = json.dumps(cfg, sort_keys=True, ensure_ascii=False)
    _log({"status": "STARTED", "no": n + 1, "cfg": key, "note": note, "at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
    try:
        res = stats(*account(cfg))
    except Exception as e:                                  # 실패도 기록
        _log({"status": "FAILED", "no": n + 1, "error": repr(e)})
        raise
    _log({"status": "DONE", "no": n + 1, "annual_pct": res["annual_pct"], "worst_day_pct": res["worst_day_pct"],
          "worst_month_pct": res["worst_month_pct"]})
    return res


def cut_test():
    """REG_CUT=20220615 · REG_SNAP=/tmp/reg-cut.pkl로 자른 자료와 온 자료에서, 여러 설정의 국면 · 계좌가 자른 날 앞까지 같은지."""
    global CUT, SNAP, DATA
    cfgs = [R0, dict(R0, n=200, confirm="br40", persist=3, down_base=0.5, down_inv=0.3, inv="252670", up_lev=0.3, side_inv=0.2),
            dict(R0, n=20, confirm="FI20neg", up_need="br50", down_base=0.0, down_inv=0.5), dict(R0, confirm="vol15", persist=5, up_lev=0.6)]
    full = [account(c) for c in cfgs]
    CUT, SNAP, DATA = "20220615", "/tmp/reg-cut.pkl", None
    part = [account(c) for c in cfgs]
    bad, n = [], 0
    for (fa, sa), (pa, ps) in zip(full, part):
        for d in pa:
            if d >= CUT:
                continue
            n += 1
            if abs(fa[d] - pa[d]) > 1e-12 or sa.get(d) != ps.get(d):
                bad.append(d)
    print(json.dumps({"cells_compared": n, "differ": len(bad), "first_bad": bad[:3], "configs": len(cfgs)}, ensure_ascii=False))


def main():
    if "--cut-test" in sys.argv:
        return cut_test()
    if "--eval" in sys.argv:
        i = sys.argv.index("--eval")
        cfg = dict(R0, **json.loads(sys.argv[i + 1]))
        note = sys.argv[i + 2] if len(sys.argv) > i + 2 else ""
        print(json.dumps(evaluate(cfg, note), ensure_ascii=False))
        return
    sys.exit("--eval · --cut-test만 됩니다")


if __name__ == "__main__":
    main()
