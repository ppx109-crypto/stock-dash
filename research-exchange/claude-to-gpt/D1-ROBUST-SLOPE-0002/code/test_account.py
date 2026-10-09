# 합성 자료로 account()만 시험(엔진 · 실제 자료 안 읽음)
import ast, types
from collections import defaultdict
src = open("/home/user/stock-dash/research/z077.py").read()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "account")
ns = {"defaultdict": defaultdict, "nrl": types.SimpleNamespace(SLOTS=10, lanes=None)}
exec(compile(ast.Module([fn], []), "acc", "exec"), ns)
acc = ns["account"]
L = {"A": {"날": ["20200102", "20200103", "20200106"], "closes": [100, 110, 99]},
     "B": {"날": ["20200102", "20200103", "20200106"], "closes": [50, 50, 50]}}
r = acc([{"code": "A", "산 날": "20200102", "판 날": "20200106", "자리": 10, "손익": -1.0}], L)
print("1", r); assert r["worst_day"][1] == -10.0 and r["worst_month"][1] == -1.0 and r["mdd_daily"][1] == -10.0 and r["end_nav"] == 0.99
r = acc([{"code": "A", "산 날": "20200102", "판 날": "20200106", "자리": 6, "손익": -1.0},
         {"code": "B", "산 날": "20200102", "판 날": "20200106", "자리": 6, "손익": -0.5}], L)
print("2", r); assert r["capped_buys"] == 1 and abs(r["end_nav"] - (0.6 * 0.99 + 0.4 * 0.995)) < 1e-4
r = acc([{"code": "A", "산 날": "20200102", "판 날": "20200103", "자리": 2, "손익": 9.75},
         {"code": "A", "산 날": "20200102", "판 날": "20200106", "자리": 2, "손익": -1.25}], L)
print("3", r); assert abs(r["end_nav"] - (1 + 0.2 * 0.0975 - 0.2 * 0.0125)) < 1e-4
print("합성 시험 통과")
