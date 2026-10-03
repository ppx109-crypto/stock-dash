"""시장 분위기 점수(I47 · I48) — DART · 한투 종목 자료로 그날까지 알려진 값만 써서 날마다 계산(연구 · 계산기용 · 주문 없음).
점수 = 앞 250거래일 안 순위의 평균: DART 전환사채 20일 공시 수 · DART 공급계약 20일 공시 수 · 한투 목표가 올림 몫(20일)
       · (100 − 한투 대차잔고 금액 합 20일 변화 순위). 공시 · 자료는 다음 거래일부터 반영. 넷 중 셋 이상 있어야 값."""
import glob
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _files(d):
    return [f for f in sorted(glob.glob(str(ROOT / d / "*.json"))) if not Path(f).name.startswith("_")]


def _rsum(a, w):
    c = np.cumsum(np.insert(np.nan_to_num(a), 0, 0))
    out = np.full(len(a), np.nan)
    out[w - 1:] = c[w:] - c[:-w]
    return out


def rank250(a):
    n = len(a)
    out = np.full(n, np.nan)
    for i in range(250, n):
        h = a[i - 250:i]
        h = h[np.isfinite(h)]
        if len(h) > 150 and np.isfinite(a[i]):
            out[i] = (h < a[i]).mean() * 100
    return out


def build(days):
    """days(오래된 → 오늘 거래일 'YYYYMMDD' 목록) → (점수 배열, 낱개 순위 dict)."""
    n = len(days)
    ix = {d: i for i, d in enumerate(days)}
    cnt = {"전환사채": np.zeros(n), "공급계약": np.zeros(n)}
    for f in _files("event-data"):
        for r in json.load(open(f, encoding="utf-8")).get("rows", []):
            if r.get("kind") in cnt:
                i = np.searchsorted(days, r["date"])
                if i < n:
                    cnt[r["kind"]][i] += 1
    up, dn = np.zeros(n), np.zeros(n)
    for f in _files("opinion-data"):
        last = {}
        for r in sorted(json.load(open(f, encoding="utf-8")).get("rows", []), key=lambda r: r["date"]):
            m, t = r.get("member"), r.get("target")
            if not t:
                continue
            if m in last and last[m] > 0:
                i = np.searchsorted(days, r["date"])
                if i < n:
                    up[i] += t > last[m] * 1.001
                    dn[i] += t < last[m] * 0.999
            last[m] = t
    loan = []
    for f in _files("loan-data"):
        a = np.full(n, np.nan)
        for r in json.load(open(f, encoding="utf-8")).get("rows", []):
            i = ix.get(str(r.get("date")))
            if i is not None and r.get("잔고금액") is not None:
                a[i] = r["잔고금액"]
        loan.append(a)
    loan = np.array(loan) if loan else np.full((1, n), np.nan)
    ls = np.where(np.isfinite(loan).sum(axis=0) >= 100, np.nansum(loan, axis=0), np.nan)
    tot = _rsum(up + dn, 20)
    raw = {"전환사채": _rsum(cnt["전환사채"], 20), "공급계약": _rsum(cnt["공급계약"], 20),
           "목표가": np.where(tot > 20, _rsum(up, 20) / np.maximum(tot, 1) * 100, np.nan),
           "대차": np.concatenate([np.full(20, np.nan), ls[20:] / ls[:-20] - 1])}
    raw = {k: np.concatenate([[np.nan], v[:-1]]) for k, v in raw.items()}        # 다음 거래일부터
    rk = {k: rank250(v) for k, v in raw.items()}
    rk["대차"] = 100 - rk["대차"]
    m = np.array(list(rk.values()))
    with np.errstate(all="ignore"):
        score = np.nanmean(m, axis=0)
    score[np.isfinite(m).sum(axis=0) < 3] = np.nan
    return score, rk
