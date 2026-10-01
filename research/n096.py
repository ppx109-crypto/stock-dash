"""일봉 새 96회차(세 갈래 공통 G11 · RNA 시장 폭 문턱 · 1일봉) — 정배열 문의 시장 폭 '50% 이상'을 '앞 n일 q분위 이상'으로(research/rnabr.py).
기준 = 새 82회차 · 씨앗 8 · 두 반. Q_PART=1 · 2로 나눔."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import rule
import rnabr as R


def hold(gate=None):
    def aligned2(r):
        f = nrl.F.form_of(nrl.shape, r)
        b = nrl.BR.get(r["date"])
        ok = (b or 0) >= 50 if gate is None else gate(r["date"], b)
        return bool(f.get("정배열") and f.get("간격") is not None and 19 <= f["간격"] < 53 and ok)
    return lambda r: (rule.holds(r) or aligned2(r)) and nrl.teacher(r) and not nrl.target_cut(r)


part = os.environ.get("Q_PART", "1")
print(f"== 일봉 새 96회차({part}): RNA 시장 폭 문턱 ==", flush=True)
T.once("기준(고정 50%)", holds=hold())
for name, n, q, mix in R.VARIANTS[part]:
    g = R.make_gate(nrl.BR, n, q, mix)
    fx, rn = R.open_share(nrl.BR, g, rule.SINCE)
    T.once(f"{name}(열린 날 {fx}→{rn}%)", holds=hold(g))
print("끝", flush=True)
