"""Z4 — 투신은 단타로 어떻게 돈을 버나 · 1회차(사용자 2026-10-07 "투신이 단타로 돈 어떻게버는지 타이머 맞추고 지속적 연구해줘").
docs/RL-TUSIN.md의 할 일 줄을 회차마다 하나씩. 이 파일은 1회차:
 A. 사건 모양: 투신(그리고 다른 투자자)이 그날 크게 산 날(대상 200 안 그날 위 10%) · 크게 판 날(아래 10%)의
    앞 5일 · 그날 · 뒤 1 · 5 · 20일 초과 수익(그날 대상 가운데값 뺌). '앞 · 그날'은 설명용(못 따라 함) · '뒤'만 t+1에 따라 살 수 있음.
 B. 투자자별 단타 손익 어림: 그날 순매수 q(주) × (h일 뒤 값 − 그날 값)을 시장 오르내림을 빼고 모두 더해 ÷ 그날 매매 금액 합.
    = '그 투자자가 그날 산 것을 h일 들고 있었다면' 번 몫(%) · 그날 안 타이밍은 (종가 − (고+저+종)/3)로 따로(평균 값보다 싸게 샀나).
    값은 그 투자자가 실제로 번 돈이 아니라 어림(체결 값 모름) · 서로 견주기용.
미래 참조: A · B는 '투신이 과거에 어떻게 벌었나'를 재는 설명이라 뒤 값을 일부러 씀. **따라 할 규칙**으로 바꿀 때만 t+1 진입 · 자르기 시험을 함.
python research/z004.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

WHO = ("투신", "외국인", "연기금", "사모", "기관", "개인")


def typical_price(C):
    """(고 + 저 + 종)/3 — volume-data 고가 · 저가."""
    hi, lo = {}, {}
    for c in C.columns:
        b = Z._json(f"volume-data/{c}.json") or {}
        cols = b.get("칸") or []
        if "고가" not in cols:
            continue
        ih, il = cols.index("고가"), cols.index("저가")
        hi[c] = {str(r[0]): r[ih] for r in b.get("날") or [] if r[ih]}
        lo[c] = {str(r[0]): r[il] for r in b.get("날") or [] if r[il]}
    H = pd.DataFrame(hi).reindex(index=C.index, columns=C.columns)
    L = pd.DataFrame(lo).reindex(index=C.index, columns=C.columns)
    return (H + L + C) / 3


def excess(r, inside):
    r = r.where(inside)
    return r.sub(r.median(axis=1), axis=0)


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    ok_day = pd.Series(C.index >= Z.START, index=C.index)
    inside = inside & pd.DataFrame(np.repeat(ok_day.to_numpy()[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    ret1 = excess(C / C.shift(1) - 1, inside)                         # 그날 초과
    before5 = excess(C.shift(1) / C.shift(6) - 1, inside)              # 앞 5일(t−6 → t−1)
    after = {h: excess(C.shift(-h) / C - 1, inside) for h in (1, 5, 20)}          # t 종가 → t+h(설명)
    after_t1 = {h: excess(C.shift(-(1 + h)) / C.shift(-1) - 1, inside) for h in (5, 20)}   # t+1 종가에 따라 삼
    typ = typical_price(C)
    out = {"A 사건 모양": {}, "B 단타 손익 어림": {}}
    for w in WHO:
        x = (F[w] / F["vol"]).where(inside)                             # 그날 순매수 ÷ 거래량
        q = x.rank(axis=1, pct=True)
        for side, m in (("크게 산 날(위 10%)", q > 0.9), ("크게 판 날(아래 10%)", q <= 0.1)):
            cell = {"앞 5일": before5.where(m), "그날": ret1.where(m), "뒤 1일": after[1].where(m), "뒤 5일": after[5].where(m),
                    "뒤 20일": after[20].where(m), "t+1에 따라 사서 5일": after_t1[5].where(m), "t+1에 따라 사서 20일": after_t1[20].where(m)}
            out["A 사건 모양"][f"{w} {side}"] = {k: round(float(np.nanmean(v.to_numpy())) * 100, 2) for k, v in cell.items()}
        # B: 그날 매매 금액 가중 손익(시장 뺌)
        val = (F[w] * C).where(inside)                                  # 원(+ 산 · − 판)
        gross = val.abs()
        res = {}
        for h in (1, 5, 20):
            pnl = (val * after[h]).sum(axis=1)
            g = gross.sum(axis=1)
            keep = g > 0
            res[f"{h}일"] = round(float(pnl[keep].sum() / g[keep].sum()) * 100, 3)
        # 그날 안 타이밍: 산 쪽이 (고+저+종)/3보다 종가가 높으면(평균보다 싸게 산 셈) +
        intra = (val * (C / typ - 1).where(inside)).sum(axis=1)
        res["그날 안(평균값 대비)"] = round(float(intra.sum() / gross.sum(axis=1).sum()) * 100, 3)
        yearly = {}
        for y in range(2017, 2027):
            sel = (C.index >= f"{y}0101") & (C.index <= f"{y}1231")
            pnl = (val[sel] * after[5][sel]).sum(axis=1).sum()
            yearly[str(y)] = round(float(pnl / gross[sel].sum(axis=1).sum()) * 100, 3)
        res["해마다 5일"] = yearly
        out["B 단타 손익 어림"][w] = res
    Z.SP.mkdir(parents=True, exist_ok=True)
    (Z.SP / "z004.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[A 사건 모양 · 초과 %]")
    for k, v in out["A 사건 모양"].items():
        print(f"  {k:24s} " + " · ".join(f"{a} {b:+.2f}" for a, b in v.items()))
    print("\n[B 단타 손익 어림 · 매매 금액 대비 % · 시장 뺌]")
    for k, v in out["B 단타 손익 어림"].items():
        print(f"  {k:4s} " + " · ".join(f"{a} {b:+.3f}" for a, b in v.items() if a != "해마다 5일") + " · 해마다 5일 " + " ".join(f"{y[2:]}:{b:+.2f}" for y, b in v["해마다 5일"].items()))


if __name__ == "__main__":
    main()
