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
        ("        vb *= base[d][0] / base[p][0]\n", "        _a = ATT.setdefault(d, {'바탕': 0.0, '레버리지': 0.0, '인버스': 0.0, '비용': 0.0, '정리 비용': 0.0, 'A0': vb + ve + cash})\n        _a['바탕'] += vb * (base[d][0] / base[p][0] - 1)\n        vb *= base[d][0] / base[p][0]\n"),
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
    # 바탕 봇별 날 손익(z100g attr · 원) → 바탕 NAV 대비 몫 → 계좌의 '바탕' 몫에 비례해 나눔
    A = {r["날"]: r for r in csv.DictReader(open(attr_csv))}
    B = {r["날"]: r for r in csv.DictReader(open(base_csv))}
    ds = sorted(navs)
    bots = ("1d", "basket", "engine", "inverse")
    mkt_days = sorted(etf)
    mret = {}
    for i in range(1, len(mkt_days)):
        mret[mkt_days[i]] = etf[mkt_days[i]] / etf[mkt_days[i - 1]] - 1
    # 봇별 계좌 기여(원) = 덧붙임 판의 '바탕' 손익 × (봇 손익 ÷ 바탕 전체 손익) — 바탕 손익 0인 날은 0
    contrib = {b: [] for b in bots}
    rows = []
    for d in ds[1:]:
        a = att[d]
        z = A.get(d)
        tot = sum(float(z[b]) for b in bots) + float(z.get("15m") or 0) + float(z.get("park") or 0) if z else 0.0
        part = {b: (a["바탕"] * float(z[b]) / tot if z and tot else 0.0) for b in bots}
        rows.append((d, a, part))
    # 베타: 봇 기여(계좌 시작 NAV 대비)와 069500 날 수익
    rr = {b: [p[b] / a["A0"] for _, a, p in rows] for b in bots}
    mm = [mret.get(d, np.nan) for d, _, _ in rows]
    beta = {b: betas(rr[b], mm) for b in bots}
    mon = {}
    for i, (d, a, p) in enumerate(rows):
        x = mon.setdefault(d[:6], {"A0": a["A0"], **{f"{b} 시장": 0.0 for b in bots}, **{f"{b} 잔차": 0.0 for b in bots},
                                  "레버리지": 0.0, "인버스 ETF": 0.0, "덧붙임 비용": 0.0, "바탕비용": 0.0})
        for b in bots:
            bt = beta[b][i]
            mk = (bt * mm[i] * a["A0"]) if (bt is not None and not np.isnan(mm[i])) else 0.0
            x[f"{b} 시장"] += mk
            x[f"{b} 잔차"] += p[b] - mk
        x["레버리지"] += a["레버리지"]
        x["인버스 ETF"] += a["인버스"]
        x["덧붙임 비용"] += a["비용"] + a["정리 비용"]
        pd_ = ds[ds.index(d) - 1]
        if d in B and pd_ in B:                   # 바탕 비용은 바탕 NAV 대비(계좌 몫으로 바꾸지 않은 참고 값 · % 단위로 따로)
            x["바탕비용"] -= (float(B[d]["비용누계"]) - float(B[pd_]["비용누계"])) / float(B[pd_]["NAV"]) * 100
    full = M.mstats(navs)["달"]
    out = {}
    for m, x in mon.items():
        if not ("201703" <= m <= "202608"):
            continue
        out[m] = {"달 수익 %": round(full[m] * 100, 3), **{k: round(v / x["A0"] * 100, 3) for k, v in x.items() if k not in ("A0", "바탕비용")},
                  "바탕 비용(참고 · 바탕 NAV 대비 %)": round(x["바탕비용"], 3)}
    loss = [m for m in out if out[m]["달 수익 %"] < 0]
    S = lambda ms, k: round(sum(out[m][k] for m in ms), 2)  # noqa: E731
    summ = {"손실 달": len(loss)}
    for b in bots:
        summ[f"{b}: 손실 달 합 시장 · 잔차(%p)"] = [S(loss, f"{b} 시장"), S(loss, f"{b} 잔차")]
        summ[f"{b}: 전체 합 시장 · 잔차(%p)"] = [S(out, f"{b} 시장"), S(out, f"{b} 잔차")]
    summ["덧붙임: 손실 달 합 레버리지 · 인버스 · 비용"] = [S(loss, "레버리지"), S(loss, "인버스 ETF"), S(loss, "덧붙임 비용")]
    worst1d = [m for m in loss if out[m]["1d 시장"] + out[m]["1d 잔차"] == min(out[m][f"{b} 시장"] + out[m][f"{b} 잔차"] for b in bots)]
    summ["1일봉이 바탕 봇 중 가장 크게 잃은 손실 달"] = len(worst1d)
    summ["그 달들 1일봉 손실의 시장 몫 · 잔차 합(%p)"] = [S(worst1d, "1d 시장"), S(worst1d, "1d 잔차")]
    base_neg = [m for m in loss if sum(out[m][f"{b} 시장"] + out[m][f"{b} 잔차"] for b in bots) < 0]
    ov_neg = [m for m in loss if out[m]["레버리지"] + out[m]["인버스 ETF"] + out[m]["덧붙임 비용"] < 0]
    both = sorted(set(base_neg) & set(ov_neg))
    comp = lambda m: {"바탕 시장": sum(out[m][f"{b} 시장"] for b in bots), "바탕 잔차": sum(out[m][f"{b} 잔차"] for b in bots),  # noqa: E731
                      "레버리지": out[m]["레버리지"], "인버스 ETF": out[m]["인버스 ETF"]}
    summ["바탕 · 덧붙임 둘 다 − 인 달"] = len(both)
    summ["그 달들에서 가장 큰 음수 원인(달 수)"] = {}
    for m in both:
        c = comp(m)
        k = min(c, key=c.get)
        summ["그 달들에서 가장 큰 음수 원인(달 수)"][k] = summ["그 달들에서 가장 큰 음수 원인(달 수)"].get(k, 0) + 1
    summ["손실 달 전체에서 가장 큰 음수 원인(달 수)"] = {}
    for m in loss:
        c = comp(m)
        k = min(c, key=c.get)
        summ["손실 달 전체에서 가장 큰 음수 원인(달 수)"][k] = summ["손실 달 전체에서 가장 큰 음수 원인(달 수)"].get(k, 0) + 1
    res = {"요약": summ, "손실 달": {m: out[m] for m in sorted(loss)}, "모든 달": out,
           "베타 평균(있는 날)": {b: round(float(np.mean([x for x in beta[b] if x is not None])), 3) for b in bots},
           "범위": "이미 본 연속 장부 계좌의 귀속(새 규칙 손익 없음) · 시장 = 069500 · 업종 베타는 자료 부족으로 뺌 · 봇 몫은 덧붙임 판 '바탕' 손익을 z100g 봇별 손익 비율로 나눔 · 달 합은 달 초 NAV 기준 단순 합"}
    json.dump(res, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "test":
        test()
    else:
        run(*sys.argv[2:5])
