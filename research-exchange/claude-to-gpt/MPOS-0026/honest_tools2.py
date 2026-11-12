"""정직 캐시 도구 시험 ⑤ ⑥ ⑦(HONEST_CACHE.md 판 2 · 합성 · 손익 없음 · honest_cache.py 함수를 그대로 씀).
⑤ 필수 칸 하나를 지운 판 → rows_diff_strict가 '칸 이름 다른 행'으로 잡아 같음=거짓
⑥ 달 중간 c 뒤에 미래 행을 넣거나 지워도 c가 든 달 · 지난 달 T[m] 같음(정직) / 전체 한 번 문턱은 바뀜(누수 대조)
⑦ 가격판 교체(한 종목 가격을 비례 아닌 모양으로) → 칸 대조가 잡음.
cwd = 고정 나무 · tree_run. 출력: 인자 1(json)."""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import lab  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402
_HC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "honest_cache.py")   # tree_run은 나무 밖 모듈 import를 막으므로 원문을 exec
_ns = {"__name__": "honest_cache", "__file__": _HC}
exec(compile(open(_HC, encoding="utf-8").read(), _HC, "exec"), _ns)
month_edges_asof, rows_diff_strict = _ns["month_edges_asof"], _ns["rows_diff_strict"]

cal = [d for d, _ in study.load_prices()["005930"]["rows"] if d <= "20260331"][-420:]
rng = np.random.default_rng(20261018)
walk = lambda n, s: [round(10000 * float(x), 2) for x in np.exp(np.cumsum(rng.normal(0.0004, s, n)))]  # noqa: E731
P = {f"Z9200{i}": {"name": f"가짜{i}", "rows": list(zip(cal, walk(420, 0.01 + 0.01 * i)))} for i in range(1, 6)}


def build(prices):
    out = {}
    for c in sorted(prices):
        for r in lab.build({c: prices[c]}, horizons=(0,)):
            r.pop("ahead", None)
            out[(r["code"], r["date"])] = r
    return out


R = build(P)
res = {}
# ⑤
k0 = sorted(R)[len(R) // 2]
B = {k: ({c: v for c, v in r.items() if c != "추세 기울기"} if k == k0 else r) for k, r in R.items()}
d5 = rows_diff_strict(R, B)
res["⑤ 필수 칸 지운 판"] = {**d5, "잡힘": d5["칸 이름 다른 행"] == 1 and not d5["같음"]}
# ⑥ 달 중간 c
_mm = sorted({d[:6] for d in cal})[len({d[:6] for d in cal}) // 2]
mid = min(d for d in cal if d[:6] == _mm and d[6:] >= "14")      # 셈 전 고정 규칙: 가운데 달의 14일 이후 첫 거래일(첫 판은 목록 위치 실수로 12-29를 골랐음 · 고침)
vols = [(k[1], r.get("변동성")) for k, r in R.items()]
first = {}
for d, _ in vols:
    if d < first.get(d[:6], "99999999"):
        first[d[:6]] = d
months = sorted(first)
upto_m = [m for m in months if m <= mid[:6]]
T_full = month_edges_asof(vols, months, first, min_k=50)
T_cut = month_edges_asof([x for x in vols if x[0] <= mid], months, {m: first[m] for m in months if first[m] <= mid}, min_k=50)
fake = vols + [(d, 99.0) for d in cal if d > mid for _ in range(30)]                   # c 뒤 미래 행을 크게 넣음
T_fake = month_edges_asof(fake, months, first, min_k=50)
same = all(T_full.get(m) == T_cut.get(m) == T_fake.get(m) for m in upto_m)
g = lambda vs: sorted(v for _, v in vs if v is not None)[int(len([1 for _, v in vs if v is not None]) * rule.CALM)]  # noqa: E731
G_full, G_fake = g(vols), g(fake)
flips = sum(1 for d, v in vols if d <= mid and v is not None and (v <= G_full) != (v <= G_fake))
res["⑥ 달 중간 컷"] = {"c": mid, "c 달까지 T 같음(긴 · 자름 · 미래 행 넣음)": same, "비교 달 수": len(upto_m),
                    "누수 대조: 전체 한 번 문턱": [G_full, G_fake], "누수로 c 앞 판단 바뀜": flips, "잡힘": same and flips > 0}
# ⑦ 가격판 교체: Z92003 앞 절반 가격을 날짜마다 다른 배수(0.98 ~ 1.0)로
P2 = {c: (dict(b, rows=[(d, x * (0.98 + 0.02 * (i % 7) / 6)) if i < 210 else (d, x) for i, (d, x) in enumerate(b["rows"])]) if c == "Z92003" else b)
      for c, b in P.items()}
d7 = rows_diff_strict(R, build(P2))
res["⑦ 가격판 교체"] = {**d7, "잡힘": not d7["같음"] and sum(d7["칸 다름"].values()) > 0}
res["모두 통과"] = all(v["잡힘"] for v in res.values())
json.dump(res, open(sys.argv[1], "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
sys.exit(0 if res["모두 통과"] else 3)
