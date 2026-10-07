"""Z2 — 투신(그리고 외국인 · 기관 · 연기금 · 사모 · 개인)이 얼마나 · 며칠 연속 사거나 팔면 다음 단기 주가가 어떻게 되나
(사용자 2026-10-07 "투신이 얼마나 어떻게 몇일동안 사면 단기주가가 어떻게되는지 · 투신만 오를확률이 높은지 외국인과 다른곳의 매수 매도도").

- 대상: 그날 시가총액 200등 안(그날까지 접수된 주식수 × 그날 종가) · 2017-03 ~ 2026-09.
- 수급(한투 투자자별 · 주식 수)은 장 끝난 뒤 나옴 → 날짜 t까지 수급을 보고 **t+1 종가에 산다**고 잼. 결과 = t+1 → t+1+h 종가 수익(h = 1 · 5 · 10 · 20).
- '초과' = 그날 대상 가운데값을 뺀 수익(시장 오르내림 뺌) · '오를 확률' = 그 수익(초과 아님)이 0보다 큰 비율.
- 표 1 · 연속: 그 투자자가 k일 연속 순매수(또는 순매도)한 **첫 날**(정확히 k일째)만 셈 → 같은 흐름을 여러 번 세지 않음.
- 표 2 · 세기: 5일 · 20일 순매수 합 ÷ 같은 기간 거래량(%) 구간별.
- 표 3 · 같이/엇갈림: 투신 5일 순매수(+/−) × 외국인 5일(+/−).
- 앞 반(2017~21) · 뒤 반(2022~26)을 따로 적어 버티는지 봄. t는 날마다 평균을 낸 뒤 겹침(h/1일)을 나눠 줄인 값.
미래 참조: 재료는 날짜 t 이하 수급만(뒤로 굴리는 합 · 연속 셈) · 진입 t+1. 자르기 · 더럽히기 · 검사 눈 시험은 `python research/z002.py check`.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402  (같은 읽기 · 대상 · 자르기 장치)

WHO = ("투신", "외국인", "기관", "연기금", "사모", "개인")
HS = (1, 5, 10, 20)
KS = (1, 2, 3, 5, 7, 10)
SP = Z.SP


def streak(sign):
    """날마다 '같은 쪽(+1/−1) 연속 며칠째' — 그날까지 값만으로(앞으로 굴림)."""
    a = sign.to_numpy()
    out = np.zeros_like(a, dtype=float)
    run = np.zeros(a.shape[1])
    for i in range(a.shape[0]):
        row = a[i]
        same = (row == 1)
        run = np.where(np.isnan(row), 0, np.where(same, run + 1, 0))
        out[i] = run
    return pd.DataFrame(out, index=sign.index, columns=sign.columns).where(sign.notna())


def materials(C, F):
    M = {}
    for w in WHO:
        net = F[w]
        s = np.sign(net).where(net.notna())
        M[f"{w}_연속매수"] = streak((s > 0).astype(float).where(s.notna()))
        M[f"{w}_연속매도"] = streak((s < 0).astype(float).where(s.notna()))
        for n in (5, 20):
            M[f"{w}_{n}일세기"] = net.rolling(n, min_periods=n).sum() / F["vol"].rolling(n, min_periods=n).sum() * 100
    # 검사 눈: 일부러 다음 날 수급을 쓴 재료(미래) — 시험에 반드시 걸려야 함
    M["엿보기"] = F["투신"].shift(-1)
    return {k: (v if k == "엿보기" else v.where(C.notna())) for k, v in M.items()}


def returns(C, inside):
    R = {}
    for h in HS:
        r = C.shift(-(1 + h)) / C.shift(-1) - 1
        r = r.where(inside)
        R[h] = (r, r.sub(r.median(axis=1), axis=0))
    return R


def half(d):
    return "앞(17~21)" if d < "20220101" else "뒤(22~26)"


def summarize(mask, R, days_ok):
    """mask[날 × 종목] True인 사건들의 h일 결과. 날마다 평균 → 평균 · t(겹침 줄임) · 오를 확률 · 건수."""
    out = {}
    for part in ("전체", "앞(17~21)", "뒤(22~26)"):
        cell = {}
        for h in HS:
            raw, ex = R[h]
            m = mask & raw.notna() & days_ok
            if part != "전체":
                sel = np.array([half(d) == part for d in m.index])
                m = m & pd.DataFrame(np.repeat(sel[:, None], m.shape[1], axis=1), index=m.index, columns=m.columns)
            n = int(m.to_numpy().sum())
            if n < 30:
                cell[h] = None
                continue
            exv = ex.where(m)
            daily = exv.mean(axis=1).dropna()
            t = daily.mean() / (daily.std(ddof=1) + 1e-12) * math.sqrt(len(daily) / max(1, h))
            cell[h] = {"초과(%)": round(float(np.nanmean(exv.to_numpy())) * 100, 2), "t": round(float(t), 1),
                       "오를 확률(%)": round(float((raw.where(m).to_numpy() > 0).sum() / n) * 100, 1),
                       "시장보다 나을 확률(%)": round(float((exv.to_numpy() > 0).sum() / n) * 100, 1), "건수": n}
        out[part] = cell
    return out


def main():
    C, F, *_ = Z.load()
    inside, _ = Z.universe(C)
    days_ok = pd.DataFrame(np.repeat((C.index >= Z.START)[:, None], C.shape[1], axis=1), index=C.index, columns=C.columns)
    M = materials(C, F)
    R = returns(C, inside)
    base = summarize(inside & days_ok, R, days_ok)
    res = {"바탕(대상 아무 날)": base, "연속": {}, "세기": {}, "같이": {}}
    for w in WHO:
        for side in ("매수", "매도"):
            st = M[f"{w}_연속{side}"]
            for k in KS:
                res["연속"][f"{w} {k}일 연속 {side}"] = summarize((st == k) & inside, R, days_ok)
        for n in (5, 20):
            x = M[f"{w}_{n}일세기"]
            bins = [(-1e9, -10), (-10, -5), (-5, -1), (-1, 1), (1, 5), (5, 10), (10, 1e9)]
            for lo, hi in bins:
                lab = f"{w} {n}일 순매수/거래량 {'' if lo < -1e8 else lo}~{'' if hi > 1e8 else hi}%"
                res["세기"][lab] = summarize((x > lo) & (x <= hi) & inside, R, days_ok)
    t5, f5 = M["투신_5일세기"], M["외국인_5일세기"]
    for a, fa in (("투신+", t5 > 1), ("투신−", t5 < -1)):
        for b, fb in (("외국인+", f5 > 1), ("외국인−", f5 < -1)):
            res["같이"][f"{a} {b}(5일 · 거래량 1% 넘게)"] = summarize(fa & fb & inside, R, days_ok)
    res["같이"]["투신+ 연기금+ 외국인+(5일)"] = summarize((t5 > 1) & (M["연기금_5일세기"] > 1) & (f5 > 1) & inside, R, days_ok)
    res["같이"]["투신+ 개인−(5일)"] = summarize((t5 > 1) & (M["개인_5일세기"] < -1) & inside, R, days_ok)
    SP.mkdir(parents=True, exist_ok=True)
    (SP / "z002.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    show(res)


def fmt(c):
    return "-" if not c else f"{c['초과(%)']:+.2f}%({c['t']:+.1f}) 오름{c['오를 확률(%)']:.0f}%"


def show(res):
    b = res["바탕(대상 아무 날)"]["전체"]
    print("바탕(대상 아무 날):", {h: fmt(b[h]) for h in HS})
    for sec in ("연속", "세기", "같이"):
        print(f"\n[{sec}]  1일 | 5일 | 10일 | 20일 (초과 · t · 오를 확률) · 건수 · 20일 앞/뒤 반")
        for k, v in res[sec].items():
            a = v["전체"]
            n = (a.get(20) or a.get(5) or {}).get("건수", 0)
            halves = " / ".join(fmt((v[p] or {}).get(20)) for p in ("앞(17~21)", "뒤(22~26)"))
            print(f"{k:34s} " + " | ".join(fmt(a.get(h)) for h in HS) + f" · {n}건 · 20일 {halves}")


def check():
    cut = os.getenv("Z_CUT") or "20220615"
    Z.CUT, Z.POISON = "", ""
    C0, F0, *_ = Z.load()
    M0 = materials(C0, F0)
    ok = True
    for mode in ("cut", "poison"):
        Z.CUT, Z.POISON = (cut, "") if mode == "cut" else ("", cut)
        C1, F1, *_ = Z.load()
        M1 = materials(C1, F1)
        bad, caught = [], False
        for k in M0:
            a = M0[k].loc[M0[k].index <= cut]
            b = M1[k].reindex(index=a.index, columns=a.columns)
            same = np.allclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float), equal_nan=True, atol=1e-9)
            if k == "엿보기":
                caught = not same
            elif not same:
                bad.append(k)
        print(f"[{mode} {cut}] 재료 {len(M0) - 1}개: {'합격' if not bad else '불합격 ' + ', '.join(bad)} · 검사 눈 {'걸림' if caught else '안 걸림(고장)'}")
        ok &= not bad and caught
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(check() if sys.argv[1:2] == ["check"] else main())
