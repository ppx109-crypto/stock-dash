"""검사 도구 자체 시험(반대 검토 결함 5): ledger_ok · cut_compare가 섞은 순서 · 칸 넘침 · 기존 줄 바뀜 · 진입/판 줄/보유/계좌 차이를 FAIL로 잡는지."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks10 as C  # noqa: E402

OLD = [["X", "20200101", "20200110", 1.0, 2]] * C.OLD_N


def run():
    ok = []
    new = [["A", "20200102", "20200105", 0.5, 1], ["B", "20200102", "20200106", 0.1, 1], ["C", "20200103", "99999999", 0.0, 1]]
    meta = [{"산 날": "20200102", "그날 순위": 0}, {"산 날": "20200102", "그날 순위": 1}, {"산 날": "20200103", "그날 순위": 0}]
    small_old = [["X", "20200101", "20200110", 1.0, 2]]
    C.OLD_N, n0 = 1, C.OLD_N
    led = small_old + new
    ok.append(("정상 장부 PASS", C.ledger_ok(led, meta, small_old)[0]))
    sh = small_old + [new[1], new[0], new[2]]
    ok.append(("섞은 순서 FAIL", not C.ledger_ok(sh, [meta[1], meta[0], meta[2]], small_old)[0]))
    big = [["Y", "20200101", "20200110", 0, 8]] + new
    ok.append(("칸 넘침 FAIL", not C.ledger_ok(big, meta, [["Y", "20200101", "20200110", 0, 8]])[0]))
    ok.append(("기존 줄 바뀜 FAIL", not C.ledger_ok([["Z", "20200101", "20200110", 1.0, 2]] + new, meta, small_old)[0]))
    C.OLD_N = n0
    nav = {"20200102": {"NAV": "1"}, "20200103": {"NAV": "2"}, "20200104": {"NAV": "3"}}
    part = [new[0][:2] + ["99999999", 0.0, 1], new[1][:2] + ["99999999", 0.0, 1], new[2]]
    ok.append(("같은 prefix PASS", C.cut_compare(new, part, nav, copy.deepcopy(nav), "20200104")[0]))
    ok.append(("진입 순서 다름 FAIL", not C.cut_compare(new, [part[1], part[0], part[2]], nav, nav, "20200104")[0]))
    nav2 = copy.deepcopy(nav)
    nav2["20200103"] = {"NAV": "2.0001"}
    ok.append(("계좌 날 다름 FAIL", not C.cut_compare(new, part, nav, nav2, "20200104")[0]))
    ok.append(("판 줄 다름 FAIL", not C.cut_compare(new, part, nav, nav, "20200105")[0]))
    ok.append(("빈 비교 FAIL", not C.cut_compare([], [], nav, nav, "20200104")[0]))
    for n, v in ok:
        print("PASS" if v else "FAIL", n)
    return all(v for _, v in ok)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
