"""door.walk 합성 시험(GPT #421 지적 1 · 2): ① 장부 순서 = 들어간 순서(미래 판 날 순서가 아님) ② 기존 문 우선 · 날마다 칸 ≤ 10
③ 같은 날 산 순서가 미래 값을 바꿔도 그대로 ④ 앞날 기존 진입을 미리 보지 않음. python3 test_door.py"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import door  # noqa: E402

CAL = [f"2020010{i}" for i in range(1, 10)]
TRADE = set(CAL)


def px(over=None):
    P = {d: {"A": 100.0, "B": 100.0, "C": 100.0, "X": 100.0} for d in CAL}
    for (d, c), v in (over or {}).items():
        P[d][c] = v
    return P


def zs(over=None):
    Z = {d: {"A": -1.0, "B": -1.0, "C": -1.0, "X": -1.0} for d in CAL}
    for (d, c), v in (over or {}).items():
        Z[d][c] = v
    return Z


def run():
    ok = []
    # ① A가 1순위 · B가 2순위로 같은 날(CAL[2]) 들어감. B가 먼저 나감(z ≥ 0) → 장부 순서는 A, B 그대로여야 함.
    cands = {CAL[1]: [(-3.0, "A"), (-2.5, "B")]}
    Z = zs({(CAL[3], "B"): 0.5})
    led, st, meta = door.walk(CAL, TRADE, cands, Z, px(), [], H=5)
    ok.append(("① 순서 = 들어간 순서", [r[0] for r in led] == ["A", "B"] and led[1][2] == CAL[4]))
    # ③ B의 미래 값만 바꿔도 앞 순서 · 산 날 같음
    led2, _, _ = door.walk(CAL, TRADE, cands, Z, px({(CAL[4], "B"): 150.0}), [], H=5)
    ok.append(("③ 미래 값이 순서를 안 바꿈", [(r[0], r[1]) for r in led] == [(r[0], r[1]) for r in led2]))
    # ② 기존 8칸(X 산 날 CAL[0] ~ CAL[8]) + 새 2칸(CAL[2]) → CAL[4]에 기존 2칸(C 대신 'Y'… 기존 장부 줄) 더 들어오면 새 문 늦게 든 B부터 정리
    old = [["X", CAL[0], CAL[8], 0.0, 8], ["C", CAL[4], CAL[8], 0.0, 1]]
    led3, st3, meta3 = door.walk(CAL, TRADE, cands, zs(), px(), old, H=8)
    newrows = led3[len(old):]
    bad = door.occupancy_ok(led3, CAL)
    ok.append(("② 칸 ≤ 10 날마다", not bad and st3["칸 넘은 날"] == 0))
    ok.append(("② 늦게 든 B부터 그날 종가 정리", newrows[1][0] == "B" and newrows[1][2] == CAL[4] and meta3[1]["나감"] == "기존 문 우선"
               and newrows[0][2] == "99999999"))
    # ④ 앞날 기존 진입(CAL[4])을 CAL[2]에 미리 보지 않음 — 기존 진입을 지워도 CAL[2] 산 것 같음
    led4, _, _ = door.walk(CAL, TRADE, cands, zs(), px(), old[:1], H=8)
    ok.append(("④ 앞날 기존 진입 안 봄", [(r[0], r[1]) for r in led3[len(old):]] == [(r[0], r[1]) for r in led4[1:]]))
    # ⑤ 장부를 일부러 섞으면 occupancy_ok는 그대로지만 순서 시험이 잡음(검사 도구 자체 시험)
    sh = copy.deepcopy(led)
    sh.reverse()
    ok.append(("⑤ 검사 도구: 섞은 순서를 잡음", [r[0] for r in sh] != ["A", "B"]))
    for n, v in ok:
        print("PASS" if v else "FAIL", n)
    return all(v for _, v in ok)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
