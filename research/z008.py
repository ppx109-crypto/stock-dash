"""N1 — 좁은 장(시장 폭 < 50%)에서도 오르는 종목의 특징(사용자 2026-10-07 "과열시장 50%밑에서도 오르는 종목은 있어 …
단타가 아니어도 좋으니 그 특징들을 찾아서 적용해보자 · 타이머 1시간으로 RL 연구방식으로 계속"). docs/RL-NARROW.md.
- 국면(그날까지 값만): 시장 폭 = 그날 시총 100위 안에서 50일선 > 200일선 비율(final_group과 같은 셈 · 날마다 다시 셈)
  · 지수 오름 = 코스피 종가 ≥ 60일선. → '좁은 오름장'(폭 < 50 · 지수 오름) · '내림장'(폭 < 50 · 지수 아래) · '넓은 장'(폭 ≥ 50).
- 재료 · 잣대는 Z1(z001)과 같음: t까지 자료 · t+1 종가에 사서 20거래일 · 대상 = 그날 시총 200위 안 · 그날 가운데값 뺀 초과.
- 국면별 · 기간별(2017~22 고르기 / 2023~26 시험) IC · 위 1/5 − 아래 1/5. 고르기 = 2017~19 · 2020~22 두 반 같은 쪽 · |t| ≥ 1.5(국면 날이 적어 Z1보다 낮춤).
python research/z008.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

TMIN = 1.5


def regimes(C, size):
    """날마다 국면 — 그날 값만(가로줄 · 앞으로 굴린 평균)."""
    top100 = size.rank(axis=1, ascending=False) <= 100
    up = (C.rolling(50).mean() > C.rolling(200).mean()).where(C.rolling(200).count() >= 200)
    breadth = (up.where(top100)).mean(axis=1) * 100
    k = json.loads(Path("market-data/index_KOSPI.json").read_text(encoding="utf-8"))["rows"]
    kc = pd.Series({str(r["date"]): float(r["종가"]) for r in k if Z._keep(r["date"])}).reindex(C.index)
    kup = kc >= kc.rolling(60, min_periods=60).mean()
    reg = pd.Series("넓은 장", index=C.index)
    reg[(breadth < 50) & kup] = "좁은 오름장"
    reg[(breadth < 50) & ~kup & kc.rolling(60, min_periods=60).mean().notna()] = "내림장"
    reg[kc.rolling(60, min_periods=60).mean().isna()] = "모름"
    return reg, breadth


def period(d):
    y = int(d[:4])
    return "2017~19" if y <= 2019 else "2020~22" if y <= 2022 else "2023~26"


def evaluate(X, C, inside, reg):
    fwd = Z.forward(C)
    days = [d for i, d in enumerate(C.index) if d >= Z.START and i % Z.STEP == 0 and i + Z.GAP + Z.H < len(C.index)]
    res = {}
    for name, F in X.items():
        if name.startswith("엿보기"):
            continue
        acc = {}
        for d in days:
            ok = inside.loc[d] & F.loc[d].notna() & fwd.loc[d].notna()
            if ok.sum() < 40:
                continue
            f, r = F.loc[d][ok], fwd.loc[d][ok]
            if f.nunique() < 2:
                continue
            r = r - r.median()
            ic = f.rank().corr(r.rank())
            if f.nunique() <= 5 or (f == f.min()).mean() > 0.2:
                hi, lo = f > f.min(), f == f.min()
                sp = r[hi].mean() - r[lo].mean() if hi.sum() >= 3 else np.nan
            else:
                q = f.rank(pct=True)
                sp = r[q > 0.8].mean() - r[q <= 0.2].mean()
            for key in ((reg[d], period(d)), (reg[d], "전체")):
                acc.setdefault(key, []).append((ic, sp))
        out = {}
        for (rg, p), v in acc.items():
            a = np.array([x[0] for x in v], dtype=float)
            a = a[~np.isnan(a)]
            s = np.array([x[1] for x in v], dtype=float)
            s = s[~np.isnan(s)]
            if len(a) < 4:
                continue
            t = a.mean() / (a.std(ddof=1) + 1e-12) * math.sqrt(len(a) / (Z.H / Z.STEP))
            out.setdefault(rg, {})[p] = {"IC": round(float(a.mean()), 4), "t": round(float(t), 2),
                                         "위-아래(%)": round(float(s.mean()) * 100, 2) if len(s) else None, "날수": int(len(a))}
        res[name] = out
    return res


def pick(res, rg):
    got = []
    for f, out in res.items():
        o = out.get(rg, {})
        a, b = o.get("2017~19"), o.get("2020~22")
        if a and b and np.sign(a["IC"]) == np.sign(b["IC"]) and min(abs(a["t"]), abs(b["t"])) >= TMIN:
            got.append((f, "+" if a["IC"] > 0 else "−", a, b, o.get("2023~26")))
    return got


def main():
    C, F, ops, evs, qs, name = Z.load()
    X = Z.features(C, F, ops, evs, qs)
    inside, size = Z.universe(C)
    reg, breadth = regimes(C, size)
    days = reg[reg.index >= Z.START]
    print("국면 날 수(2017-03 ~):", days.value_counts().to_dict(), "· 오늘", reg.index[-1], reg.iloc[-1], f"폭 {breadth.iloc[-1]:.0f}%")
    res = evaluate(X, C, inside, reg)
    out = {"국면 날 수": days.value_counts().to_dict(), "재료별": res}
    for rg in ("좁은 오름장", "내림장", "넓은 장"):
        ch = pick(res, rg)
        out[f"고른 재료({rg})"] = [(f, s, a, b, c) for f, s, a, b, c in ch]
        print(f"\n[{rg}] 2017~22 두 반 같은 쪽 · |t| ≥ {TMIN} → 2023~26 시험")
        for f, s, a, b, c in sorted(ch, key=lambda x: -abs(x[2]["IC"] + x[3]["IC"])):
            ct = f"{c['IC']:+.3f}({c['t']:+.1f}) {c['위-아래(%)']:+.1f}%" if c and c.get("위-아래(%)") is not None else (f"{c['IC']:+.3f}({c['t']:+.1f})" if c else "-")
            print(f"  {f:16s} {s} | 17~19 {a['IC']:+.3f}({a['t']:+.1f}) | 20~22 {b['IC']:+.3f}({b['t']:+.1f}) | 시험 23~26 {ct}")
    Z.SP.mkdir(parents=True, exist_ok=True)
    (Z.SP / "z008.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
