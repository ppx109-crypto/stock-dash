"""B8 — 봇 강화(docs/RL-BOTS.md · 오푸스 검토 ②): 사건 바구니 C 숫자 고원 + 시설투자 더하기.
z021과 같은 사건(그날 시총 200위 · 같은 갈래 20일 겹침 없음 · 반응 = t0 종가 초과) · 공시 다음 날 종가에 삼 · 비용 0.5%.
판: 칸 3 · 5 · 8 × 들기 10 · 20 · 30 · 40일 × (C = 자사주 반응 < −2% + 무상증자) / (C + 시설투자 반응 < −2%).
고르기: 앞 반(2017 ~ 21) 바구니 따로 연 수익(하루 · 달 손실 −15% 안) → 뒤 반(2022 ~ 26) 시험 · 고른 판은 합친 계좌(지금 운영 조합 + 바구니 먼저)도.
python research/z031.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402
import z021 as B  # noqa: E402


def events3(C, evs, inside):
    keep = {c: [(d, k) for d, k in v if k in ("무상증자", "자사주취득", "시설투자")] for c, v in evs.items()}
    old = B.events.__globals__
    # z021.events는 두 갈래만 봄 → 같은 셈을 세 갈래로
    days = list(C.index)
    r1 = C / C.shift(1) - 1
    react = r1.sub(r1.where(inside).median(axis=1), axis=0)
    rows = []
    for c in C.columns:
        last = {}
        for d, k in keep.get(c, []):
            if d < "20170101":
                continue
            j = int(np.searchsorted(days, d))
            if j >= len(days):
                continue
            t0 = days[j]
            if not inside.at[t0, c] or (k in last and j - last[k] < 20):
                continue
            last[k] = j
            rows.append((k, c, t0, react.at[t0, c]))
    return pd.DataFrame(rows, columns=["갈래", "코드", "날", "반응"]).dropna(subset=["반응"])


def pick(ev, fac):
    m = (ev["갈래"] == "무상증자") | ((ev["갈래"] == "자사주취득") & (ev["반응"] < -0.02))
    if fac:
        m |= (ev["갈래"] == "시설투자") & (ev["반응"] < -0.02)
    return ev[m]


def main():
    C, F, ops, evs, qs, name = Z.load()
    C = C[C.index >= "20161001"]
    inside, _ = Z.universe(C)
    ev = events3(C, evs, inside)
    print(f"사건: 자사주 {int((ev['갈래'] == '자사주취득').sum())} · 무상증자 {int((ev['갈래'] == '무상증자').sum())} · 시설투자 {int((ev['갈래'] == '시설투자').sum())}", flush=True)
    res = []
    for fac in (False, True):
        for slots in (3, 5, 8):
            for hold in (10, 20, 30, 40):
                B.SLOTS, B.HOLD = slots, hold
                r, inv = B.simulate(C, pick(ev, fac))
                a, b = B.stats(r, *B.HALVES[0][1:]), B.stats(r, *B.HALVES[1][1:])
                res.append((fac, slots, hold, a, b, r, inv))
                print(f"  {'C+시설' if fac else 'C    '} 칸 {slots} · {hold:2d}일 | 앞 {B.fmt(a)} | 뒤 {B.fmt(b)}", flush=True)
    ok = [x for x in res if x[3]["day"] > -0.15 and x[3]["mon"] > -0.15]
    best = max(ok, key=lambda x: x[3]["ann"])
    fac, slots, hold, a, b, r, inv = best
    print(f"\n앞 반으로 고른 판: {'C+시설' if fac else 'C'} · 칸 {slots} · {hold}일 (지금 운영: C · 칸 5 · 20일)")
    z = np.load(B.DUMP)
    D = [str(d) for d in z["days"]]
    d1, mix, used = (pd.Series(z[k], index=D) for k in ("d1", "mix", "used"))
    eng = mix - d1
    pf = (1 - used).clip(0, 1).shift(1).fillna(1.0)
    for lab, (rr, ii) in (("지금 C · 5칸 · 20일", next((x[5], x[6]) for x in res if not x[0] and x[1] == 5 and x[2] == 20)),
                          ("고른 판", (r, inv))):
        rr, ii = rr.reindex(D).fillna(0.0), ii.reindex(D).fillna(0.0)
        comb = d1 + pf * rr + eng * (1 - ii.shift(1).fillna(0.0))
        print(f"  합친 계좌 [{lab}] " + " | ".join(f"{h}: {B.fmt(B.stats(comb, lo, hi))}" for h, lo, hi in B.HALVES))


if __name__ == "__main__":
    main()
