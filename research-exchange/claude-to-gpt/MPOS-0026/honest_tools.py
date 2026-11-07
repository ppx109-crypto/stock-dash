"""정직 캐시 도구 시험(합성 · 손익 없음 · HONEST_CACHE.md 2): 가짜 종목(Z9100x · 자료 파일 없음)의 종가로 고정 나무 lab.build를 돌려
① 정직판(horizons=(0,) + 달 문턱 '그달 첫날 앞 행 40% 자리')은 c 뒤 가격을 바꾸거나 지워도 c까지 행 · 칸 · 달 문턱이 같음
② 고의 누수 A(전체 한 번 문턱 · rule.calm_edge식)는 c 뒤를 바꾸면 c 앞 조용함 판단이 바뀜 → 잡혀야 함
③ 고의 누수 B(horizons=(5,10,20,60))는 c 앞 마지막 5바 행이 빠짐 → 잡혀야 함
④ 칸 대조 도구(rows_diff)는 c까지 행의 한 칸에 일부러 다른 값을 넣으면 잡아야 함.
실제 검사에서도 같은 rows_diff · month_edges를 씀. cwd = 고정 나무 · tree_run. 출력: 인자 1(json)."""
import bisect
import json
import math
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import numpy as np  # noqa: E402
import lab  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402

SKIP = {"ahead", "i"}


def month_edges(vols_by_date, months, q=rule.CALM):
    """달마다 그달 첫날 앞 모든 행 변동성의 q 자리(int(k × q) · nrl._calm_by_month와 같은 식)."""
    got = sorted(vols_by_date)
    days = [d for d, _ in got]
    out = {}
    for m in months:
        k = bisect.bisect_left(days, m + "01")
        if k:
            v = sorted(x for _, x in got[:k])
            out[m] = v[int(k * q)]
    return out


def rows_diff(A, B, upto):
    """행 사전 {(종목, 날): 행} 둘을 upto까지 비교: 한쪽만 있는 행 · 칸 값 다른 (칸 → 건수)."""
    a = {k: v for k, v in A.items() if k[1] <= upto}
    b = {k: v for k, v in B.items() if k[1] <= upto}
    bad = {}
    for k in set(a) & set(b):
        for col, x in a[k].items():
            if col in SKIP:
                continue
            y = b[k].get(col, "<없음>")
            same = (isinstance(x, float) and isinstance(y, float) and ((math.isnan(x) and math.isnan(y)) or abs(x - y) <= 1e-9 * max(1.0, abs(x), abs(y)))) or x == y
            if not same:
                bad[col] = bad.get(col, 0) + 1
    return {"A만": len(set(a) - set(b)), "B만": len(set(b) - set(a)), "칸 다름": bad}


def build(prices, upto, horizons=(0,)):
    pp = {c: dict(b, rows=[x for x in b["rows"] if x[0] <= upto]) for c, b in prices.items()}
    rows = {}
    for c in sorted(pp):
        for r in lab.build({c: pp[c]}, horizons=horizons):
            r.pop("ahead", None)
            rows[(r["code"], r["date"])] = r
    return rows


cal = [d for d, _ in study.load_prices()["005930"]["rows"] if d <= "20260331"][-420:]
rng = np.random.default_rng(20261017)
walk = lambda n, s=0.02: [round(10000 * float(x), 2) for x in np.exp(np.cumsum(rng.normal(0.0004, s, n)))]  # noqa: E731
P = {f"Z9100{i}": {"name": f"가짜{i}", "rows": list(zip(cal, walk(420, 0.01 + 0.01 * i)))} for i in range(1, 6)}
cut = cal[379]
months = sorted({d[:6] for d in cal if d <= cut})
full, pre = build(P, cal[-1]), build(P, cut)
# c 뒤 가격을 크게 흔든 판(변동성 2배 · 값 0.7배)
shake = {c: dict(b, rows=[(d, x * (0.7 + 0.6 * (int(d) % 2)) if d > cut else x) for d, x in b["rows"]]) for c, b in P.items()}
shaken = build(shake, cal[-1])
vol = lambda R, upto: [(k[1], r["변동성"]) for k, r in R.items() if k[1] <= upto and r.get("변동성") is not None]  # noqa: E731
vol_all = lambda R: [(k[1], r["변동성"]) for k, r in R.items() if r.get("변동성") is not None]  # noqa: E731
res = {}
# ①
d1, d2 = rows_diff(pre, full, cut), rows_diff(pre, shaken, cut)
me_pre, me_full, me_shk = month_edges(vol(pre, cut), months), month_edges(vol_all(full), months), month_edges(vol_all(shaken), months)
res["① 정직판 불변(앞 묶음 대 긴 묶음 · 흔든 묶음)"] = {"대 긴": d1, "대 흔든": d2, "달 문턱 같음": me_pre == me_full == me_shk,
                                              "pass": d1 == d2 == {"A만": 0, "B만": 0, "칸 다름": {}} and me_pre == me_full == me_shk}
# ②
g_full = sorted(x for _, x in vol_all(full))
g_shk = sorted(x for _, x in vol_all(shaken))
G1, G2 = g_full[int(len(g_full) * rule.CALM)], g_shk[int(len(g_shk) * rule.CALM)]
flips = sum(1 for k, r in full.items() if k[1] <= cut and r.get("변동성") is not None and (r["변동성"] <= G1) != (r["변동성"] <= G2))
res["② 고의 누수 A(전체 한 번 문턱)"] = {"G(긴)": G1, "G(흔든)": G2, "c 앞 판단 바뀜": flips, "잡힘": flips > 0}
# ③
o_pre, o_full = build(P, cut, (5, 10, 20, 60)), build(P, cal[-1], (5, 10, 20, 60))
d3 = rows_diff(o_pre, o_full, cut)
res["③ 고의 누수 B(horizons 5…)"] = {**d3, "잡힘": d3["B만"] > 0}
# ④
k0 = sorted(k for k in pre if k[1] <= cut)[len(pre) // 2]
poisoned = {k: (dict(v, **{"추세 기울기": (v.get("추세 기울기") or 0) + 0.123}) if k == k0 else v) for k, v in full.items()}
d4 = rows_diff(pre, poisoned, cut)
res["④ 칸 대조 도구(한 칸에 일부러 다른 값)"] = {**d4, "잡힘": d4["칸 다름"].get("추세 기울기") == 1}
res["모두 통과"] = res["① 정직판 불변(앞 묶음 대 긴 묶음 · 흔든 묶음)"]["pass"] and all(res[k]["잡힘"] for k in res if k[0] in "②③④")
json.dump(res, open(sys.argv[1], "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
sys.exit(0 if res["모두 통과"] else 3)
