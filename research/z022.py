"""Z22 — 투신 단타 T4b: 시장 전체 연기금 순매수가 큰 날 → 코스피200 ETF(069500)(docs/RL-TUSIN.md).
- 신호(t 장 끝난 뒤 앎): 코스피 연기금 순매수 ÷ 거래대금(1일 · 5일 합)을 **앞 250거래일과만** 견준 순위 ≥ q.
- 사기: t+1 종가 069500 · h일 들기(들고 있는 중 새 신호면 h일 늘림) · 비용 0.2%(사고팔기 합).
- 고르기: q ∈ {0.6, 0.7, 0.8, 0.9} × h ∈ {5, 10, 20} × 1일/5일을 **앞 반 2017 ~ 21**에서 '든 날 하루 평균 − 069500 아무 날 평균'으로 고름 → 뒤 반 2022 ~ 26 시험.
- 같은 것을 '시장 폭 < 50 날만'(빈칸 엔진이 켜지는 때)으로도.
- 연 · 골 · 나쁜 하루 · 달(사용자 한도 −15%) · 자르기 시험(자료를 자른 날 앞까지 들기 표가 같은지).
python research/z022.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402
import z008 as N  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COST = 0.002


def rows(name):
    return {str(r["date"]): r for r in json.loads((ROOT / "market-data" / name).read_text(encoding="utf-8"))["rows"]}


def past_rank(s, n=250):
    """오늘 값이 앞 n날(오늘 뺌) 가운데 몇 번째인지(0 ~ 1) — 앞 날들과만 견줌."""
    a = s.to_numpy()
    out = np.full(len(a), np.nan)
    for i in range(n, len(a)):
        w = a[i - n:i]
        w = w[~np.isnan(w)]
        if len(w) >= n // 2 and not np.isnan(a[i]):
            out[i] = (w < a[i]).mean()
    return pd.Series(out, index=s.index)


def hold(sig, h):
    """sig[t] → t+1 종가에 들어가 h일 들기. 돌려줌: 날 i의 하루 수익(i−1 → i 종가)을 받는지."""
    sig = sig.fillna(False).to_numpy()
    on = np.zeros(len(sig), bool)
    left = 0
    for i in range(len(sig)):
        # 날 i 수익은 i−1 종가에 들고 있었으면 받음. i−1 종가에 들어가는 건 sig[i−2].
        if i >= 2 and sig[i - 2]:
            left = h
        if left > 0:
            on[i] = True
            left -= 1
    return pd.Series(on, index=sig.index if hasattr(sig, "index") else None)


def account(on, r):
    on = pd.Series(on, index=r.index)
    flip = on.astype(int).diff().abs().fillna(0)
    return (r * on).fillna(0) - flip * COST / 2


def stats(x):
    e = (1 + x).cumprod()
    mon = (1 + x).groupby(pd.to_datetime(x.index).to_period("M")).prod() - 1
    return f"연 {(e.iloc[-1] ** (245 / len(x)) - 1) * 100:+5.1f}% · 골 {(e / e.cummax() - 1).min() * 100:6.1f}% · 나쁜 하루 {x.min() * 100:5.1f}% · 나쁜 달 {mon.min() * 100:5.1f}%"


def main():
    idx, inv = rows("index_KOSPI.json"), rows("investor_KSP.json")
    body = json.loads((ROOT / "etf-data/069500.json").read_text(encoding="utf-8"))
    etf = pd.Series({str(d): float(c) for d, c in body["closes"] if c})
    days = sorted(set(idx) & set(inv) & set(etf.index))
    D = pd.DataFrame(index=days)
    D["연기금%"] = [inv[d].get("연기금") / idx[d]["거래대금"] if inv[d].get("연기금") is not None and idx[d]["거래대금"] else np.nan for d in days]
    r = etf.reindex(days).pct_change()
    C, *_ = Z.load()
    inside, size = Z.universe(C)
    reg, br = N.regimes(C, size)
    weak = (br.reindex(days) < 50)
    feats = {"1일": past_rank(D["연기금%"]), "5일": past_rank(D["연기금%"].rolling(5).sum())}
    A = pd.Series([d < "20220101" for d in days], index=days) & (pd.Index(days) >= "20170101")
    B = pd.Series([d >= "20220101" for d in days], index=days)
    base = {k: r[m].mean() for k, m in (("A", A), ("B", B))}
    for gate_lab, gate in (("모든 날", pd.Series(True, index=days)), ("시장 폭 < 50 날만", weak)):
        print(f"\n== {gate_lab} · 069500 아무 날 하루 평균 앞 {base['A'] * 1e4:+.1f} / 뒤 {base['B'] * 1e4:+.1f}bp ==")
        res = []
        for fk, f in feats.items():
            for q in (0.6, 0.7, 0.8, 0.9):
                for h in (5, 10, 20):
                    on = hold((f >= q) & gate, h)
                    on.index = pd.Index(days)
                    x = account(on, r)
                    ea = (x[A & on].mean() - base["A"]) * 1e4 if (A & on).sum() > 30 else np.nan
                    eb = (x[B & on].mean() - base["B"]) * 1e4 if (B & on).sum() > 30 else np.nan
                    res.append((ea, eb, fk, q, h, (A & on).mean() / A.mean(), (B & on).mean() / B.mean(), x))
        res.sort(key=lambda t: -np.nan_to_num(t[0], nan=-1e9))
        print("  앞 반 '든 날 하루 평균 − 아무 날'(bp) 위 6개 → 뒤 반 시험:")
        for ea, eb, fk, q, h, fa, fb, _ in res[:6]:
            print(f"    {fk} 순위 ≥ {q:.1f} · {h:2d}일 | 앞 {ea:+5.1f}bp(든 날 {fa:.0%}) → 뒤 {eb:+5.1f}bp(든 날 {fb:.0%})")
        allb = [t[1] for t in res if t[1] == t[1]]
        print(f"  (24판 모두 뒤 반: 평균 {np.mean(allb):+.1f}bp · + 인 판 {np.mean(np.array(allb) > 0):.0%})")
        ea, eb, fk, q, h, *_ , x = res[0]
        print(f"  고른 판 계좌(그 밖 날 현금): 앞 {stats(x[A])} | 뒤 {stats(x[B])}")
    # 자르기 시험: 자료를 2022-01-03에서 자르고 같은 셈 → 자른 날 앞 들기 표가 같나
    cut = "20220103"
    f_full = past_rank(D["연기금%"].rolling(5).sum())
    f_cut = past_rank(D.loc[D.index < cut, "연기금%"].rolling(5).sum())
    on_full = hold(f_full >= 0.8, 20)
    on_cut = hold(f_cut >= 0.8, 20)
    same = (on_full[:len(on_cut)] == on_cut).all()
    print(f"\n자르기 시험(5일 · ≥ 0.8 · 20일 · 자른 날 {cut}): 앞 {len(on_cut)}날 들기 표 {'같음 → 통과' if same else '다름 → 실패'}")


if __name__ == "__main__":
    main()
