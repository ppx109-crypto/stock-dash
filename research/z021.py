"""P4b — 전문 트레이더 갈래(docs/RL-PRO.md): 사건 바구니 C를 1일봉 계좌의 '쉬는 돈'에.
- 사건(그날 시총 200위 안 · 같은 갈래 같은 종목 20거래일 안 겹침 없음): 자사주 취득 · 무상증자. 반응 = t0−1 → t0 종가 초과(그날 대상 가운데값 뺌).
  (P2 z012 표는 '뒤 60일 값이 있는 사건만' 남겨 자르기에 걸리므로 여기서 사건을 새로 만듦 — t0까지 값만.)
- 바구니: 공시 다음 날(t0+1) 종가 · 5칸 · 20거래일 · 비용 0.5%(z018과 같음).
- **문턱 다시 고르기(앞 반 2017 ~ 21만)**: 자사주 취득 반응 문턱 {없음, 0, −1, −2, −3, −5%} · 무상증자는 늘 넣음 → 앞 반 연 수익이 가장 높고 하루 · 달 손실 −15% 안인 것.
- 합친 계좌(지금 운영 조합 = 1일봉 장부 + 빈칸 엔진 · 덤프 dd_now.npz):
  쉬는 돈(1 − 1일봉이 쓴 몫, 전날 값)을 바구니가 먼저 쓰고, 빈칸 엔진은 남은 몫만 → 합친 = 1일봉 + 쉬는 돈 × 바구니 수익 + 엔진 몫 × (1 − 바구니 든 몫).
  (어림: 쉬는 돈 크기가 날마다 바뀌는 것을 바구니 비율로 맞춤)
- Z_PART=check: Z_CUT으로 자른 자료로 다시 돌려 자른 날 앞까지 바구니 날마다 수익이 한 칸도 안 다른지(자르기 시험).
python research/z021.py · Z_PART=check python research/z021.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

SLOTS, HOLD, COST = 5, 20, 0.005
TH = (None, 0.0, -0.01, -0.02, -0.03, -0.05)
DUMP = Z.SP / "dd_now.npz"


def events(C, evs, inside):
    days = list(C.index)
    r1 = C / C.shift(1) - 1
    react = r1.sub(r1.where(inside).median(axis=1), axis=0)
    rows = []
    for c in C.columns:
        last = {}
        for d, k in evs.get(c, []):
            if k not in ("무상증자", "자사주취득") or d < "20170101":
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


def simulate(C, ev):
    """돌려줌: 바구니 하루 수익(바구니 돈 기준) · 든 몫(그날 끝)."""
    days = list(C.index)
    pos = {d: i for i, d in enumerate(days)}
    want = {}
    for r in ev.itertuples():
        j = pos.get(r.날)
        if j is not None and j + 1 < len(days):
            want.setdefault(days[j + 1], []).append(r.코드)
    held, cash, eq, inv = {}, 1.0, [], []
    for i, d in enumerate(days):
        px = C.iloc[i]
        for c in [c for c, (k, p0, m) in held.items() if i - k >= HOLD]:
            k, p0, m = held.pop(c)
            p = px[c] if px[c] == px[c] else p0
            cash += m * p / p0 * (1 - COST / 2)
        value = cash + sum(m * (px[c] / p0 if px[c] == px[c] else 1) for c, (k, p0, m) in held.items())
        for c in want.get(d, []):
            if len(held) >= SLOTS or c in held or not (px[c] == px[c]):
                continue
            m = min(value / SLOTS, cash)
            if m <= 0:
                break
            cash -= m
            held[c] = (i, px[c] * (1 + COST / 2), m)
        tot = cash + sum(m * (px[c] / p0 if px[c] == px[c] else 1) for c, (k, p0, m) in held.items())
        eq.append(tot)
        inv.append(1 - cash / tot)
    eq = pd.Series(eq, index=days)
    return eq.pct_change().fillna(0.0), pd.Series(inv, index=days)


def pick(ev, th):
    if th is None:
        return ev
    return ev[(ev["갈래"] == "무상증자") | (ev["반응"] < th)]


def stats(r, lo, hi):
    x = r[(r.index >= lo) & (r.index < hi)]
    e = (1 + x).cumprod()
    mon = (1 + x).groupby(pd.to_datetime(x.index).to_period("M")).prod() - 1
    return dict(ann=e.iloc[-1] ** (245 / len(x)) - 1, mdd=(e / e.cummax() - 1).min(), day=x.min(),
                dday=x.idxmin(), mon=mon.min(), dmon=str(mon.idxmin()))


def fmt(s):
    return f"연 {s['ann'] * 100:+5.1f}% · 골 {s['mdd'] * 100:6.1f}% · 나쁜 하루 {s['day'] * 100:5.1f}%({s['dday']}) · 나쁜 달 {s['mon'] * 100:5.1f}%({s['dmon']})"


HALVES = (("앞 2017~21", "20170101", "20220101"), ("뒤 2022~26", "20220101", "20991231"))


def main():
    C, F, ops, evs, qs, name = Z.load()
    C = C[C.index >= "20161001"]
    inside, _ = Z.universe(C)
    ev = events(C, evs, inside)
    if os.getenv("Z_OUT"):                       # 자르기 시험용
        r, inv = simulate(C, pick(ev, float(os.getenv("Z_TH", "-0.02"))))
        pd.DataFrame({"r": r, "inv": inv}).to_csv(os.environ["Z_OUT"])
        return
    print(f"사건 {len(ev)}건(자사주 취득 {int((ev['갈래'] == '자사주취득').sum())} · 무상증자 {int((ev['갈래'] == '무상증자').sum())})")
    print("\n[1] 바구니 따로 · 자사주 반응 문턱별(앞 반으로 고름 · 뒤 반은 보기만)")
    res = {}
    for th in TH:
        r, inv = simulate(C, pick(ev, th))
        a, b = stats(r, *HALVES[0][1:]), stats(r, *HALVES[1][1:])
        res[th] = (r, inv, a)
        lab = "없음(모두)" if th is None else f"< {th * 100:+.0f}%"
        print(f"  문턱 {lab:9s} 사건 {len(pick(ev, th)):4d} | 앞 {fmt(a)}\n  {'':24s}| 뒤 {fmt(b)}")
    ok = [th for th in TH if res[th][2]["day"] > -0.15 and res[th][2]["mon"] > -0.15]
    best = max(ok, key=lambda t: res[t][2]["ann"])
    print(f"  → 앞 반으로 고른 문턱: {'없음' if best is None else f'{best * 100:+.0f}%'}")
    z = np.load(DUMP)
    D = [str(d) for d in z["days"]]
    d1, mix, used = (pd.Series(z[k], index=D) for k in ("d1", "mix", "used"))
    eng = mix - d1
    prev_free = (1 - used).clip(0, 1).shift(1).fillna(1.0)
    print("\n[2] 합친 계좌(지금 운영 조합 + 바구니가 쉬는 돈을 먼저 · 엔진은 남은 몫)")
    for lab, s in (("지금 운영 조합", mix),):
        print(f"  [{lab}]\n    " + "\n    ".join(f"{h}: {fmt(stats(s, lo, hi))}" for h, lo, hi in HALVES))
    for th in sorted({best, -0.01, -0.03}, key=lambda t: -9 if t is None else t):
        r, inv, _ = res[th]
        r, inv = r.reindex(D).fillna(0.0), inv.reindex(D).fillna(0.0)
        comb = d1 + prev_free * r + eng * (1 - inv.shift(1).fillna(0.0))
        lab = f"+ 바구니(문턱 {'없음' if th is None else f'{th * 100:+.0f}%'}{' · 앞 반으로 고름' if th == best else ' · 이웃 문턱'})"
        print(f"  [{lab}] 바구니가 쉬는 돈에서 든 몫 평균 {(prev_free * inv).loc['20170101':].mean():.0%}\n    "
              + "\n    ".join(f"{h}: {fmt(stats(comb, lo, hi))}" for h, lo, hi in HALVES))


def check():
    cut = os.getenv("Z_CUT_AT", "20220103")
    out = {}
    for tag, env in (("full", {}), ("cut", {"Z_CUT": cut})):
        p = Z.SP / f"z021_{tag}.csv"
        subprocess.run([sys.executable, __file__], env={**os.environ, **env, "Z_OUT": str(p), "Z_PART": ""}, check=True)
        out[tag] = pd.read_csv(p, index_col=0, dtype={0: str})
    a, b = out["full"], out["cut"]
    a.index, b.index = a.index.astype(str), b.index.astype(str)
    common = [d for d in b.index if d < cut]
    diff = (a.loc[common] - b.loc[common]).abs().max().max()
    print(f"자르기 시험(Z_CUT={cut}): 자른 날 앞 {len(common)}날 · 바구니 수익 · 든 몫 가장 큰 차이 {diff:.2e} → {'통과' if diff < 1e-12 else '실패'}")


if __name__ == "__main__":
    check() if os.getenv("Z_PART") == "check" else main()
