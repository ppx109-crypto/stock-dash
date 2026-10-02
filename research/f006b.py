"""F 6회차 둘째 판(미리) — 받아진 investor-full 종목 안에서만(같은 대상끼리 공정 견줌) 1일봉 엔진(새 82 · 씨앗 8):
지금 사는 조건 vs + 금융투자 / 보험 / 기타법인 5일 순매수(전날까지) 거르기 · 칸 +1."""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/f006.py", encoding="utf-8").read().split("# 앞으로 20 · 60일 수익")[0])
import ntools as T

IN = set(FULL)
base = lambda r: r["code"] in IN and nrl.BASE_HOLD(r)
plus = lambda col: (lambda r: base(r) and (power(r, col) or 0) > 0)
up = lambda col: (lambda r: min(4, nrl.BASE_SIZE(r) + 1) if (power(r, col) or 0) > 0 else nrl.BASE_SIZE(r))
print(f"== F 6회차 둘째 판(미리): 받아진 {len(IN)}종목 안에서만 ==", flush=True)
T.once("지금 사는 조건(이 종목들만)", holds=base)
for col in ("금융투자", "보험", "기타법인"):
    T.once(f"+ {col} 순매수만 삼", holds=plus(col))
    T.once(f"+ {col} 순매수면 칸 +1", holds=base, size=up(col))
T.once("+ 금융투자 또는 보험 순매수만 삼", holds=lambda r: base(r) and ((power(r, "금융투자") or 0) > 0 or (power(r, "보험") or 0) > 0))
T.once("+ 금융투자 · 보험 둘 다 순매도면 안 삼", holds=lambda r: base(r) and not ((power(r, "금융투자") or 0) < 0 and (power(r, "보험") or 0) < 0))
print("끝", flush=True)
