"""Q2 · Q3 · Q7 · Q8 — 공시 → 주가 반응 → 그 뒤 수급(사용자 2026-10-07 퀀트 연구 요청).
A. 공시 뒤 '수급이 붙는지'를 **확인하고** 사기: 공시 날 t0(접수일 · 그날 시총 200위) → t0+1 ~ t0+5 외국인 + 기관 순매수 합(÷ 그 5일 거래량)을 본 뒤
   **t0+6 종가에 삼** · 20일 들기. 수급 붙음(> +3%) / 보통 / 빠짐(< −3%) × 공시 갈래 × 반응(t0 초과 ±2%).
   비교: 같은 공시를 t0+1 종가에 산 것(P1 방식). → Q3 '수급이 붙을 때 기대수익이 얼마나 느나' · Q8 '반응 없던 공시(보통)에 수급이 붙으면?'.
B. 거래대금 급증(그날 거래대금 ≥ 앞 20일 평균 × 3 · 그날 값 +) 날을 누가 샀나로 나눔(Q7): 외국인 + 기관 > 0 vs 개인만 + → t+1 종가에 사서 5 · 20일.
모든 값은 바탕(그날 대상 가운데값) 뺀 초과 · 비용 0.5% 뺀 평균 · 나을 확률 · 앞(2017 ~ 21)/뒤(2022 ~ 26).
python research/z041.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

KINDS = ("공급계약", "자사주취득", "주식소각", "무상증자", "시설투자", "잠정실적", "배당", "유상증자", "전환사채", "최대주주변경", "대량보유", "자사주처분")


def main():
    C, F, ops, evs, qs, name = Z.load()
    C = C[C.index >= "20160601"]
    F = {k: v.reindex(C.index) for k, v in F.items()}
    inside, _ = Z.universe(C)
    days = list(C.index)
    r1 = C / C.shift(1) - 1
    react = r1.sub(r1.where(inside).median(axis=1), axis=0)
    inst = F["외국인"].add(F["기관"], fill_value=np.nan) if "기관" in F else F["외국인"]
    def fwd_from(lag, h):
        f = C.shift(-(lag + h)) / C.shift(-lag) - 1
        return f.sub(f.where(inside).median(axis=1), axis=0)
    f1, f6 = fwd_from(1, 20), fwd_from(6, 20)
    rows = []
    for c in C.columns:
        last = {}
        for d, k in evs.get(c, []):
            if k not in KINDS or d < "20170101":
                continue
            j = int(np.searchsorted(days, d))
            if j + 26 >= len(days):
                continue
            t0 = days[j]
            if not inside.at[t0, c] or (k in last and j - last[k] < 20):
                continue
            last[k] = j
            fl = inst[c].iloc[j + 1:j + 6].sum()
            vv = F["vol"][c].iloc[j + 1:j + 6].sum()
            rows.append((k, t0, react.at[t0, c], fl / vv if vv else np.nan, f1.at[t0, c], f6.at[t0, c]))
    E = pd.DataFrame(rows, columns=["갈래", "날", "반응", "뒤수급", "t1사기", "t6사기"]).dropna()
    E["반"] = np.where(E["날"] < "20220101", "앞", "뒤")
    E["반응칸"] = np.where(E["반응"] > 0.02, "오름", np.where(E["반응"] < -0.02, "내림", "보통"))
    E["수급칸"] = np.where(E["뒤수급"] > 0.03, "붙음", np.where(E["뒤수급"] < -0.03, "빠짐", "보통"))
    print(f"[A] 공시 {len(E)}건 · 수급 붙음 {int((E['수급칸'] == '붙음').sum())} · 빠짐 {int((E['수급칸'] == '빠짐').sum())}")
    print("  표: 갈래 × 반응 · (t0+1 종가 사기) vs 수급 붙음/빠짐 확인 뒤 t0+6 사기 · 20일 초과 평균[앞/뒤] · 나을 확률 · 비용 0.5% 뒤")
    def cell(g, col):
        a, b = g[g["반"] == "앞"][col], g[g["반"] == "뒤"][col]
        return f"{g[col].mean() * 100:+.2f}[{a.mean() * 100:+.2f}/{b.mean() * 100:+.2f}] {(g[col] > 0).mean():.0%} → {(g[col].mean() - 0.005) * 100:+.2f}"
    for k in KINDS:
        for rk in ("오름", "보통", "내림"):
            g = E[(E["갈래"] == k) & (E["반응칸"] == rk)]
            if len(g) < 40:
                continue
            s = f"  {k:6s} {rk} {len(g):4d}건 | t1 {cell(g, 't1사기')}"
            for fk in ("붙음", "빠짐"):
                h = g[g["수급칸"] == fk]
                s += f" | {fk} {len(h):3d}건 t6 {cell(h, 't6사기')}" if len(h) >= 20 else f" | {fk} {len(h)}건(적음)"
            print(s, flush=True)
    print("  전체(모든 갈래):")
    for fk in ("붙음", "보통", "빠짐"):
        h = E[E["수급칸"] == fk]
        print(f"    수급 {fk} {len(h)}건 t6 {cell(h, 't6사기')}", flush=True)
    # B. 거래대금 급증
    ok = inside & pd.DataFrame(np.repeat((C.index >= "20170101")[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    surge = (F["value"] >= F["value"].rolling(20, min_periods=15).mean().shift(1) * 3) & (r1 > 0) & ok
    fi = F["외국인"] + (F["기관"] if "기관" in F else 0)
    who = {"외국인 + 기관 순매수 > 0": surge & (fi > 0), "개인만 순매수(외국인 + 기관 ≤ 0)": surge & (fi <= 0)}
    first = pd.Series(C.index < "20220101", index=C.index)
    print("\n[B] 거래대금 급증(앞 20일 평균 × 3 · 그날 +) · t+1 종가에 사서 · 바탕 뺀 초과[앞/뒤] · 나을 확률 · 그날 초과")
    for h in (5, 20):
        f = fwd_from(1, h)
        b = f.where(ok).stack().dropna()
        for lab, g in who.items():
            e = f.where(g)
            s, sf, sb = e.stack().dropna(), e[first].stack().dropna(), e[~first].stack().dropna()
            td = react.where(g).stack().dropna()
            print(f"  {h:2d}일 {lab:24s} {len(s):5d}건 · {(s.mean() - b.mean()) * 100:+.2f}%p [{(sf.mean()) * 100 - b.mean() * 100:+.2f}/{(sb.mean() - b.mean()) * 100:+.2f}] · "
                  f"나을 {(s > 0).mean():.0%} · 그날 {td.mean() * 100:+.1f}%", flush=True)


if __name__ == "__main__":
    main()
