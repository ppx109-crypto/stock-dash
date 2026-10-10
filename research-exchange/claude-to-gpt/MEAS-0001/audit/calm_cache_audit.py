"""MEAS-0001 B — 1D 연구 캐시(nrl-cache.pkl)의 calm 문턱 출처 감사. 제한 로더(numpy._frombuffer · dtype만 허용)로 읽기만 함.
python calm_cache_audit.py <nrl-cache.pkl> <00b98ab1 폴더> <out.json>"""
import bisect
import json
import pickle
import socket
import sys
from pathlib import Path

import numpy as np

socket.socket = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
CACHE, BASE, OUT = sys.argv[1:4]
ALLOW = {("numpy._core.numeric", "_frombuffer"), ("numpy", "dtype")}


class Safe(pickle.Unpickler):
    def find_class(self, m, n):
        if (m, n) in ALLOW:
            return super().find_class(m, n)
        raise pickle.UnpicklingError(f"허용 안 된 참조 {m}.{n}")


with open(CACHE, "rb") as f:
    got = Safe(f).load()
prices, lanes, shape, BR, inside, calm = got[:6]
calm_month = got[6] if len(got) > 6 else None
# rule.py 기준점 상수(소스에서 읽음 · import 안 함)
src = Path(BASE, "rule.py").read_text(encoding="utf-8")
CALM_FRAC = [l for l in src.splitlines() if l.startswith("CALM =")]
SLOPE = 1.46
SIXTY = 20.0
days = sorted({r["date"] for r in inside})
out = {"cache_items": len(got), "rule._calm(cached)": calm, "rule.py CALM line": CALM_FRAC,
       "calm_month_available": calm_month is not None, "inside_rows": len(inside), "inside_first": days[0], "inside_last": days[-1],
       "BR_last": max(BR), "price_rows_last": max(d for v in prices.values() for d, _ in v["rows"])}
if calm_month:
    ks = sorted(calm_month)
    out["calm_month_first_last"] = [ks[0], calm_month[ks[0]], ks[-1], calm_month[ks[-1]]]
    out["calm_month_by_year_jan"] = {k: calm_month[k] for k in ks if k.endswith("01")}
    # 시간 맞춘 문턱(그 달 앞 자료만)과 캐시 문턱(전 기간 한 번)으로 '추세 문의 조용함 조건'만 다르게 갈리는 행 수
    flip = {"to_pass": 0, "to_fail": 0, "rows_with_vol": 0, "trend_rows_cached": 0, "trend_rows_monthly": 0}
    byyear = {}
    for r in inside:
        v = r.get("변동성")
        if v is None:
            continue
        key = r["date"][:6]
        cm = calm_month.get(key)
        if cm is None:
            continue
        flip["rows_with_vol"] += 1
        other = (r.get("추세 기울기") or -99) >= SLOPE and (r.get("60일 전 대비") or -99) >= SIXTY
        a, b = other and v <= calm, other and v <= cm
        flip["trend_rows_cached"] += a
        flip["trend_rows_monthly"] += b
        if a != b:
            y = r["date"][:4]
            byyear.setdefault(y, [0, 0])
            byyear[y][0 if b else 1] += 1
            flip["to_pass" if b else "to_fail"] += 1
    out["trend_door_calm_only_flip(수급 · 시총 문 전 · 조용함 조건만)"] = {**flip, "by_year[monthly_pass_only, cached_pass_only]": byyear}
Path(OUT).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "calm_month_by_year_jan"}, ensure_ascii=False, default=str)[:1500])
