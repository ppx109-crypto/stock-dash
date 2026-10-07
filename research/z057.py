"""2차 연구 §5 — DART 사건 × KIS 시장 반응(H1 ~ H7 · 조건 쌓기 · 갈래별 표) · docs/PREREG-2.md 문턱 그대로.
대상: 쪼개기 고친 그날 시총 200위(t0에) · 상장폐지 종목 없음. 사건 = 접수일 t0(첫 거래일 ≥ 접수일) · 정정 · 자회사 공시 뺌 ·
같은 종목 · 같은 갈래 20거래일 안 겹침 없음.
판 R2(주 · 시각 무관): 창 = t0 · t0+1 · 반응 = t0−1 종가 → t0+1 종가 초과(그날 200위 가운데값 뺌) · 사기 = t0+2 종가.
판 R1(보조 · 1차 바구니 C와 같음): 창 = t0 · 반응 = t0−1 → t0 · 사기 = t0+1 종가.
H7 '거래량 지속'은 사기 = 창 끝 + 6(그 5일을 다 본 다음 날).
뒤 수익 = 사기 날 종가 → +h거래일 종가 초과(그날 200위 가운데값 뺌) − 바탕(아무 종목 · 날 같은 h 초과 평균) · h ∈ 1 · 3 · 5 · 10 · 20 · 40.
보유 h는 학습(2017 ~ 20)에서 '바탕 뺀 평균'이 가장 큰 것 하나 → 검증 · 시험에 그대로. 비용: 사건마다 perf2 EXTREME(계좌 1억 · 5칸).
통계: 평균 · 중앙 · 나을 확률 · 종목 묶음 t · 달 묶음 t(둘 중 작은 것을 씀) · BH(5%) · Bonferroni.
python research/z057.py   (Z_R=R1 이면 보조 판)
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import caps  # noqa: E402
import perf2 as P  # noqa: E402
import z001 as Z  # noqa: E402

caps.ADJ = True
MODE = os.getenv("Z_R", "R2")
HS = (1, 3, 5, 10, 20, 40)
PER = (("학습", "20170101", "20210101"), ("검증", "20210101", "20230101"), ("시험", "20230101", "20991231"))
GOOD = ("자사주취득", "주식소각", "무상증자", "배당", "공급계약", "시설투자", "실적개선")
DART_KINDS = {"합병": "합병", "분할": "분할", "유형자산양도": "자산매각", "타법인주식양도": "자산매각"}


def load_events(codes, qs):
    out = {}
    for c in codes:
        got = []
        p = Path("event-data") / f"{c}.json"
        if p.exists():
            for r in json.loads(p.read_text(encoding="utf-8")).get("rows") or []:
                t = str(r.get("title", ""))
                if "정정" in t or "자회사" in t or "종속회사" in t or not r.get("date"):
                    continue
                k = r.get("kind")
                if k in ("잠정실적", "실적공시"):
                    continue
                got.append((str(r["date"]), k))
        p = Path("dart-events") / f"{c}.json"
        if p.exists():
            rows = json.loads(p.read_text(encoding="utf-8")).get("rows") or {}
            for k, lst in rows.items():
                if k in DART_KINDS:
                    for x in lst or []:
                        no = str(x.get("rcept_no", ""))
                        if no[:8].isdigit():
                            got.append((no[:8], DART_KINDS[k]))
        for d, op, op_ly, *_ in qs.get(c) or []:
            if op is not None and op_ly is not None:
                got.append((d, "실적개선" if op > op_ly else "실적악화"))
        out[c] = sorted(set(got))
    return out


def cl_t(x, g):
    """묶음(g) 강건 t — 평균 / √(Σ_g (Σ(x − 평균))² ) × n."""
    x = np.asarray(x, float)
    if len(x) < 10:
        return np.nan
    e = x - x.mean()
    s = pd.Series(e).groupby(np.asarray(g)).sum()
    se = np.sqrt((s ** 2).sum()) / len(x)
    return x.mean() / se if se > 0 else np.nan


def main():
    C, F, ops, evs, qs, name = Z.load()
    inside, size = Z.universe(C)
    days = list(C.index)
    n = len(days)
    Cv = C.to_numpy()
    r1 = C / C.shift(1) - 1
    med1 = r1.where(inside).median(axis=1).to_numpy()
    vol = F["vol"].reindex(C.index).to_numpy()
    fo, ins, ind = (F[k].reindex(C.index).to_numpy() for k in ("외국인", "기관", "개인"))
    sr = F["공매도비중"].reindex(C.index)
    srv = sr.to_numpy()
    hi252 = C.rolling(252, min_periods=200).max().to_numpy()
    lo252 = C.rolling(252, min_periods=200).min().to_numpy()
    ins_v = inside.to_numpy()
    # 뒤 초과: 사기 날 i → i+h (그날 200위 가운데값 뺌) · 바탕
    fwd, base = {}, {}
    for h in HS:
        f = C.shift(-h) / C - 1
        ex = f.sub(f.where(inside).median(axis=1), axis=0)
        fwd[h] = ex.to_numpy()
        base[h] = {p: float(np.nanmean(ex.where(inside)[(ex.index >= lo) & (ex.index < hi)].to_numpy())) for p, lo, hi in PER}
    E = load_events(list(C.columns), qs)
    col = {c: k for k, c in enumerate(C.columns)}
    rows = []
    w = 1 if MODE == "R1" else 2          # 창 길이
    for c, lst in E.items():
        k = col[c]
        last = {}
        for d, kind in lst:
            if d < "20170101":
                continue
            j = int(np.searchsorted(days, d))
            if j < 21 or j + w + 1 >= n or not ins_v[j, k]:
                continue
            if kind in last and j - last[kind] < 20:
                continue
            last[kind] = j
            te = j + w - 1                      # 창 끝
            p0, pe = Cv[j - 1, k], Cv[te, k]
            if not (np.isfinite(p0) and np.isfinite(pe)):
                continue
            mret = np.nanprod(1 + med1[j:te + 1]) - 1
            react = pe / p0 - 1 - mret
            v20 = np.nanmean(vol[j - 20:j, k])
            vw = np.nanmean(vol[j:te + 1, k])
            v5 = np.nanmean(vol[te + 1:te + 6, k]) if te + 6 < n else np.nan
            fsum, isum, psum = (np.nansum(a[j:te + 1, k]) if np.isfinite(a[j:te + 1, k]).any() else np.nan for a in (fo, ins, ind))
            srw = np.nanmean(srv[j:te + 1, k]) if np.isfinite(srv[j:te + 1, k]).any() else np.nan
            sr20 = np.nanmean(srv[j - 20:j, k]) if np.isfinite(srv[j - 20:j, k]).any() else np.nan
            srmed = np.nanmedian(np.nanmean(srv[j:te + 1][:, ins_v[te]], axis=0)) if ins_v[te].any() else np.nan
            pos = (pe - lo252[te, k]) / (hi252[te, k] - lo252[te, k]) if np.isfinite(hi252[te, k]) and hi252[te, k] > lo252[te, k] else np.nan
            row = dict(코드=c, 갈래=kind, t0=days[j], 반응=react, 급증=vw >= 2 * v20 if np.isfinite(v20) and v20 > 0 else False,
                       지속=v5 >= 1.5 * v20 if np.isfinite(v5) and np.isfinite(v20) and v20 > 0 else False,
                       외기합=(fsum + isum) if np.isfinite(fsum) and np.isfinite(isum) else np.nan, 외=fsum, 기=isum, 개=psum,
                       공매낮음=srw < srmed if np.isfinite(srw) and np.isfinite(srmed) else np.nan,
                       공매감소=srw < sr20 if np.isfinite(srw) and np.isfinite(sr20) else np.nan, 위치=pos)
            for h in HS:
                for tag, ent in (("", te + 1), ("_h7", te + 6)):
                    row[f"f{h}{tag}"] = fwd[h][ent, k] if ent + h < n else np.nan
            rows.append(row)
    D = pd.DataFrame(rows)
    D["달"] = D["t0"].str[:6]
    D["기간"] = np.select([D["t0"] < "20210101", D["t0"] < "20230101"], ["학습", "검증"], "시험")
    D["좋은"] = D["갈래"].isin(GOOD)
    D["내림"] = D["반응"] <= -0.02
    D["오름"] = D["반응"] >= 0.02
    cost = {}
    for r in D.itertuples():
        b, s = P.side_costs(r.코드, r.t0, r.t0, 1e8 / 5, 2.0)
        cost[r.Index] = b + s
    D["비용EX"] = pd.Series(cost)
    print(f"판 {MODE} · 사건 {len(D)}(좋은 {int(D['좋은'].sum())}) · 학습 {int((D['기간'] == '학습').sum())} · 검증 {int((D['기간'] == '검증').sum())} · 시험 {int((D['기간'] == '시험').sum())} · "
          f"EXTREME 비용 가운데 {D['비용EX'].median() * 100:.2f}%", flush=True)
    results = []

    def cell(lab, m, tag=""):
        sub = D[m]
        best, bv = None, -9
        tr = sub[sub["기간"] == "학습"]
        for h in HS:
            x = tr[f"f{h}{tag}"].dropna() - base[h]["학습"]
            if len(x) >= 15 and x.mean() > bv:
                best, bv = h, x.mean()
        if best is None:
            print(f"  {lab:46s} 학습 건수 부족({len(tr)})", flush=True)
            return
        parts = []
        res = {"칸": lab, "h": best}
        for p, lo, hi in PER:
            s = sub[sub["기간"] == p]
            x = (s[f"f{best}{tag}"] - base[best][p]).dropna()
            if len(x) < 5:
                parts.append(f"{p} {len(x)}건")
                continue
            xs = s.loc[x.index]
            t = np.nanmin([abs(cl_t(x, xs["코드"])), abs(cl_t(x, xs["달"]))]) * np.sign(x.mean())
            net = x - xs["비용EX"]
            parts.append(f"{p} {len(x)}건 {x.mean() * 100:+.2f}%p(중앙 {x.median() * 100:+.2f} · 나을 {(x > 0).mean():.0%} · t {t:+.1f}) → 비용 뒤 {net.mean() * 100:+.2f}")
            res.update({f"{p}_n": len(x), f"{p}_m": x.mean(), f"{p}_t": t, f"{p}_net": net.mean()})
        print(f"  {lab:46s} h={best:2d} | " + " | ".join(parts), flush=True)
        results.append(res)

    G, dn = D["좋은"], D["내림"]
    print("\n[갈래별 · 반응별(창 반응) — 서술]", flush=True)
    for kd in sorted(D["갈래"].unique()):
        m = D["갈래"] == kd
        if m.sum() < 60:
            continue
        for rl, rm in (("내림", D["내림"]), ("보통", ~D["내림"] & ~D["오름"]), ("오름", D["오름"])):
            cell(f"{kd} · {rl}", m & rm)
    print("\n[가설]", flush=True)
    cell("H0 좋은 사건 전부", G)
    cell("H1 좋은 사건 · 반응 ≤ −2%", G & dn)
    cell("H1 대조: 좋은 사건 · 반응 > −2%", G & ~dn)
    cell("H2 좋은 · 내림 · 외국인 + 기관 합 > 0", G & dn & (D["외기합"] > 0))
    cell("H2 대조: 좋은 · 내림 · 외국인 + 기관 합 ≤ 0", G & dn & (D["외기합"] <= 0))
    cell("H3 좋은 · 내림 · 거래량 급증 · 공매도 낮음", G & dn & D["급증"] & (D["공매낮음"] == True))  # noqa: E712
    cell("H3 대조: 좋은 · 내림 · 급증 · 공매도 높음", G & dn & D["급증"] & (D["공매낮음"] == False))  # noqa: E712
    cell("H4 좋은 · 내림 · 52주 위치 중간(0.3 ~ 0.7)", G & dn & D["위치"].between(0.3, 0.7))
    cell("H4 대조: 좋은 · 내림 · 52주 저점 부근(< 0.2)", G & dn & (D["위치"] < 0.2))
    cell("H4 대조: 좋은 · 내림 · 52주 고점 부근(> 0.8)", G & dn & (D["위치"] > 0.8))
    h5 = (D["외"] > 0) & (D["기"] > 0) & (D["개"] < 0)
    cell("H5 좋은 · 외국인 + · 기관 + · 개인 −", G & h5)
    cell("H5 좋은 · 내림 · 외국인 + · 기관 + · 개인 −", G & dn & h5)
    cell("H6 좋은 · 내림 · 공매도 비중 감소", G & dn & (D["공매감소"] == True))  # noqa: E712
    cell("H6 대조: 좋은 · 내림 · 공매도 비중 늘어남", G & dn & (D["공매감소"] == False))  # noqa: E712
    cell("H7 좋은 · 거래량 급증 · 그 뒤 5일 지속(t+6 사기)", G & D["급증"] & D["지속"], "_h7")
    cell("H7 대조: 좋은 · 급증 · 일회(t+6 사기)", G & D["급증"] & ~D["지속"], "_h7")
    print("\n[조건 쌓기]", flush=True)
    m = G.copy()
    for lab, add in (("좋은 사건", None), ("+ 반응 ≤ −2%", dn), ("+ 거래량 급증", D["급증"]), ("+ 외국인 + 기관 > 0", D["외기합"] > 0),
                     ("+ 공매도 낮음", D["공매낮음"] == True), ("+ 52주 위치 중간", D["위치"].between(0.3, 0.7))):  # noqa: E712
        if add is not None:
            m = m & add
        cell(f"쌓기 {lab}", m)
    R = pd.DataFrame(results)
    # 다중검정: 시험 기간 t → 양쪽 p (정규 어림)
    from math import erf, sqrt
    R = R[R["시험_t"].notna()] if "시험_t" in R else R
    p = R["시험_t"].abs().apply(lambda t: 2 * (1 - 0.5 * (1 + erf(t / sqrt(2)))))
    M = len(p)
    order = p.sort_values()
    bh = pd.Series(False, index=p.index)
    for rank, (ix, pv) in enumerate(order.items(), 1):
        if pv <= 0.05 * rank / M:
            bh[order.index[:rank]] = True
    R["p"], R["BH"], R["Bonf"] = p, bh, p <= 0.05 / M
    ok = R[(np.sign(R["학습_m"]) == np.sign(R["검증_m"])) & (R["시험_net"] > 0) & (R["시험_t"] >= 2) & (R["시험_n"] >= 30)]
    print(f"\n[다중검정] 시험 기간에 잰 칸 M = {M} · BH 통과 {int(R['BH'].sum())} · Bonferroni 통과 {int(R['Bonf'].sum())}", flush=True)
    print("[채택 잣대 ①~④ 통과 칸(학습 · 검증 같은 부호 · 시험 EXTREME 비용 뒤 > 0 · 시험 t ≥ 2 · 시험 30건 이상)]", flush=True)
    for r in ok.itertuples():
        print(f"  {r.칸} · h {r.h} · 시험 {r.시험_n}건 {r.시험_m * 100:+.2f}%p · t {r.시험_t:+.1f} · 비용 뒤 {r.시험_net * 100:+.2f} · p {r.p:.4f} · BH {r.BH} · Bonf {r.Bonf}", flush=True)
    out = os.getenv("Z_OUT")
    if out:
        D.to_pickle(out)


if __name__ == "__main__":
    main()
