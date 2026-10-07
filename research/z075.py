"""N18 — 좁은 장 RL(docs/RL-NARROW.md): 1일봉 '새 82' 후보가 칸보다 많을 때 사는 순서를 '공매도 비중 낮은 것 먼저'로.
공매도 비중 20일 = 신호 날 **전날까지** 20거래일 공매도비중(short-data) 평균(15일 이상 있을 때) — 공매도 자료는 장 끝난 뒤 나오므로 그날 값은 안 씀.
판: ① 늘 공매도 낮은 것 먼저(같으면 지금 순서) ② 좁은 오름장 날(폭 < 50 · 코스피 ≥ 60일선)만 ①, 다른 날은 지금 순서.
문턱 · 거르기 · 칸은 그대로(Z3와 같은 방식). 공매도 값 없는 후보는 뒤로. 엔진 잣대(씨앗 8 · 두 반 · 행운뺌 · 비용).
Z_PART=check: 자르기 시험 — short-data를 T까지만 남겨도 T 이하 행의 순서 재료가 같은가 + 검사 눈(그날 값까지 쓴 재료는 걸려야 함).
CAPS_ADJ=1 NRL_CACHE=.../nrl-cache-adj.pkl python research/z075.py
"""
import bisect
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402
from z072 import KUP  # noqa: E402

ROOT = Path("/home/user/stock-dash")
base = nrl.rule.order
SH = {}


def short_rows(code):
    if code not in SH:
        p = ROOT / "short-data" / f"{code}.json"
        rows = []
        if p.exists():
            b = json.loads(p.read_text(encoding="utf-8"))
            k = b["cols"].index("공매도비중")
            rows = sorted((str(r[0]), float(r[k])) for r in b.get("rows") or [] if r[k] is not None)
        SH[code] = ([d for d, _ in rows], np.array([v for _, v in rows]))
    return SH[code]


def short20(r, lag=1):
    days, vals = short_rows(r["code"])
    j = bisect.bisect_left(days, r["date"]) + (1 - lag)          # lag 1: 그날 앞까지 · lag 0: 그날까지(검사 눈)
    w = vals[max(0, j - 20):j]
    return float(w.mean()) if len(w) >= 15 else None


def key_low(r):
    s = short20(r)
    return (0 if s is not None else 1, s if s is not None else 0.0, base(r))


def key_narrow(r):
    if nrl.BR.get(r["date"], 100) < 50 and KUP.get(r["date"]):
        return key_low(r)
    return (0, 0.0, base(r))


def main():
    print("== N18: 1일봉 후보 순서를 공매도 비중 낮은 것 먼저 ==", flush=True)
    got0 = T.once("지금(새 82 · 추세 기울기 순)", holds=nrl.BASE_HOLD)
    for tag, key in (("① 늘 공매도 낮은 것 먼저", key_low), ("② 좁은 오름장 날만 공매도 낮은 것 먼저", key_narrow)):
        got = T.once(tag, holds=nrl.BASE_HOLD, rank=key)
        T.diff_check(got0, got)


def check(cuts=("20190315", "20220615", "20250902")):
    rows = list(nrl.inside)
    full = {(r["code"], r["date"]): short20(r) for r in rows}
    peek = {(r["code"], r["date"]): short20(r, lag=0) for r in rows}
    saved = dict(SH)
    ok = True
    for cut in cuts:
        for code, (d, v) in saved.items():
            k = bisect.bisect_right(d, cut)
            SH[code] = (d[:k], v[:k])
        bad = [k for k in full if k[1] <= cut and full[k] != short20({"code": k[0], "date": k[1]})]
        # 검사 눈: 그날 값까지 쓴 재료는 cut 날 행에서 달라져야 함(cut 날 값을 지우면)
        for code, (d, v) in saved.items():
            k = bisect.bisect_left(d, cut)
            SH[code] = (d[:k], v[:k])
        caught = any(k[1] == cut and peek[k] != short20({"code": k[0], "date": k[1]}, lag=0) for k in peek)
        SH.update(saved)
        n = sum(1 for k in full if k[1] <= cut)
        print(f"[cut {cut}] 순서 재료 {n}행: {'합격' if not bad else f'불합격 {len(bad)}'} · 검사 눈 {'걸림' if caught else '안 걸림(고장)'}", flush=True)
        ok &= not bad and caught
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(check() if os.environ.get("Z_PART") == "check" else main())
