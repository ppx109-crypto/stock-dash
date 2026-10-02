"""F 6회차 셋째 판 — 받아진 investor-full 종목 안에서만(같은 대상끼리) 1일봉 엔진(새 82 · 씨앗 8): '금융투자 · 보험 둘 다 순매도면 안 삼'의 고원.
기간 3 · 5 · 10 · 20일 · 금융투자만 · 보험만 · 기타법인 더함 · 둘 중 하나 순매도면 안 삼(더 셈)."""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/f006.py", encoding="utf-8").read().split("# 앞으로 20 · 60일 수익")[0])
import ntools as T

IN = set(FULL)
base = lambda r: r["code"] in IN and nrl.BASE_HOLD(r)
neg = lambda r, col, n: (power(r, col, n) or 0) < 0
print(f"== F 6회차 셋째 판: 받아진 {len(IN)}종목 안에서만 ==", flush=True)
T.once("지금 사는 조건(이 종목들만)", holds=base)
for n in (3, 5, 10, 20):
    T.once(f"금융투자 · 보험 둘 다 {n}일 순매도면 안 삼", holds=lambda r, n=n: base(r) and not (neg(r, "금융투자", n) and neg(r, "보험", n)))
T.once("금융투자 5일 순매도면 안 삼", holds=lambda r: base(r) and not neg(r, "금융투자", 5))
T.once("보험 5일 순매도면 안 삼", holds=lambda r: base(r) and not neg(r, "보험", 5))
T.once("금융투자 · 보험 하나라도 5일 순매도면 안 삼", holds=lambda r: base(r) and not (neg(r, "금융투자", 5) or neg(r, "보험", 5)))
T.once("금융투자 · 보험 · 기타법인 셋 다 5일 순매도면 안 삼", holds=lambda r: base(r) and not (neg(r, "금융투자", 5) and neg(r, "보험", 5) and neg(r, "기타법인", 5)))
print("끝", flush=True)
