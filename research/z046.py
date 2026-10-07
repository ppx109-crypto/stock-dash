"""후보 전략 성적표 ② — 공시 사건 바구니들(보고서 TOP 10 · 20개 후보용).
공통: 사건 날 t0 = DART 접수일(장 중 · 뒤 모름 → 다음 날부터 씀) · 그날 시총 200위 · 같은 종목 · 같은 갈래 20거래일 안 겹침 없음 ·
  반응 = t0 종가 초과(그날 200위 가운데값 뺌) · 사기 = t0+1 종가(또는 '수급 확인' 판은 t0+6 종가) · 칸 K · 들기 H거래일 · 비용 왕복 0.5%(사고팔 때 반씩).
계좌: 빈 칸 있을 때만 사고 · 한 칸 = 계좌 ÷ K · **날마다 평가**(종가) → perf 지표 · 매매 목록 → PF · 승률 · t · 부트스트랩.
기간: 앞 2017 ~ 21(학습) · 뒤 2022 ~ 26 · 시험 2023 ~. 스트레스: 비용 1.0%.
python research/z046.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perf as P  # noqa: E402
import z001 as Z  # noqa: E402


def build(C, F, evs, inside, kinds):
    days = list(C.index)
    r1 = C / C.shift(1) - 1
    react = r1.sub(r1.where(inside).median(axis=1), axis=0)
    fi = F["외국인"].reindex(C.index) + F["기관"].reindex(C.index)
    vol = F["vol"].reindex(C.index)
    rows = []
    for c in C.columns:
        last = {}
        for d, k in evs.get(c, []):
            if k not in kinds or d < "20170101":
                continue
            j = int(np.searchsorted(days, d))
            if j + 1 >= len(days):
                continue
            t0 = days[j]
            if not inside.at[t0, c] or (k in last and j - last[k] < 20):
                continue
            last[k] = j
            fl = fi[c].iloc[j + 1:j + 6].sum() / vol[c].iloc[j + 1:j + 6].sum() if j + 6 < len(days) and vol[c].iloc[j + 1:j + 6].sum() else np.nan
            rows.append((k, c, t0, j, react.at[t0, c], fl))
    return pd.DataFrame(rows, columns=["갈래", "코드", "날", "j", "반응", "뒤수급"]).dropna(subset=["반응"])


def simulate(C, ev, slots, hold, lag=1, cost=0.005):
    days = list(C.index)
    want = {}
    for r in ev.itertuples():
        if r.j + lag < len(days):
            want.setdefault(r.j + lag, []).append(r.코드)
    held, cash, eq, trades = {}, 1.0, [], []
    px = C.to_numpy()
    col = {c: i for i, c in enumerate(C.columns)}
    for i in range(len(days)):
        row = px[i]
        for c in [c for c, (k, p0, m) in held.items() if i - k >= hold]:
            k, p0, m = held.pop(c)
            p = row[col[c]] if row[col[c]] == row[col[c]] else p0
            cash += m * p / p0 * (1 - cost / 2)
            trades.append((c, days[k], days[i], (p * (1 - cost / 2) / p0 - 1) * 100 + cost * 100, m))   # 비용 전 손익(perf가 cost를 뺌)
        val = lambda: cash + sum(m * ((row[col[c]] / p0) if row[col[c]] == row[col[c]] else 1) for c, (k, p0, m) in held.items())
        v = val()
        for c in want.get(i, []):
            if len(held) >= slots or c in held or not (row[col[c]] == row[col[c]]):
                continue
            m = min(v / slots, cash)
            if m <= 0:
                break
            cash -= m
            held[c] = (i, row[col[c]] * (1 + cost / 2), m)
        eq.append(val())
    eq = pd.Series(eq, index=days)
    return eq.pct_change().fillna(0.0), trades


def main():
    C, F, ops, evs, qs, name = Z.load()
    C = C[C.index >= "20161001"]
    F = {k: v.reindex(C.index) for k, v in F.items()}
    inside, _ = Z.universe(C)
    ev = build(C, F, evs, inside, ("자사주취득", "무상증자", "공급계약", "시설투자", "잠정실적", "대량보유", "유상증자", "최대주주변경"))
    S = {
        "E1 자사주 취득 전부(5칸 · 20일)": (ev[ev["갈래"] == "자사주취득"], 5, 20, 1),
        "E2 자사주 취득 · 반응 < −2%": (ev[(ev["갈래"] == "자사주취득") & (ev["반응"] < -0.02)], 5, 20, 1),
        "E3 무상증자 전부": (ev[ev["갈래"] == "무상증자"], 5, 20, 1),
        "E4 바구니 C(E2 + E3 · 운영)": (ev[((ev["갈래"] == "자사주취득") & (ev["반응"] < -0.02)) | (ev["갈래"] == "무상증자")], 5, 20, 1),
        "E5 바구니 C · 8칸(보수)": (ev[((ev["갈래"] == "자사주취득") & (ev["반응"] < -0.02)) | (ev["갈래"] == "무상증자")], 8, 20, 1),
        "E6 공급계약 · 반응 < −2%": (ev[(ev["갈래"] == "공급계약") & (ev["반응"] < -0.02)], 5, 20, 1),
        "E7 공급계약 전부": (ev[ev["갈래"] == "공급계약"], 5, 20, 1),
        "E8 시설투자 · 반응 < −2%": (ev[(ev["갈래"] == "시설투자") & (ev["반응"] < -0.02)], 5, 20, 1),
        "E9 잠정실적 · 반응 > +2%(따라 사기)": (ev[(ev["갈래"] == "잠정실적") & (ev["반응"] > 0.02)], 5, 20, 1),
        "E10 대량보유 보고 전부": (ev[ev["갈래"] == "대량보유"], 5, 20, 1),
        "E11 유상증자(사기 시험)": (ev[ev["갈래"] == "유상증자"], 5, 20, 1),
        "E12 최대주주변경 + 뒤 5일 외국인 · 기관 붙음(> 3% · t0+6 사기)": (ev[(ev["갈래"] == "최대주주변경") & (ev["뒤수급"] > 0.03)], 5, 20, 6),
        "E13 시설투자 · 반응 < −2% + 수급 붙음(t0+6)": (ev[(ev["갈래"] == "시설투자") & (ev["반응"] < -0.02) & (ev["뒤수급"] > 0.03)], 5, 20, 6),
    }
    for lab, (e, K, H, lag) in S.items():
        print(f"== {lab} · 사건 {len(e)} ==", flush=True)
        for cost in (0.005, 0.010):
            r, tr = simulate(C, e, K, H, lag, cost)
            trs = [(c, b, d, p, m) for c, b, d, p, m in tr]
            for h, lo, hi in (("앞 2017 ~ 21", "20170101", "20220101"), ("뒤 2022 ~ 26", "20220101", "20991231"), ("시험 2023 ~", "20230101", "20991231")):
                tt = [t for t in trs if lo <= t[1] < hi]
                print(f"  비용 {cost * 100:.1f}% {h}: {P.fmt(P.trade_stats(tt, cost=cost))}")
                print(f"  {'':18s} 계좌: {P.fmt(P.account_stats(r, lo, hi))}", flush=True)
            if cost == 0.005:
                pass


if __name__ == "__main__":
    main()
