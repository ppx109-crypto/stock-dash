# 합성 자료로 account()만 시험(엔진 · 실제 자료 안 읽음)
import ast, types
from collections import defaultdict
src = open("/home/user/stock-dash/research/z077.py").read()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "account")
L = {"A": {"날": ["20200102", "20200103", "20200106", "20200107"], "closes": [100, 110, 99, 99]},
     "B": {"날": ["20200102", "20200103", "20200106", "20200107"], "closes": [50, 50, 50, 55]}}
lab = types.SimpleNamespace(trading_days=lambda lanes: sorted({d for v in lanes.values() for d in v["날"]}))
ns = {"defaultdict": defaultdict, "nrl": types.SimpleNamespace(SLOTS=10, lanes=L), "lab": lab}
exec(compile(ast.Module([fn], []), "acc", "exec"), ns)
acc = ns["account"]
S0, E0 = "20200102", "20200107"
# 1) +10% · −10% → 달 −1% (단순 합 0% 아님), 고정 기간 끝까지 NAV 유지
r = acc([{"code": "A", "산 날": S0, "판 날": "20200106", "자리": 10, "손익": -1.0}], [], S0, E0)
print(1, r); assert r["worst_day"][1] == -10.0 and r["worst_month"][1] == -1.0 and r["end_nav"] == 0.99 and r["period"] == [S0, E0]
# 2) 현금이 모자라도 줄이지 않음: 6칸 + 6칸 = 총노출 1.2 · 현금 −0.2
r = acc([{"code": "A", "산 날": S0, "판 날": "20200106", "자리": 6, "손익": -1.0},
         {"code": "B", "산 날": S0, "판 날": "20200106", "자리": 6, "손익": -0.5}], [], S0, E0)
print(2, r); assert abs(r["max_gross_exposure"] - 1.2) < 1e-9 or r["max_gross_exposure"] > 1.2 - 1e-9
assert abs(r["end_nav"] - (1 + 0.6 * -0.01 + 0.6 * -0.005)) < 1e-4
# 3) 반익 한 줄은 닫히고 나머지는 끝까지 남음(남은자리) → 끝날 종가로 평가
r = acc([{"code": "B", "산 날": S0, "판 날": "20200103", "자리": 2, "손익": 9.75}],
        [{"code": "B", "산 날": S0, "자리": 2, "price": 50}], S0, E0)
print(3, r); assert r["open_at_end"] == 1 and abs(r["end_nav"] - (1 + 0.2 * 0.0975 + 0.2 * 0.10)) < 1e-4
# 4) 같은 날 매수 순서를 바꿔도 같음
x = [{"code": "A", "산 날": S0, "판 날": "20200106", "자리": 6, "손익": -1.0}, {"code": "B", "산 날": S0, "판 날": "20200107", "자리": 6, "손익": 9.0}]
assert acc(x, [], S0, E0) == acc(x[::-1], [], S0, E0); print(4, "순서 무관")
print("합성 시험 통과")
# 5) 2.2판: 판정용 반올림 전 현금 값(min_cash_raw)이 있고, 오른 보유 + 새 매수로 생긴 작은 음수를 그대로 보임
r = acc([{"code": "A", "산 날": S0, "판 날": "20200107", "자리": 9, "손익": -1.0},
         {"code": "B", "산 날": "20200103", "판 날": "20200107", "자리": 1, "손익": 10.0}], [], S0, E0)
print(5, r["min_cash_raw"], r["min_cash_share"]); assert r["min_cash_raw"] < 0 and abs(r["min_cash_raw"] - (0.1 - 0.109)) < 1e-12
print("2.2판 합성 시험 통과")
