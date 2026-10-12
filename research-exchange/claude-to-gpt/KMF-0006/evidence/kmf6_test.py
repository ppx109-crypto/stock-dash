"""KMF-0006 합성 시험(성과 셈 없음 · 가짜 날별 손익)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf6 as K6  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


chk("1 앞 달 셈(해 넘김 포함)", K6.prev_months("202603", 3) == ["202602", "202601", "202512"] and K6.prev_months("202601", 1) == ["202512"])
pnl = {"A": {"20260210": 5.0, "20260305": 100.0}, "B": {"20260210": 3.0, "20260305": -50.0}}
chk("2 3월 고르기는 2월까지만 봄(3월 값 100이 커도 상관없음)", K6.choose(pnl, "202603", 1) == ("A", 5.0))
pnl2 = {"A": {"20260210": 5.0, "20260305": 1.0}, "B": {"20260210": 3.0, "20260305": 999.0}}
chk("3 같은 앞 달 값이면 그달 값을 바꿔도 같은 후보", K6.choose(pnl2, "202603", 1) == K6.choose(pnl, "202603", 1))
neg = {"A": {"20260210": -1.0}, "B": {"20260210": -2.0}}
chk("4 모두 손해면 쉼", K6.choose(neg, "202603", 1)[0] is None)
chk("5 같으면 이름 순", K6.choose({"B": {"20260210": 1.0}, "A": {"20260210": 1.0}}, "202603", 1)[0] == "A")
w = K6.walk({"A": {"20260210": 5.0, "20260305": 2.0, "20260402": -3.0}}, 1)
chk("6 걷기: 3월 A(+2) · 4월 A(3월 +2라 고름 · −3) · 5월 쉼(4월 −3)", [r["pick"] for r in w["months"][:3]] == ["A", "A", None] and w["months"][1]["month_p"] == -3.0)
chk("7 후보 26개 · 이름 겹침 없음", len(K6.pool()) == 26 and len({K6.pname(*x) for x in K6.pool()}) == 26)
chk("8 잠금 통과", bool(K6.verify_inputs()))
print(f"모두 통과 {ok}개")
