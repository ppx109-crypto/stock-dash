"""I 46회차 — DART · 한투 종목 자료를 시장 전체 지표로 합쳐 '앞으로 5 · 20일 지수'를 미리 알려 주나 훑기(사용자 2026-10-03 "다트 · 한투 자료로 더 깊게").
지표(그날까지 알려진 것만 · 날짜판 = 069500 거래일):
  DART(event-data 505종목 · 2015 ~): 20거래일 공시 수 — 유상증자 · 자사주취득 · 자사주처분 · 전환사채 · 최대주주변경 · 공급계약 · 무상증자 · 감자 · 관리종목
  한투(2017 ~): 공매도 비중 평균(5일) · 대차잔고 금액 합 20일 변화 · 신용 잔고율 평균 20일 변화 · 체결강도(매수 / 매도 체결량 합 · 5일)
               · 프로그램 순매수 종목 몫(5일 합 > 0) · 외국인 순매수 종목 몫(5일) · 개인 순매수 종목 몫(5일)
               · 증권사 목표가 올림 − 내림(같은 증권사 · 같은 종목 앞 목표가와 견줌 · 20일 합)
각 지표를 '앞 250일 안 순위(0 ~ 100)'로 바꿈(미래 참조 없음). 순위 아래 20% · 위 20%일 때 코스피200(069500) · 코스닥150(229200) 앞 5 · 20일 수익 평균.
기간 B(2017 ~ 2020) · C(2021 ~ 2026)에서 같은 방향이면 '쓸 만함'. 결과 지표는 scratchpad/agg.npz에 남김."""
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


def files(d):
    return [f for f in sorted(glob.glob(str(ROOT / d / "*.json"))) if not Path(f).name.startswith("_")]


def roll_sum(a, w):
    c = np.cumsum(np.insert(np.nan_to_num(a), 0, 0))
    out = np.full(n, np.nan)
    out[w - 1:] = c[w:] - c[:-w]
    return out


AGG = {}
# ---- DART 공시 물결
kinds = ["유상증자", "자사주취득", "자사주처분", "전환사채", "최대주주변경", "공급계약", "무상증자", "감자", "관리종목"]
cnt = {k: np.zeros(n) for k in kinds}
for f in files("event-data"):
    for r in json.load(open(f)).get("rows", []):
        k = r.get("kind")
        if k in cnt:
            i = np.searchsorted(D, r["date"])        # 장 끝난 뒤 공시면 다음 거래일로 미는 게 맞지만 날짜만 있어 그날에 넣고, 신호는 다음 날부터 씀(아래 shift)
            if i < n:
                cnt[k][i] += 1
for k in kinds:
    AGG[f"DART {k} 20일 수"] = roll_sum(cnt[k], 20)

# ---- 한투 종목 자료
def stack(d, getter, start="20170101"):
    mats = []
    for f in files(d):
        b = json.load(open(f))
        cols = b.get("cols")
        a = np.full(n, np.nan)
        for r in b.get("rows", []):
            dd = r[0] if cols else r.get("date")
            i = IX.get(str(dd))
            if i is not None:
                v = getter(r, cols)
                if v is not None:
                    a[i] = v
        mats.append(a)
    return np.array(mats)


g = lambda name: (lambda r, cols: (r[cols.index(name)] if cols else r.get(name)))
short = stack("short-data", g("공매도비중"))
AGG["한투 공매도 비중 평균(5일)"] = np.array([np.nanmean(short[:, max(0, i - 4):i + 1]) if np.isfinite(short[:, max(0, i - 4):i + 1]).any() else np.nan for i in range(n)])
loan = stack("loan-data", g("잔고금액"))
lsum = np.nansum(loan, axis=0)
lsum[np.isfinite(loan).sum(axis=0) < 100] = np.nan
AGG["한투 대차잔고 20일 변화"] = np.concatenate([np.full(20, np.nan), lsum[20:] / lsum[:-20] - 1])
cred = stack("credit-data", g("잔고율"))
cm = np.array([np.nanmean(cred[:, i]) if np.isfinite(cred[:, i]).sum() > 100 else np.nan for i in range(n)])
AGG["한투 신용 잔고율 평균"] = cm
AGG["한투 신용 잔고율 20일 변화"] = np.concatenate([np.full(20, np.nan), cm[20:] - cm[:-20]])
buy, sell = stack("side-data", g("매수체결량")), stack("side-data", g("매도체결량"))
bs, ss = roll_sum(np.nansum(buy, axis=0), 5), roll_sum(np.nansum(sell, axis=0), 5)
AGG["한투 체결강도(5일)"] = np.where(ss > 0, bs / ss, np.nan)
prog = stack("program-data", g("순매수대금"))
ok = np.isfinite(prog).sum(axis=0) > 100
p5 = np.array([roll_sum(row, 5) for row in prog])
AGG["한투 프로그램 순매수 종목 몫(5일)"] = np.where(ok, np.nanmean(p5 > 0, axis=0) * 100, np.nan)
inv = {c: stack("investor-data", g(c)) for c in ("외국인", "개인")}
for c, m in inv.items():
    m5 = np.array([roll_sum(row, 5) for row in m])
    AGG[f"한투 {c} 순매수 종목 몫(5일)"] = np.where(np.isfinite(m).sum(axis=0) > 100, np.nanmean(m5 > 0, axis=0) * 100, np.nan)
up, dn = np.zeros(n), np.zeros(n)
for f in files("opinion-data"):
    last = {}
    for r in sorted(json.load(open(f)).get("rows", []), key=lambda r: r["date"]):
        m, t = r.get("member"), r.get("target")
        if not t:
            continue
        if m in last and last[m] > 0:
            i = np.searchsorted(D, r["date"])
            if i < n:
                if t > last[m] * 1.001:
                    up[i] += 1
                elif t < last[m] * 0.999:
                    dn[i] += 1
        last[m] = t
AGG["한투 목표가 올림 − 내림(20일)"] = roll_sum(up - dn, 20)
AGG["한투 목표가 올림 몫(20일)"] = np.where(roll_sum(up + dn, 20) > 20, roll_sum(up, 20) / np.maximum(roll_sum(up + dn, 20), 1) * 100, np.nan)

# 하루 밀기(그날 장 끝 뒤 공시 · 자료를 다음 날 판단에 씀)
for k in AGG:
    AGG[k] = np.concatenate([[np.nan], AGG[k][:-1]])
np.savez(SP + "agg.npz", **{k: v for k, v in AGG.items()})


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
print("== I 46회차: DART · 한투 시장 지표 훑기 — 순위 아래 20% / 위 20%일 때 앞 수익(%) · 차이 ==", flush=True)
print("   (칸: 코스피200 5일 · 20일 | 코스닥150 5일 · 20일 — 각 '위20% − 아래20%' · B / C)", flush=True)
for k, a in AGG.items():
    rk = rank250(a)
    parts, signs = [], []
    for code in ("069500", "229200"):
        for h in (5, 20):
            cell = []
            for nm, lo, hi in PER:
                idx = np.array([lo <= d < hi for d in D])
                f = fwd[(code, h)]
                lo_m = np.nanmean(f[idx & (rk <= 20)]) * 100
                hi_m = np.nanmean(f[idx & (rk >= 80)]) * 100
                cell.append(hi_m - lo_m)
            signs.append(np.sign(cell[0]) == np.sign(cell[1]))
            parts.append(f"{cell[0]:+5.1f}/{cell[1]:+5.1f}")
    flag = "★ 두 기간 같은 방향 " + str(sum(signs)) + "/4" if sum(signs) >= 3 else ""
    print(f"  {k:28s} | " + " | ".join(parts) + f"  {flag}", flush=True)
print("끝", flush=True)
