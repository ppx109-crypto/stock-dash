"""E 3회차 — 1회차에서 두 반 모두 같은 쪽으로 나온 실적 거르기를 1일봉 엔진(새 82 · 씨앗 8)에 넣어 봄.
실적 자료가 없는 종목은 그대로 통과(지금 규칙과 같게). 접수일이 신호 날 앞인 보고서만."""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import etools as E
import nrl
import ntools as T

book = E.Book()
memo = {}


def f(r):
    k = (r["code"], r["date"])
    if k not in memo:
        memo[k] = book.feats(*k) or {}
    return memo[k]


base = nrl.BASE_HOLD
cut_loss = lambda r: f(r).get("q_turn") == "적지"
cut_sales = lambda r: (f(r).get("q_s") is not None and f(r)["q_s"] <= -20)
cut_run = lambda r: f(r).get("run", 0) >= 4
cut_ytd_loss = lambda r: f(r).get("ytd_turn") == "적지"
print("== E 3회차: 실적 거르기를 1일봉 엔진에 ==", flush=True)
b = T.once("지금(새 82)", holds=base)
for tag, cut in (("− 이번 분기 영업 적자 지속", cut_loss), ("− 올해 누적 영업 적자 지속", cut_ytd_loss),
                 ("− 분기 매출 작년보다 20%↓", cut_sales), ("− 영업이익 4분기 넘게 이어 늘음", cut_run),
                 ("− 적자 지속 · 매출 20%↓", lambda r: cut_loss(r) or cut_sales(r)),
                 ("− 셋 다", lambda r: cut_loss(r) or cut_sales(r) or cut_run(r))):
    g = T.once(tag, holds=lambda r, cut=cut: base(r) and not cut(r))
    T.diff_check(b, g, "거른")
print("끝", flush=True)
