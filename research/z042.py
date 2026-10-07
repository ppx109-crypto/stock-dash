"""Q4 · Q5 · 전략 B · C — 실적 변화 + 수급 + 주가 위치 vs 전통 가치지표(사용자 2026-10-07 퀀트 연구).
사건 = DART 분기 · 반기 · 사업보고서 접수일 t0(quarter-data 접수번호 앞 8자리 · 그날 시총 200위) → **t0+1 종가에 사서** 20 · 60일 초과(그날 대상 가운데값 뺌).
t0에 아는 것만: 이번 보고서 숫자(그날 접수) · 그날까지 KIS 값(수급 20일 · 52주 고점비 · 20일 수익 · 시총).
재료: 영업이익 YoY · 매출 YoY · 영업현금 YoY(cash-data 같은 보고서) · 이익의 질(영업현금 ÷ 영업이익) · 부채비율(부채 ÷ 자본) 변화 ·
      이익 수익률(영업이익 연환산 ÷ 시총 ≈ 1/PER) · 장부 비율(자본 ÷ 시총 ≈ 1/PBR) · 외국인20 · 기관20 · 52주고점비 · 수익20.
견줌(숫자 맞추지 않음 · 같은 무게 순위 합): 가치(이익 수익률 + 장부) / 실적 변화(영업이익 + 매출 + 영업현금 YoY) / 변화 + 수급(외국인 + 기관) + 위치(52주 고점비 낮음 = 덜 오름) 등.
잣대: 사건 날마다(보고 시즌) 순위 IC → 평균 · t · 앞(2017 ~ 21)/뒤(2022 ~ 26) · 위 1/5 − 아래 1/5 · 위 1/5 비용 0.5% 뒤.
python research/z042.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import z001 as Z  # noqa: E402

ANN = {"1분기": 4.0, "반기": 2.0, "3분기": 4 / 3, "사업": 1.0}


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return np.nan


def yoy(a, b):
    a, b = num(a), num(b)
    if not np.isfinite(a) or not np.isfinite(b) or b == 0:
        return np.nan
    return (a - b) / abs(b)


def main():
    C, F, ops, evs, qs, name = Z.load()
    C = C[C.index >= "20160601"]
    X = Z.features(C, F, ops, evs, qs)
    inside, size = Z.universe(C)
    days = list(C.index)
    fwd = {h: (lambda f: f.sub(f.where(inside).median(axis=1), axis=0))(C.shift(-(1 + h)) / C.shift(-1) - 1) for h in (20, 60)}
    rows = []
    for c in C.columns:
        q = json.loads((Path("quarter-data") / f"{c}.json").read_text(encoding="utf-8")).get("rows") if (Path("quarter-data") / f"{c}.json").exists() else None
        cf = json.loads((Path("cash-data") / f"{c}.json").read_text(encoding="utf-8")).get("rows") if (Path("cash-data") / f"{c}.json").exists() else {}
        if not q:
            continue
        for key, v in q.items():
            if not v or not str(v.get("접수번호", ""))[:8].isdigit():
                continue
            d = str(v["접수번호"])[:8]
            if d < "20170101":
                continue
            j = int(np.searchsorted(days, d))
            if j + 61 >= len(days):
                continue
            t0 = days[j]
            if not inside.at[t0, c] or not np.isfinite(size.at[t0, c]):
                continue
            kind = key.split("-")[-1]
            cv = (cf or {}).get(key) or {}
            op, sales, eq, debt = num(v.get("영업이익")), num(v.get("매출")), num(v.get("자본")), num(v.get("부채"))
            eq_ly, debt_ly = num(v.get("자본_작년")), num(v.get("부채_작년"))
            ocf = num(cv.get("영업현금"))
            rows.append(dict(코드=c, 날=t0, 반="앞" if t0 < "20220101" else "뒤",
                             영업이익YoY=yoy(v.get("영업이익"), v.get("영업이익_작년")), 매출YoY=yoy(v.get("매출"), v.get("매출_작년")),
                             영업현금YoY=yoy(cv.get("영업현금"), cv.get("영업현금_작년")),
                             이익의질=ocf / op if np.isfinite(ocf) and np.isfinite(op) and op > 0 else np.nan,
                             부채비율변화=(debt / eq - debt_ly / eq_ly) if all(np.isfinite([debt, eq, debt_ly, eq_ly])) and eq > 0 and eq_ly > 0 else np.nan,
                             이익수익률=op * ANN.get(kind, 1.0) / size.at[t0, c] if np.isfinite(op) else np.nan,
                             장부비율=eq / size.at[t0, c] if np.isfinite(eq) else np.nan,
                             외국인20=X["외국인20"].at[t0, c], 기관20=X["기관20"].at[t0, c], 고점비=X["52주고점비"].at[t0, c],
                             수익20=X["수익20"].at[t0, c], 거래대금증가=X["거래대금증가"].at[t0, c],
                             f20=fwd[20].at[t0, c], f60=fwd[60].at[t0, c]))
    E = pd.DataFrame(rows).dropna(subset=["f20", "f60"])
    E["시즌"] = E["날"].str[:6]                      # 같은 달 접수 = 같은 보고 시즌 무리
    print(f"보고서 사건 {len(E)}건(시총 200위 · 2017 ~) · 시즌 {E['시즌'].nunique()}", flush=True)
    feats = ["영업이익YoY", "매출YoY", "영업현금YoY", "이익의질", "부채비율변화", "이익수익률", "장부비율", "외국인20", "기관20", "고점비", "수익20", "거래대금증가"]
    R = E.groupby("시즌")[feats].rank(pct=True)
    R = R.fillna(0.5)
    combos = {"가치(이익수익률 + 장부비율)": (["이익수익률", "장부비율"], [1, 1]),
              "실적 변화(영업이익 + 매출 + 영업현금 YoY)": (["영업이익YoY", "매출YoY", "영업현금YoY"], [1, 1, 1]),
              "실적 변화 + 이익의 질": (["영업이익YoY", "매출YoY", "영업현금YoY", "이익의질"], [1, 1, 1, 1]),
              "수급(외국인20 + 기관20)": (["외국인20", "기관20"], [1, 1]),
              "실적 변화 + 수급": (["영업이익YoY", "매출YoY", "영업현금YoY", "외국인20", "기관20"], [1, 1, 1, 1, 1]),
              "실적 변화 + 수급 + 덜 오름(52주 고점비 낮음)": (["영업이익YoY", "매출YoY", "영업현금YoY", "외국인20", "기관20", "고점비"], [1, 1, 1, 1, 1, -1]),
              "실적 변화 + 수급 + 가치": (["영업이익YoY", "매출YoY", "영업현금YoY", "외국인20", "기관20", "이익수익률", "장부비율"], [1, 1, 1, 1, 1, 1, 1])}
    def report(lab, score):
        for h in ("f20", "f60"):
            t = E.assign(s=score)
            ic = t.groupby("시즌").apply(lambda x: x["s"].corr(x[h], method="spearman") if len(x) >= 20 else np.nan).dropna()
            cut = t.groupby("시즌")["s"].rank(pct=True)
            top, bot = t[cut > 0.8][h], t[cut <= 0.2][h]
            ia = t[t["반"] == "앞"].groupby("시즌").apply(lambda x: x["s"].corr(x[h], method="spearman") if len(x) >= 20 else np.nan).dropna()
            ib = t[t["반"] == "뒤"].groupby("시즌").apply(lambda x: x["s"].corr(x[h], method="spearman") if len(x) >= 20 else np.nan).dropna()
            print(f"  {lab:38s} {h[1:]}일 IC {ic.mean():+.3f}(t {ic.mean() / ic.std() * np.sqrt(len(ic)):+.1f}) [앞 {ia.mean():+.3f} / 뒤 {ib.mean():+.3f}]"
                  f" · 위−아래 {(top.mean() - bot.mean()) * 100:+.2f}%p · 위 1/5 {top.mean() * 100:+.2f}%(비용 뒤 {(top.mean() - 0.005) * 100:+.2f} · 나을 {(top > 0).mean():.0%})", flush=True)
    print("[하나씩]")
    for f in feats:
        report(f, R[f])
    print("[묶음 · 같은 무게]")
    for lab, (cols, w) in combos.items():
        report(lab, sum(R[c] * (s if s > 0 else 1) if s > 0 else (1 - R[c]) for c, s in zip(cols, w)))


if __name__ == "__main__":
    main()
