"""I 49회차 — DART 분기 실적 '실적 물결' · 코스닥 종목만 모은 한투 지표 훑기(i031과 같은 방식 · 결과 scratchpad/agg2.npz).
실적 물결(quarter-data 416종목 · 2016 ~): 보고서 접수일(접수번호 앞 8자리)에 그 보고서의 영업이익 vs 작년 같은 기간 영업이익.
  지표: 앞 60거래일 안에 나온 보고서 중 '영업이익 늘어남' 몫(%) · 늘어난 폭 가운데 값(작년 |값| 대비 · ±200%로 자름) · 흑자 전환 − 적자 전환 수.
  보고서 접수 다음 거래일부터 반영(미래 참조 없음).
코스닥 종목만(kosdaq-data에 있는 종목코드): 공매도 비중 평균 · 대차잔고 20일 변화 · 신용 잔고율 20일 변화 · 체결강도 · 개인 순매수 종목 몫.
견줌: 앞 250일 순위 위 20% − 아래 20%의 앞 5 · 20일 코스피200 · 코스닥150 수익(B 2017 ~ 2020 / C 2021 ~)."""
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

ROOT = Path("/home/user/stock-dash")
D, n = I.DAYS, len(I.DAYS)
IX = {d: i for i, d in enumerate(D)}
SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
num = lambda x: float(str(x).replace(",", "")) if x not in (None, "", "-") else np.nan
AGG = {}

# ---- 실적 물결
ev = []                                  # (반영 날 i, 늘어남?, 폭, 흑전, 적전)
for f in glob.glob(str(ROOT / "quarter-data/*.json")):
    for key, r in (json.load(open(f)).get("rows") or {}).items():
        if not isinstance(r, dict):
            continue
        no = str(r.get("접수번호") or "")
        if len(no) < 8:
            continue
        i = np.searchsorted(D, no[:8], side="right")           # 접수 다음 거래일부터
        if i >= n:
            continue
        a, b = num(r.get("영업이익")), num(r.get("영업이익_작년"))
        if not (np.isfinite(a) and np.isfinite(b)):
            continue
        g = np.clip((a - b) / max(abs(b), 1.0), -2, 2)
        ev.append((i, a > b, g, b <= 0 < a, a <= 0 < b))
up, tot, grow, tp, tl = (np.zeros(n) for _ in range(5))
gl = [[] for _ in range(n)]
for i, u, g, p, l in ev:
    tot[i] += 1
    up[i] += u
    tp[i] += p
    tl[i] += l
    gl[i].append(g)


def rsum(a, w):
    c = np.cumsum(np.insert(a, 0, 0))
    out = np.full(n, np.nan)
    out[w - 1:] = c[w:] - c[:-w]
    return out


T60, U60 = rsum(tot, 60), rsum(up, 60)
AGG["DART 실적 늘어난 회사 몫(60일)"] = np.where(T60 >= 30, U60 / np.maximum(T60, 1) * 100, np.nan)
AGG["DART 실적 늘어난 폭 가운데(60일)"] = np.array([np.median(sum(gl[max(0, i - 59):i + 1], [])) * 100 if sum(len(x) for x in gl[max(0, i - 59):i + 1]) >= 30 else np.nan for i in range(n)])
AGG["DART 흑자전환 − 적자전환(60일)"] = rsum(tp - tl, 60)
print(f"실적 보고서 {len(ev)}건", flush=True)

# ---- 코스닥 종목만
KQ = {Path(f).stem for f in glob.glob(str(ROOT / "kosdaq-data/*.json"))}


def stack(d, name):
    mats = []
    for f in sorted(glob.glob(str(ROOT / d / "*.json"))):
        if Path(f).stem not in KQ:
            continue
        b = json.load(open(f))
        cols = b.get("cols")
        a = np.full(n, np.nan)
        for r in b.get("rows", []):
            dd = r[0] if cols else r.get("date")
            i = IX.get(str(dd))
            if i is not None:
                v = r[cols.index(name)] if cols else r.get(name)
                if v is not None:
                    a[i] = v
        mats.append(a)
    return np.array(mats) if mats else np.full((1, n), np.nan)


sh = stack("short-data", "공매도비중")
print(f"코스닥 종목: 공매도 {len(sh)}", flush=True)
mn = lambda m, k=20: np.where(np.isfinite(m).sum(axis=0) >= k, np.nanmean(m, axis=0), np.nan)
s1 = mn(sh)
AGG["코스닥 공매도 비중 평균"] = np.array([np.nanmean(s1[max(0, i - 4):i + 1]) if np.isfinite(s1[max(0, i - 4):i + 1]).any() else np.nan for i in range(n)])
lo = stack("loan-data", "잔고금액")
ls = np.where(np.isfinite(lo).sum(axis=0) >= 20, np.nansum(lo, axis=0), np.nan)
AGG["코스닥 대차잔고 20일 변화"] = np.concatenate([np.full(20, np.nan), ls[20:] / ls[:-20] - 1])
cr = mn(stack("credit-data", "잔고율"))
AGG["코스닥 신용 잔고율 평균"] = cr
AGG["코스닥 신용 잔고율 20일 변화"] = np.concatenate([np.full(20, np.nan), cr[20:] - cr[:-20]])
bu, se = stack("side-data", "매수체결량"), stack("side-data", "매도체결량")
b5, s5 = rsum(np.nansum(bu, axis=0), 5), rsum(np.nansum(se, axis=0), 5)
with np.errstate(invalid="ignore", divide="ignore"):
    AGG["코스닥 체결강도(5일)"] = np.where(s5 > 0, b5 / s5, np.nan)
iv = stack("investor-data", "개인")
i5 = np.array([rsum(np.nan_to_num(r), 5) for r in iv])
AGG["코스닥 개인 순매수 종목 몫(5일)"] = np.where(np.isfinite(iv).sum(axis=0) >= 20, (i5 > 0).mean(axis=0) * 100, np.nan)
for k in AGG:
    AGG[k] = np.concatenate([[np.nan], AGG[k][:-1]])
np.savez(SP + "agg2.npz", **AGG)


def rank250(a):
    out = np.full(n, np.nan)
    for i in range(250, n):
        h = a[i - 250:i]
        h = h[np.isfinite(h)]
        if len(h) > 150 and np.isfinite(a[i]):
            out[i] = (h < a[i]).mean() * 100
    return out


fwd = {}
for code in ("069500", "229200"):
    p = I.px(code)
    for h in (5, 20):
        f = np.full(n, np.nan)
        f[:-h] = p[h:] / p[:-h] - 1
        fwd[(code, h)] = f
PER = (("B", "20170101", "20210101"), ("C", "20210101", "20991231"))
print("== I 49회차: 실적 물결 · 코스닥 종목 지표 — '위20% − 아래20%' 앞 수익(%) B / C ==", flush=True)
print("   (칸: 코스피200 5일 · 20일 | 코스닥150 5일 · 20일)", flush=True)
for k, a in AGG.items():
    rk = rank250(a)
    parts, signs = [], []
    for code in ("069500", "229200"):
        for h in (5, 20):
            cell = []
            for nm, lo_, hi_ in PER:
                idx = np.array([lo_ <= d < hi_ for d in D])
                f = fwd[(code, h)]
                cell.append((np.nanmean(f[idx & (rk >= 80)]) - np.nanmean(f[idx & (rk <= 20)])) * 100)
            signs.append(np.sign(cell[0]) == np.sign(cell[1]))
            parts.append(f"{cell[0]:+5.1f}/{cell[1]:+5.1f}")
    print(f"  {k:26s} | " + " | ".join(parts) + ("  ★ " + str(sum(signs)) + "/4" if sum(signs) >= 3 else ""), flush=True)
print("끝", flush=True)
