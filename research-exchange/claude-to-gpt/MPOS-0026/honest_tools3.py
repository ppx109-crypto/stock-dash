"""정직 캐시 도구 시험 ⑧ ~ ⑪(GPT #457 4차 · 합성 · 손익 없음 · honest_cache.py 원문 exec).
⑧ 유한 대 +inf · −inf · +inf 대 −inf · 유한 대 NaN은 다름 / NaN 대 NaN · +inf 대 +inf는 같음 / int 1 대 float 1.0은 수치 호환으로 같음 · bool은 수치 아님
⑨ rows_diff_strict가 ⑧의 칸 오염을 잡음
⑩ keyed_diff: 한쪽에만 있는 달 · 날 키를 양쪽 다 잡음 · 값 다름 · None 대 숫자
⑪ shape_diff: 한쪽에만 있는 종목 · 배열 길이 모자람 · inf 부호 다름 · NaN 위치 다름을 잡고 같은 배열은 통과.
honest_cache.py가 나무 모듈을 불러오므로 cwd = 고정 나무 · tree_run. 출력: 인자 1(json)."""
import json
import math
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
_HC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "honest_cache.py")
_ns = {"__name__": "honest_cache", "__file__": _HC}
exec(compile(open(_HC, encoding="utf-8").read(), _HC, "exec"), _ns)
num_same, rows_diff_strict, keyed_diff, shape_diff = (_ns[k] for k in ("num_same", "rows_diff_strict", "keyed_diff", "shape_diff"))
inf, nan = float("inf"), float("nan")
res = {}
cases = [(1.0, inf, False), (1.0, -inf, False), (inf, -inf, False), (1.0, nan, False), (nan, nan, True), (inf, inf, True), (-inf, -inf, True),
         (1.0, 1.0 + 1e-12, True), (1.0, 1.001, False)]
got = [(str(a), str(b), num_same(a, b), want) for a, b, want in cases]
res["⑧ num_same"] = {"사례": got, "잡힘": all(g == w for _, _, g, w in got)}
base = {("A", "20200102"): {"x": 1.0, "n": 1, "b": True}, ("A", "20200103"): {"x": 2.0, "n": 2, "b": False}}
vari = {
    "유한 대 +inf": {k: (dict(v, x=inf) if k[1] == "20200103" else v) for k, v in base.items()},
    "유한 대 −inf": {k: (dict(v, x=-inf) if k[1] == "20200103" else v) for k, v in base.items()},
    "유한 대 NaN": {k: (dict(v, x=nan) if k[1] == "20200103" else v) for k, v in base.items()},
    "bool 대 int": {k: (dict(v, b=1) if k[1] == "20200102" else v) for k, v in base.items()},
}
r9 = {name: not rows_diff_strict(base, v)["같음"] for name, v in vari.items()}
compat = rows_diff_strict(base, {k: dict(v, n=float(v["n"])) for k, v in base.items()})["같음"]
res["⑨ rows_diff_strict 칸 오염"] = {"잡힘 사례": r9, "int 1 대 float 1.0 같음(수치 호환)": compat, "잡힘": all(r9.values()) and compat}
Ta = {"202001": 1.0, "202002": 2.0, "202003": 3.0}
k1 = keyed_diff(Ta, {"202001": 1.0, "202002": 2.0}, upto="202003")
k2 = keyed_diff({"202001": 1.0}, Ta, upto="202003")
k3 = keyed_diff(Ta, dict(Ta, **{"202002": 2.5}), upto="202003")
k4 = keyed_diff(Ta, dict(Ta, **{"202002": None}), upto="202003")
k5 = keyed_diff(Ta, dict(Ta, **{"202004": 9.0}), upto="202003")          # c 뒤 키는 비교 밖
res["⑩ keyed_diff 양쪽 키"] = {"A에만": k1["A만 수"], "B에만": k2["B만 수"], "값 다름": k3["값 다름 수"], "None 대 숫자": k4["값 다름 수"], "c 뒤 키 무시": k5["같음"],
                            "잡힘": k1["A만 수"] == 1 and k2["B만 수"] == 2 and k3["값 다름 수"] == 1 and k4["값 다름 수"] == 1 and k5["같음"]}
arr = {"정배열": [0, 1, 1, 0], "간격": [nan, 0.1, 0.2, 0.3], "50>200": [0, 0, 1, 1]}
same = shape_diff({"A": arr}, {"A": dict(arr)}, {"A": 4})["같음"]
s_only = shape_diff({"A": arr}, {"A": arr, "B": arr}, {"A": 4, "B": 4})
s_len = shape_diff({"A": arr}, {"A": {k: v[:3] for k, v in arr.items()}}, {"A": 4})
s_inf = shape_diff({"A": dict(arr, 간격=[nan, inf, 0.2, 0.3])}, {"A": dict(arr, 간격=[nan, -inf, 0.2, 0.3])}, {"A": 4})
s_nan = shape_diff({"A": arr}, {"A": dict(arr, 간격=[0.0, 0.1, 0.2, 0.3])}, {"A": 4})
res["⑪ shape_diff"] = {"같은 배열 통과": same, "B에만 종목": s_only["B만 종목"], "길이 모자람": s_len["다른 종목"], "inf 부호": s_inf["다른 종목"], "NaN 위치": s_nan["다른 종목"],
                       "잡힘": same and s_only["B만 종목"] == 1 and s_len["다른 종목"] == 1 and s_inf["다른 종목"] == 1 and s_nan["다른 종목"] == 1}
res["모두 통과"] = all(v["잡힘"] for v in res.values())
json.dump(res, open(sys.argv[1], "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
sys.exit(0 if res["모두 통과"] else 3)
