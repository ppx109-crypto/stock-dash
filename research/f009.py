"""F 9회차 — F4에서 두 반 같은 쪽이던 '전환'(기관 · 투신 · 연기금이 20일 팔다 5일 삼) · '같이 감'(프로그램 · 외국인이 함께 삼)을
1일봉 엔진(새 82 · 씨앗 8) 안에서 사는 순서 · 칸 재료로. 문턱은 쓰지 않음(같은 날 후보끼리 순서만 · 켜짐/꺼짐은 부호로)."""
import os
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/f003.py", encoding="utf-8").read().split("\npart = os.environ")[0])
import ntools as T

fs20 = lambda r, c: nrl.flow_sum(r, 20, c)


def turned(r, cols=("기관", "투신", "연기금")):
    for c in cols:
        a, b = fs20(r, c), fs(r, c)
        if a is not None and b is not None and a < 0 and b > 0:
            return True
    return False


def prog_power(r):
    p, v = prog(r), T.vol_avg(r["code"], r["date"])
    return p / v if p is not None and v else None


def frg_power(r):
    return T.flow_strength(r, 5, ("외국인",))


base_rank = rule.order
HOLD = nrl.BASE_HOLD
part = os.environ.get("Q_PART", "1")
print(f"== F 9회차({part}): 전환 · 같이 감을 순서 · 칸 재료로 ==", flush=True)
if part == "1":
    T.once("지금(새 82)", holds=HOLD)
    T.once("순서: 전환(기관 · 투신 · 연기금) 먼저", holds=HOLD, rank=lambda r: (0 if turned(r) else 1, base_rank(r)))
    T.once("순서: 기관 전환 먼저", holds=HOLD, rank=lambda r: (0 if turned(r, ("기관",)) else 1, base_rank(r)))
    T.once("순서: 프로그램 힘 큰 것 먼저", holds=HOLD, rank=lambda r: (-(prog_power(r) or -9), base_rank(r)))
    T.once("순서: 외국인 힘 큰 것 먼저", holds=HOLD, rank=lambda r: (-(frg_power(r) or -9), base_rank(r)))
    T.once("순서: 외국인 힘 작은 것 먼저(1시간봉 90회차 꼴)", holds=HOLD, rank=lambda r: ((frg_power(r) or 9), base_rank(r)))
else:
    up = lambda test: (lambda r: min(4, nrl.BASE_SIZE(r) + 1) if test(r) else nrl.BASE_SIZE(r))
    T.once("칸: 전환이면 +1칸(최대 4)", holds=HOLD, size=up(turned))
    T.once("칸: 기관 전환이면 +1칸", holds=HOLD, size=up(lambda r: turned(r, ("기관",))))
    T.once("칸: 프로그램 + 이면 +1칸", holds=HOLD, size=up(lambda r: (prog(r) or 0) > 0))
    T.once("칸: 프로그램 − 면 −1칸(최소 1)", holds=HOLD,
           size=lambda r: max(1, nrl.BASE_SIZE(r) - 1) if (prog(r) or 0) < 0 else nrl.BASE_SIZE(r))
    T.once("거름: 프로그램 5일 − 면 안 삼", holds=lambda r: HOLD(r) and (prog(r) is None or prog(r) >= 0))
print("끝", flush=True)
