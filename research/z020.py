"""N9 — 좁은 장 RL(docs/RL-NARROW.md): 좁은 오름장엔 종목 대신 지수 · 큰 종목 통째로.
- 국면(z008.regimes · 그날 종가까지 값): 좁은 오름장(폭 < 50 · 코스피 ≥ 60일선) · 내림장 · 넓은 장.
- t 종가에 국면 판단 → **t+1 종가에 들어감**(t+2 하루 수익부터 셈) · 국면이 바뀌면 t+1 종가에 나옴.
- 들 것: 069500(코스피200 ETF) · 그날 시총 1 ~ 10위 같은 비중 · 1 ~ 30위 · 대상 200 같은 비중 · (참고) 빈칸 엔진 ③ 돌리기 어림(날마다 다시 고름).
  큰 종목 바구니는 날마다 같은 비중으로 맞춤 — 바뀐 몫만 비용 0.5% · ETF 비용 0.2%(사고팔기 합).
- 국면 아닌 날은 현금(0). 앞 2017 ~ 22 / 뒤 2023 ~ 26 · 연 수익 · 골 · 가장 나쁜 하루 · 가장 나쁜 달(사용자 한도 −15%) · 들고 있는 날 몫.
python research/z020.py
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

ROT = ("133690", "138230", "132030", "148070")


def etf(code, idx):
    body = json.loads(Path(f"etf-data/{code}.json").read_text(encoding="utf-8"))
    return pd.Series({str(d): float(c) for d, c in body["closes"] if c and Z._keep(str(d))}).reindex(idx)


def run(W, R, cost):
    """W: t 종가에 정한 비중(행 = 날) → t+1 종가에 맞춤 → t+2 수익부터. R: 하루 수익."""
    held = W.shift(1).fillna(0)                        # t+1 종가에 들고 있는 비중
    gross = (held.shift(1).fillna(0) * R.fillna(0)).sum(axis=1)
    turn = held.diff().abs().sum(axis=1).fillna(held.abs().sum(axis=1))
    return gross - turn * cost / 2, (held.abs().sum(axis=1) > 0)


def report(lab, r, on):
    out = []
    for part, m in (("앞 2017~22", r.index < "20230101"), ("뒤 2023~26", r.index >= "20230101")):
        x = r[m & (r.index >= Z.START)]
        e = (1 + x).cumprod()
        ann = e.iloc[-1] ** (245 / len(x)) - 1
        mdd = (e / e.cummax() - 1).min()
        mon = (1 + x).groupby(pd.to_datetime(x.index).to_period("M")).prod() - 1
        o = on[x.index]
        per = x[o].mean() * 245 if o.any() else np.nan
        out.append(f"{part}: 연 {ann * 100:+5.1f}% · 골 {mdd * 100:6.1f}% · 나쁜 하루 {x.min() * 100:5.1f}% · 나쁜 달 {mon.min() * 100:5.1f}% · 든 날 {o.mean():.0%} · 든 날 연율 {per * 100:+5.1f}%")
    print(f"  [{lab}]\n    " + "\n    ".join(out))


def main():
    C, *_ = Z.load()
    inside, size = Z.universe(C)
    reg, _ = N.regimes(C, size)
    R = C.pct_change(fill_method=None).clip(-0.5, 1.0)
    rank = size.rank(axis=1, ascending=False)
    E = pd.DataFrame({c: etf(c, C.index) for c in ("069500",) + ROT})
    RE = E.pct_change(fill_method=None)
    for rg in ("좁은 오름장", "내림장", "넓은 장"):
        on = (reg == rg)
        print(f"\n== {rg} 날만 들기(그 밖엔 현금) · 국면 날 몫 {on[on.index >= Z.START].mean():.0%} ==")
        w = pd.DataFrame(0.0, index=C.index, columns=["069500"])
        w.loc[on, "069500"] = 1.0
        report("069500 코스피200 ETF", *run(w, RE[["069500"]], 0.002))
        for k in (10, 30, 200):
            sel = (rank <= k) & inside & C.notna()
            wk = sel.div(sel.sum(axis=1).replace(0, np.nan), axis=0).fillna(0).mul(on.astype(float), axis=0)
            report(f"시총 1 ~ {k}위 같은 비중", *run(wk, R, 0.005))
        r20 = E[list(ROT)] / E[list(ROT)].shift(20) - 1
        pick = r20.where(r20 > 0).rank(axis=1, ascending=False) <= 2
        wr = (pick.astype(float) * 0.5).mul(on.astype(float), axis=0)
        report("참고: ③ 돌리기 어림", *run(wr, RE[list(ROT)], 0.002))
    k = E["069500"]
    report("참고: 069500 늘 들기", *run(pd.DataFrame({"069500": 1.0}, index=C.index), RE[["069500"]], 0.0))


if __name__ == "__main__":
    main()
