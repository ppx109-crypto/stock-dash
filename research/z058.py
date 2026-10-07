"""2차 연구 STEP 6 · 10 — A 다시 재기(쪼개기 고친 시총 · 새 비용 3판) + 국면 + 상관 + 섞기(docs/PREREG-2.md §3 · §6 · §7).
A_1D = 1일봉 '새 82' 매매 목록(z055 · adj / raw) → 새 비용(perf2 · 계좌 Z_ACC · 칸 몫 주문) → 날마다 평가(a_mtm).
A = A_1D + 빈칸 엔진 · 인버스(기존 dd_now.npz의 엔진 몫 mix − d1 · 엔진 켜는 시장 폭은 옛 시총 계산 → 어림).
D5 · D8 · F5 · 바탕 = z054_adj.npz(BASE). 섞기: 날마다 맞춤 · 달마다 맞춤(달 첫날 몫으로 돌려 놓고 달 안에선 흘러감).
위험 맞춤: 역변동성(앞 60일 · 어제까지) 달마다 · 변동성 목표 연 15%(몫 합 ≤ 1 · 빚 없음 · 어제까지 60일 변동성).
CAPS_ADJ=1 NRL_CACHE=.../nrl-cache-adj.pkl python research/z058.py
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import a_mtm  # noqa: E402
import perf2 as P  # noqa: E402

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
ACC = float(os.getenv("Z_ACC", "1e8"))
PER = (("학습 2017 ~ 20", "20170201", "20210101"), ("검증 2021 ~ 22", "20210101", "20230101"), ("시험 2023 ~ 26", "20230101", "20991231"), ("전체", "20170201", "20991231"))


def recost(ledger, scale, acc=ACC):
    """장부 손익(왕복 0.25% 뺀 값) → 비용 전으로 되돌린 뒤 새 비용(perf2) 뺌. 반 팔기 등은 장부 손익 그대로 비율로."""
    out, tr = [], []
    for c, b, e, p, k in ledger:
        g = (1 + p / 100) / (1 - 0.0025) - 1          # 비용 전 어림
        cb, cs = P.side_costs(c, b, e, acc * k / 10, scale)
        net = (1 + g) * (1 - cb) * (1 - cs) - 1
        out.append((c, b, e, net * 100, k))
        tr.append((c, b, e, net, k / 10))
    return out, tr


def regimes(days):
    k = pd.Series({str(r["date"]): float(r["종가"]) for r in json.loads((P.ROOT / "market-data/index_KOSPI.json").read_text(encoding="utf-8"))["rows"] if r.get("종가")}).sort_index()
    m200 = k.rolling(200).mean()
    slope = m200 / m200.shift(20) - 1
    trend = pd.Series("횡보", index=k.index)
    trend[(k > m200) & (slope > 0)] = "강세"
    trend[(k < m200) & (slope < 0)] = "약세"
    v20 = k.pct_change().rolling(20).std()
    vol = pd.Series(np.where(v20 > v20.expanding(min_periods=120).median(), "고변동", "저변동"), index=k.index)
    return trend.shift(1).reindex(days).fillna("횡보"), vol.shift(1).reindex(days).fillna("저변동")


def mix(R, w, rebalance="day"):
    if rebalance == "day":
        return sum(R[k] * v for k, v in w.items())
    out, val, mon = [], None, None
    for i, d in enumerate(R.index):
        if mon != d[:6]:
            val = {k: v for k, v in w.items()}
            mon = d[:6]
        tot = sum(val.values())
        r = sum(val[k] * R[k].iat[i] for k in w) / tot if tot else 0.0
        val = {k: val[k] * (1 + R[k].iat[i]) for k in w}
        out.append(r)
    return pd.Series(out, index=R.index)


def risk_parity(R, keys, target=None):
    vol = R[keys].rolling(60, min_periods=40).std().shift(1)
    out, mon, w = [], None, None
    for i, d in enumerate(R.index):
        if mon != d[:6]:
            v = vol.iloc[i]
            if v.notna().all() and (v > 0).all():
                inv = 1 / v
                w = inv / inv.sum()
            else:
                w = pd.Series(1 / len(keys), index=keys)
            if target:
                port_vol = (R[keys].iloc[max(0, i - 60):i] @ w).std() * np.sqrt(245) if i > 40 else np.nan
                scale = min(1.0, target / port_vol) if port_vol and np.isfinite(port_vol) and port_vol > 0 else 1.0
                w = w * scale
            mon = d[:6]
        out.append(float((R[keys].iloc[i] * w).sum()))
    return pd.Series(out, index=R.index)


def main():
    z = np.load(SP / "dd_now.npz")
    D0 = [str(d) for d in z["days"]]
    eng = z["mix"] - z["d1"]
    import nrl
    zz = np.load(SP / "z054_adj.npz")
    dz = [str(d) for d in zz["days"]]
    R = pd.DataFrame({"D5": zz["D 바구니 C 5칸"], "D8": zz["D 바구니 C 8칸"], "F5": zz["F5 공매도 비중 낮음 위 20"], "바탕": zz["바탕 200위 똑같이"]}, index=dz)
    for tag in ("adj", "raw"):
        led = json.load(open(SP / f"z055_d1_{tag}.json"))
        print(f"\n===== A · 시총 {'쪼개기 고침' if tag == 'adj' else '옛 계산'} · 매매 {len(led)} =====", flush=True)
        for sc, k in P.SCALES.items():
            l2, tr = recost(led, k)
            a1 = pd.Series(a_mtm.account(D0, l2, np.zeros(len(D0)), nrl.prices), index=D0)
            aa = pd.Series(a_mtm.account(D0, l2, eng, nrl.prices), index=D0)
            if tag == "adj" and sc == "BASE":
                R["A_1D"], R["A"] = a1.reindex(dz).fillna(0), aa.reindex(dz).fillna(0)
            for h, lo, hi in PER:
                if sc != "BASE" and not h.startswith(("시험", "전체")):
                    continue
                print(f"  [{sc}] {h:14s} 매매: {P.fmt_t(P.trade_stats(tr, lo, hi))}", flush=True)
                print(f"  [{sc}] {'':14s} 1D만 계좌: {P.fmt_d(P.daily_stats(a1, lo, hi))}", flush=True)
                print(f"  [{sc}] {'':14s} A(+엔진): {P.fmt_d(P.daily_stats(aa, lo, hi))}", flush=True)
            if sc == "BASE":
                print(f"  해마다(1D만): {P.years_line(P.daily_stats(a1, '20170201', '20991231'))}", flush=True)
                print(f"  해마다(A): {P.years_line(P.daily_stats(aa, '20170201', '20991231'))}", flush=True)
                s = P.daily_stats(aa, "20170201", "20991231")
                worst = sorted(s["달마다"].items(), key=lambda kv: kv[1])[:5]
                print("  A 가장 나쁜 달 5: " + " · ".join(f"{m} {v * 100:+.1f}%" for m, v in worst), flush=True)
        for acc in (1e9, 1e10):
            l2, tr = recost(led, 1.0, acc)
            aa = pd.Series(a_mtm.account(D0, l2, eng, nrl.prices), index=D0)
            print(f"  [계좌 {acc / 1e8:.0f}억 · BASE] 시험: {P.fmt_d(P.daily_stats(aa, '20230101', '20991231'))}", flush=True)
    R = R[R.index >= "20170201"]
    print("\n===== 날마다 수익 상관(2017-02 ~) =====", flush=True)
    print(R[["A", "A_1D", "D5", "D8", "F5", "바탕"]].corr().round(2).to_string(), flush=True)
    print("\n===== 국면별 연율(어제 국면 · 강세 = 코스피 > 200일선 & 기울기 + · 약세 = 아래 & − · 고변동 = 20일 변동성 > 쌓인 가운데값) =====", flush=True)
    tr_, vo_ = regimes(list(R.index))
    for key in ("A", "A_1D", "D5", "D8", "F5", "바탕"):
        cells = []
        for nm, g in (("강세", tr_ == "강세"), ("횡보", tr_ == "횡보"), ("약세", tr_ == "약세"), ("고변동", vo_ == "고변동"), ("저변동", vo_ == "저변동")):
            x = R[key][g]
            cells.append(f"{nm} {x.mean() * 245 * 100:+.0f}%({int(g.sum())}일)")
        print(f"  {key:5s} " + " · ".join(cells), flush=True)
    print("\n===== 섞기(BASE 비용 · D = 바구니 C 8칸) =====", flush=True)
    W = {"A100": {"A": 1}, "D100": {"D8": 1}, "F5 100": {"F5": 1}, "A70 + D30": {"A": .7, "D8": .3}, "A50 + D50": {"A": .5, "D8": .5},
         "A50 + D30 + F5 20": {"A": .5, "D8": .3, "F5": .2}, "A40 + D40 + F5 20": {"A": .4, "D8": .4, "F5": .2}, "A33 + D33 + F5 33": {"A": 1 / 3, "D8": 1 / 3, "F5": 1 / 3}}
    for reb in ("day", "month"):
        print(f"  [{'날마다' if reb == 'day' else '달마다'} 맞춤]", flush=True)
        for lab, w in W.items():
            r = mix(R, w, reb)
            for h, lo, hi in PER:
                if h.startswith(("검증", "학습")) and reb == "month":
                    continue
                print(f"    {lab:18s} {h:14s} {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)
    for lab, r in (("역변동성(A · D8 · F5)", risk_parity(R, ["A", "D8", "F5"])), ("역변동성 + 변동성 목표 15%", risk_parity(R, ["A", "D8", "F5"], 0.15))):
        for h, lo, hi in PER:
            print(f"    {lab:18s} {h:14s} {P.fmt_d(P.daily_stats(r, lo, hi))}", flush=True)
    R.to_pickle(SP / "z058_R.pkl")


if __name__ == "__main__":
    main()
