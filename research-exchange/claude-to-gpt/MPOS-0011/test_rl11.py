"""MPOS-0011 합성 시험: 결정은 앞선 끝난 달만 · 같은 문맥만 · 표본 < 6이면 P0 · 동률 순서 · 효용 λ · 0과 결측."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rl11 as R  # noqa: E402


def rr(p0, base=None):
    return {"P0": p0, "BASE": p0 if base is None else base, "HALF": p0 / 2, "CASH": 0.0}


def run():
    ok = []
    ctx = lambda m: (True, False)
    past = [(f"2017{i:02d}", (True, False), rr(-0.02)) for i in range(1, 8)]
    ok.append(("손실만 본 문맥 → CASH", R.decide("201708", past, 1.0, None, ctx)[0] == "CASH"))
    ok.append(("표본 5 → P0", R.decide("201708", past[:5], 1.0, None, ctx)[0] == "P0"))
    fut = past + [("201709", (True, False), rr(0.5))]
    ok.append(("결정 달 뒤 자료 안 씀", R.decide("201708", fut, 1.0, None, ctx)[0] == "CASH"))
    other = [(f"2017{i:02d}", (False, False), rr(0.05)) for i in range(1, 8)]
    ok.append(("다른 문맥 자료 안 씀", R.decide("201708", other + past, 1.0, None, ctx)[0] == "CASH"))
    zero = [(f"2017{i:02d}", (True, False), {"P0": 0.0, "BASE": 0.0, "HALF": 0.0, "CASH": 0.0}) for i in range(1, 8)]
    ok.append(("모두 0 동률 → P0", R.decide("201708", zero, 3.0, None, ctx)[0] == "P0"))
    mix = [(f"2017{i:02d}", (True, False), rr(0.03 if i % 2 else -0.02)) for i in range(1, 9)]
    a1, a3 = R.decide("201709", mix, 0.0, None, ctx)[0], R.decide("201709", mix, 3.0, None, ctx)[0]
    ok.append(("λ 0 → P0 · λ 3 → CASH(평균 +0.5% · 하방 큼)", a1 == "P0" and a3 == "CASH"))
    win = [(f"2017{i:02d}", (True, False), rr(0.03)) for i in range(1, 7)] + [(f"2018{i:02d}", (True, False), rr(-0.05)) for i in range(1, 7)]
    ok.append(("창 6 → 최근 6달만(CASH) · 전부 → P0와 CASH 비교", R.decide("201901", win, 1.0, 6, ctx)[0] == "CASH"))
    ok.append(("문맥 없음(None) → P0", R.decide("201708", past, 1.0, None, lambda m: None)[0] == "P0"))
    ok.append(("gt 0과 None", R.gt(0.0, -1.0) and not R.gt(None, 1.0) and not R.gt(0.0, 0.0)))
    ok.append(("이웃", set(R.nei("RL_L3_WALL")) == {"RL_L1_WALL", "RL_L3_W36"}))
    for n, v in ok:
        print("PASS" if v else "FAIL", n)
    return all(v for _, v in ok)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
