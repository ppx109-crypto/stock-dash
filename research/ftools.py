"""수급 갈래(F) 도우미 — 종목 × 날 표: 투자자별 n일 순매수 ÷ 20일 평균 거래량(힘)과 앞으로 h일 '시장 넘는 수익'.
자료: investor-data(개인 · 외국인 · 기관 · 투신 · 연기금 · 사모, 2017 ~ · 440종목) · program-data(프로그램 순매수량, 261종목)
      · price-data 종가(수정 주가) · volume-data 거래량.
때: t일 장 끝난 뒤 자료로 보고 t+1일 종가에 사서 t+1+h일 종가까지(늦게 사는 쪽으로 잡음).
시장 넘는 수익 = 그 종목 수익 − 같은 날 모든 종목 수익의 평균."""
import glob
import json
import os
from pathlib import Path

import numpy as np

ROOT = Path("/home/user/stock-dash")
CATS = ("개인", "외국인", "기관", "투신", "연기금", "사모")
HS = (5, 20, 60)
MID = "20210101"
CACHE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/ftab.npz")


def _load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def build(n=5):
    """행 = (종목, 날). 열: 각 투자자 n일 힘 · 프로그램 n일 힘(없으면 nan) · 연속일(외국인 · 투신) · 20일 수익 · 앞으로 h일 수익."""
    key = f"{CACHE}.{n}"
    if os.path.exists(key + ".npz"):
        z = np.load(key + ".npz", allow_pickle=True)
        return {k: z[k] for k in z.files}
    days_all = sorted({r[0] for f in glob.glob(str(ROOT / "investor-data/*.json")) for r in (_load(f) or {}).get("rows", [])})
    di = {d: i for i, d in enumerate(days_all)}
    T = len(days_all)
    out = {k: [] for k in ("code", "day") + tuple(f"s_{c}" for c in CATS) + ("s_프로그램", "run_외국인", "run_투신", "r20", "cap")
           + tuple(f"f{h}" for h in HS)}
    for f in sorted(glob.glob(str(ROOT / "investor-data/*.json"))):
        inv = _load(f)
        code = Path(f).stem
        pr = _load(ROOT / f"price-data/{code}.json")
        vo = _load(ROOT / f"volume-data/{code}.json")
        if not inv or not pr or not vo or len(inv["rows"]) < 80:
            continue
        cl = np.full(T, np.nan)
        for d, c in pr["closes"]:
            if d in di:
                cl[di[d]] = c
        vol = np.full(T, np.nan)
        for row in vo["날"]:
            if row[0] in di:
                vol[di[row[0]]] = row[1]
        fl = {c: np.full(T, np.nan) for c in CATS}
        for r in inv["rows"]:
            if r[0] in di:
                for j, c in enumerate(CATS):
                    fl[c][di[r[0]]] = r[1 + j] if r[1 + j] is not None else np.nan
        prog = np.full(T, np.nan)
        pg = _load(ROOT / f"program-data/{code}.json")
        for r in (pg or {}).get("rows", []):
            if r["date"] in di and r.get("순매수량") is not None:
                prog[di[r["date"]]] = r["순매수량"]
        ok = ~np.isnan(cl) & ~np.isnan(vol) & ~np.isnan(fl["외국인"])
        idx = np.where(ok)[0]
        if len(idx) < 80:
            continue
        # 거래일만 남겨 이어 붙임(그 종목이 거래한 날 기준 n일)
        c_, v_ = cl[idx], vol[idx]
        cs = lambda a: np.concatenate([[0], np.nancumsum(a)])
        vavg = (cs(v_)[20:] - cs(v_)[:-20]) / 20
        vavg = np.concatenate([np.full(19, np.nan), vavg])
        L = len(idx)
        sums = {}
        for c in CATS:
            a = fl[c][idx]
            s = cs(a)
            sums[c] = np.concatenate([np.full(n - 1, np.nan), s[n:] - s[:-n]])
        a = prog[idx]
        s = cs(a)
        pn = np.concatenate([np.full(n - 1, np.nan), s[n:] - s[:-n]])
        have_p = np.concatenate([np.full(n - 1, 0), (cs(~np.isnan(a))[n:] - cs(~np.isnan(a))[:-n])])
        pn[have_p < n] = np.nan

        def run(x):
            o = np.zeros(L)
            for i in range(L):
                o[i] = o[i - 1] + 1 if (i and x[i] > 0) else (1 if x[i] > 0 else 0)
            return o
        rf, rt = run(fl["외국인"][idx]), run(fl["투신"][idx])
        r20 = np.concatenate([np.full(20, np.nan), c_[20:] / c_[:-20] - 1])
        fw = {}
        for h in HS:
            x = np.full(L, np.nan)
            x[: L - 1 - h] = c_[1 + h:] / c_[1: L - h] - 1
            fw[h] = x
        cap = c_ * v_  # 거래대금 흉내(크기 무리 나눌 때만)
        good = ~np.isnan(vavg) & (vavg > 0) & ~np.isnan(sums["외국인"]) & ~np.isnan(r20)
        for i in np.where(good)[0]:
            out["code"].append(code)
            out["day"].append(days_all[idx[i]])
            for c in CATS:
                out[f"s_{c}"].append(sums[c][i] / vavg[i])
            out["s_프로그램"].append(pn[i] / vavg[i] if not np.isnan(pn[i]) else np.nan)
            out["run_외국인"].append(rf[i]); out["run_투신"].append(rt[i])
            out["r20"].append(r20[i]); out["cap"].append(cap[i])
            for h in HS:
                out[f"f{h}"].append(fw[h][i])
    tab = {k: np.array(v) for k, v in out.items()}
    # 시장 넘는 수익: 같은 날 평균을 뺌
    days = tab["day"]
    order = np.argsort(days, kind="stable")
    for h in HS:
        x = tab[f"f{h}"]
        ex = np.full(len(x), np.nan)
        ud, start = np.unique(days[order], return_index=True)
        bounds = list(start) + [len(order)]
        for k in range(len(ud)):
            sl = order[bounds[k]: bounds[k + 1]]
            v = x[sl]
            m = np.nanmean(v) if np.any(~np.isnan(v)) else np.nan
            ex[sl] = v - m
        tab[f"x{h}"] = ex
    np.savez(key, **tab)
    return tab


def halves(tab):
    return (("앞(2017 ~ 2020)", tab["day"] < MID), ("뒤(2021 ~)", tab["day"] >= MID))


def pit(tab, top=100):
    """그날 시총 top위 안(nrl.inside · 미래 정보 없음)만 남기고, 시장 넘는 수익을 그 안 평균으로 다시 셈."""
    import sys
    sys.path[:0] = ["/home/user/stock-dash/research", "/home/user/stock-dash"]
    import nrl
    keep = {(r["code"], r["date"]) for r in nrl.inside if (r.get("시총순위") or 999) <= top}
    m = np.fromiter(((c, d) in keep for c, d in zip(tab["code"], tab["day"])), bool, len(tab["day"]))
    sub = {k: v[m] for k, v in tab.items()}
    days = sub["day"]
    order = np.argsort(days, kind="stable")
    ud, start = np.unique(days[order], return_index=True)
    bounds = list(start) + [len(order)]
    for h in HS:
        x = sub[f"f{h}"]
        ex = np.full(len(x), np.nan)
        for k in range(len(ud)):
            sl = order[bounds[k]: bounds[k + 1]]
            v = x[sl]
            ex[sl] = v - (np.nanmean(v) if np.any(~np.isnan(v)) else np.nan)
        sub[f"x{h}"] = ex
    return sub


def show(tab, mask, name, width=34):
    """두 반: 건수 · 시장 넘는 수익 평균(5 · 20 · 60일) · 20일 가운데값 · 20일 이긴 비율."""
    out = [f"  {name:<{width}}"]
    for hn, hm in halves(tab):
        m = mask & hm
        n = int(m.sum())
        if n == 0:
            out.append(f"| {hn[:1]} 없음")
            continue
        v = [np.nanmean(tab[f'x{h}'][m]) * 100 for h in HS]
        med = np.nanmedian(tab["x20"][m]) * 100
        win = np.nanmean(tab["x20"][m] > 0) * 100
        out.append(f"| {hn[:1]} {n:6d}건 5일 {v[0]:+5.2f} 20일 {v[1]:+5.2f} 60일 {v[2]:+5.2f} 가운데 {med:+5.2f} 이김 {win:4.1f}")
    print(" ".join(out), flush=True)
