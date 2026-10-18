"""MPOS-0028 0단계 원인 분해(STAGE0.md · 새 규칙 손익 없음).
python3 stage0.py test                     → 베타 도구 시험(합성 · 돌연변이)
python3 stage0.py run 바탕csv z100g_attr.csv 출력.json  → 손실 달 분해
덧붙임 분해는 research/attr_mix54/attr.py와 같은 방식(regime_dev.account 원문에 더하기 줄만 끼움 · 끝 NAV = 원 함수 assert)."""
import inspect
import json
import sys
from pathlib import Path

import numpy as np

SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
WIN, MIN_N = 120, 60


def betas(r, m, lag=1):
    """r · m: 같은 길이 날 수열. 베타[t] = (t−WIN ~ t−1) 최소제곱 기울기(lag=1 · 당일 제외). 앞 날 MIN_N 미만이면 None.
    lag=0은 돌연변이(당일 포함 창) — 시험에서만 씀."""
    out = []
    for t in range(len(r)):
        hi = t + 1 - lag
        lo = max(0, hi - WIN)
        x, y = np.array(m[lo:hi], float), np.array(r[lo:hi], float)
        ok = ~(np.isnan(x) | np.isnan(y))
        x, y = x[ok], y[ok]
        if len(x) < MIN_N or np.var(x) == 0:
            out.append(None)
            continue
        out.append(float(np.cov(x, y, bias=True)[0, 1] / np.var(x)))
    return out


def test():
    rng = np.random.default_rng(20261019)
    m = list(rng.normal(0, 0.01, 400))
    r = [1.5 * x + rng.normal(0, 0.002) for x in m]
    b = betas(r, m)
    ok1 = abs(np.mean([x for x in b[200:] if x is not None]) - 1.5) < 0.05
    m2 = m[:300] + [x * 5 + 0.03 for x in m[300:]]          # 300번째 날 뒤 시장 수익을 바꿈
    r2 = r[:300] + [1.5 * x for x in m2[300:]]
    b2 = betas(r2, m2)
    ok2 = b[:301] == b2[:301]                                 # t ≤ 300의 베타는 t−1까지 자료만 → 같아야 함
    b0, b02 = betas(r, m, lag=0), betas(r2, m2, lag=0)
    mut = b0[:301] != b02[:301]                               # 돌연변이(당일 포함)는 t = 300에서 달라져야 함
    res = {"합성 베타 ≈ 1.5": bool(ok1), "미래 날 바꿔도 과거 베타 같음": bool(ok2), "돌연변이(당일 포함 창) 잡힘": bool(mut), "앞 60일 미만 None": bool(b[59] is None and b[60] is not None)}
    res["통과"] = all(res.values())
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0 if res["통과"] else 3)


def run(base_csv, attr_csv, out_path):
    import csv
    sys.path.insert(0, str(SP / "r8/research-exchange/claude-to-gpt/MPOS-0012"))
    sys.argv = ["x"]
    import mpos12 as M
    Dv = M.Dv
    ref = M.account(base_csv)                    # 원 함수(자료도 여기서 읽힘)
    src = inspect.getsource(Dv.account)
    rep = [
        ("def account(cfg, lo=LO, hi=HI):", "def account_attr(cfg, lo=LO, hi=HI):\n    ATT = {}"),
        ("        vb *= base[d][0] / base[p][0]\n", "        _a = ATT.setdefault(d, {'바탕': 0.0, '레버리지': 0.0, '인버스': 0.0, '비용': 0.0, '정리 비용': 0.0, 'A0': vb + ve + cash, 'VB0': vb})\n        _a['바탕'] += vb * (base[d][0] / base[p][0] - 1)\n        vb *= base[d][0] / base[p][0]\n"),
        ("            ve *= etf[code][d] / etf[code][p]\n", "            _a['레버리지' if code == '122630' else '인버스'] += ve * (etf[code][d] / etf[code][p] - 1)\n            ve *= etf[code][d] / etf[code][p]\n"),
        ("            A -= cost\n", "            A -= cost\n            _a['비용'] -= cost\n"),
        ("            cash += cut * (1 - COST_ETF)\n", "            cash += cut * (1 - COST_ETF)\n            _a['정리 비용'] -= cut * COST_ETF\n"),
        ("            cash += x * (1 - COST_BASE_DOWN)\n", "            cash += x * (1 - COST_BASE_DOWN)\n            _a['정리 비용'] -= x * COST_BASE_DOWN\n"),
        ("    return navs, nst", "    return navs, nst, ATT"),
    ]
    for a, b in rep:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    exec(compile(src, "account_attr", "exec"), Dv.__dict__)
    Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(base_csv), None, None
    navs, nst, att = Dv.account_attr(dict(M.CFG))
    assert navs == ref, "덧붙임 분해 판의 NAV가 원 함수와 다름"
    etf = Dv.data()[1]["069500"]
    # 판 2(GPT #459 16:21:57Z): 봇 몫은 손익 비율이 아니라 자본 배율(그날 시작 계좌 안 바탕 VB0 ÷ 전날 바탕 NAV)로 연결
    rowsA = list(csv.DictReader(open(attr_csv)))
    A = {r["날"]: r for r in rowsA}
    assert len(A) == len(rowsA), "z100g 봇별 손익에 중복 날"
    B = {r["날"]: r for r in csv.DictReader(open(base_csv))}
    ds = sorted(navs)
    bots = ("1d", "basket", "engine", "inverse")
    mkt_days = sorted(etf)
    mret = {mkt_days[i]: etf[mkt_days[i]] / etf[mkt_days[i - 1]] - 1 for i in range(1, len(mkt_days))}
    rows, other_abs, zero_tot = [], [], 0
    for j, d in enumerate(ds[1:], 1):
        a, pd_ = att[d], ds[j - 1]
        if d not in A or d not in B or pd_ not in B:
            raise SystemExit(f"날 누락: {d}(봇별 손익 · 바탕 csv에 없음) — 0으로 채우지 않음")
        k = a["VB0"] / float(B[pd_]["NAV"])
        part = {b: k * float(A[d][b]) for b in bots}
        other = a["바탕"] - sum(part.values())         # 15m · park · 바탕 csv 원 단위 반올림
        other_abs.append(abs(other))
        zero_tot += abs(sum(float(A[d][b]) for b in bots)) < 1e-9 and any(abs(float(A[d][b])) > 0 for b in bots)
        rows.append((d, a, part, other))
    rr = {b: [p[b] / a["A0"] for _, a, p, _ in rows] for b in bots}
    mm = [mret.get(d, float("nan")) for d, _, _, _ in rows]
    beta = {b: betas(rr[b], mm) for b in bots}
    noest = {b: {"날": 0, "시장 자료 없음": 0, "베타 없음(앞 60일 미만 · 분산 0)": 0} for b in bots}
    mon = {}
    for i, (d, a, p, other) in enumerate(rows):
        x = mon.setdefault(d[:6], {"A0": a["A0"], **{f"{b} 설명": 0.0 for b in bots}, **{f"{b} 미설명": 0.0 for b in bots},
                                  **{f"{b} 추정불가": 0.0 for b in bots}, "바탕 기타": 0.0, "레버리지": 0.0, "인버스 ETF": 0.0, "덧붙임 비용": 0.0})
        for b in bots:
            bt, mk = beta[b][i], mm[i]
            if bt is None or not np.isfinite(mk):
                x[f"{b} 추정불가"] += p[b]
                if p[b] != 0:
                    noest[b]["날"] += 1
                    noest[b]["시장 자료 없음" if not np.isfinite(mk) else "베타 없음(앞 60일 미만 · 분산 0)"] += 1
                continue
            x[f"{b} 설명"] += bt * mk * a["A0"]
            x[f"{b} 미설명"] += p[b] - bt * mk * a["A0"]
        x["바탕 기타"] += other
        x["레버리지"] += a["레버리지"]
        x["인버스 ETF"] += a["인버스"]
        x["덧붙임 비용"] += a["비용"] + a["정리 비용"]
    full = M.mstats(navs)["달"]
    raw = {}
    for m, x in mon.items():
        if "201703" <= m <= "202608":
            raw[m] = {"달 수익 %": full[m] * 100, **{kk: v / x["A0"] * 100 for kk, v in x.items() if kk != "A0"}}
    gap = max(abs(v["달 수익 %"] - sum(w for kk, w in v.items() if kk != "달 수익 %")) for v in raw.values())
    loss = [m for m in raw if raw[m]["달 수익 %"] < 0]                         # 원정밀도로 분류(표시만 반올림)
    S = lambda ms, kk: sum(raw[m][kk] for m in ms)  # noqa: E731
    R2 = lambda v: round(v, 2)  # noqa: E731
    summ = {"손실 달": len(loss), "달 부분 합 대 달 수익 최대 차이(%p · 원정밀도 · 단순 합 복리 차이 포함)": gap,
            "바탕 기타(15m · park · 반올림) 날 최대 |원|": max(other_abs), "봇 손익 합 0인데 봇별은 0 아닌 날(판 1이 0으로 지운 날)": zero_tot,
            "추정 불가 날(봇별 · 손익 0 아닌 날만)": noest}
    for b in bots:
        summ[f"{b}: 손실 달 합 설명 · 미설명 · 추정불가(%p)"] = [R2(S(loss, f"{b} 설명")), R2(S(loss, f"{b} 미설명")), R2(S(loss, f"{b} 추정불가"))]
        summ[f"{b}: 114달 합 설명 · 미설명 · 추정불가(%p)"] = [R2(S(raw, f"{b} 설명")), R2(S(raw, f"{b} 미설명")), R2(S(raw, f"{b} 추정불가"))]
    summ["덧붙임: 손실 달 합 레버리지 · 인버스 · 비용"] = [R2(S(loss, "레버리지")), R2(S(loss, "인버스 ETF")), R2(S(loss, "덧붙임 비용"))]
    tb = lambda m, b: raw[m][f"{b} 설명"] + raw[m][f"{b} 미설명"] + raw[m][f"{b} 추정불가"]  # noqa: E731
    worst1d = [m for m in loss if min(bots, key=lambda b: (tb(m, b), bots.index(b))) == "1d"]
    summ["1일봉이 바탕 봇 중 가장 크게 잃은 손실 달"] = len(worst1d)
    summ["그 달들 1일봉 손실 설명 · 미설명 · 추정불가(%p)"] = [R2(S(worst1d, "1d 설명")), R2(S(worst1d, "1d 미설명")), R2(S(worst1d, "1d 추정불가"))]
    ORDER4 = ("바탕 설명", "바탕 미설명", "레버리지", "인버스 ETF")          # 판 1과 같은 4갈래(동률이면 이 순서의 앞)
    ORDER7 = ORDER4 + ("바탕 추정불가", "바탕 기타", "덧붙임 비용")

    def comp(m):
        return {"바탕 설명": sum(raw[m][f"{b} 설명"] for b in bots), "바탕 미설명": sum(raw[m][f"{b} 미설명"] for b in bots),
                "레버리지": raw[m]["레버리지"], "인버스 ETF": raw[m]["인버스 ETF"], "바탕 추정불가": sum(raw[m][f"{b} 추정불가"] for b in bots),
                "바탕 기타": raw[m]["바탕 기타"], "덧붙임 비용": raw[m]["덧붙임 비용"]}

    def tally(ms, order):
        out_ = {}
        for m in ms:
            c = comp(m)
            kk = min(order, key=lambda q: (c[q], order.index(q)))
            out_[kk] = out_.get(kk, 0) + 1
        return out_
    summ["손실 달: 4갈래 중 최대 음수 기여(달 수 · 판 1 정의)"] = tally(loss, ORDER4)
    summ["손실 달: 7갈래 중 최대 음수 기여(달 수 · 추정불가 · 기타 · 비용 포함)"] = tally(loss, ORDER7)
    base_neg = [m for m in loss if sum(tb(m, b) for b in bots) + raw[m]["바탕 기타"] < 0]
    ov_neg = [m for m in loss if raw[m]["레버리지"] + raw[m]["인버스 ETF"] + raw[m]["덧붙임 비용"] < 0]
    both = sorted(set(base_neg) & set(ov_neg))
    summ["바탕 · 덧붙임 둘 다 − 인 달"] = len(both)
    summ["그 달들: 4갈래 중 최대 음수 기여"] = tally(both, ORDER4)
    out = {m: {kk: round(v, 3) for kk, v in raw[m].items()} for m in raw}
    res = {"요약": summ, "손실 달": {m: out[m] for m in sorted(loss)}, "모든 달": out,
           "베타 평균(있는 날)": {b: round(float(np.mean([x for x in beta[b] if x is not None])), 3) for b in bots},
           "범위": "이미 본 연속 장부 계좌의 귀속(새 규칙 손익 없음) · '설명분' = 앞 120일 계좌 기여 베타 × 그날 069500 수익(사후 귀속 · 진입 신호 아님) · '미설명분'은 종목 고유 알파가 아니라 069500 하나로 설명 안 된 나머지(코스닥 · 업종 · 현금 · 노출 변화 · 추정 오차 포함) · 업종 베타 없음 · 봇 몫 = VB0 ÷ 전날 바탕 NAV × 봇 손익 · '최대 음수 기여'는 인과 판정 아님"}
    json.dump(res, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "test":
        test()
    else:
        run(*sys.argv[2:5])
