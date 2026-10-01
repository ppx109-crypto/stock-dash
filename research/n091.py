"""일봉 새 91회차(세 갈래 공통 G7 · G8 · 1일봉) — 기준 = 새 82회차 · 씨앗 8 · 두 반(2017 ~ 2020 · 2021 ~).
Q_PART=1(G7): 닮은 종목 거르기 문턱 rule.KIN 0.6 → 0.5 · 0.7 · 끔 / Q_PART=2(G8): 칸 수 10 → 9 · 11 · 12(크기 4/4/3/2 그대로).
Q_PART=3(G7b): 날짜 맞춘 닮음 — lab.kinship은 들고 있는 줄의 창을 그 줄이 산 날에 둬 날이 어긋나면 닮음이 0 근처(research/kinpatch.py 주의).
  여기선 들고 있는 종목의 창도 오늘 후보의 날(그날까지 60일)로 맞춤 · 0.6 · 0.5 · 0.7."""
import bisect
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import lab

part = os.environ.get("Q_PART", "1")
print(f"== 일봉 새 91회차({part}): { {'1': '닮은 종목 문턱', '2': '칸 수', '3': '날짜 맞춘 닮음'}[part]} ==", flush=True)
T.once("기준(닮음 0.6 · 10칸)")
if part == "1":
    steps = lab.moves(nrl.prices)
    for e, tag in ((0.5, "닮음 0.5"), (0.7, "닮음 0.7"), (1.01, "닮음 거르기 끔")):
        nrl.kin = lab.unlike(steps, edge=e)
        T.once(tag)
elif part == "3":
    steps = lab.moves(nrl.prices)
    DAYS = {c: [str(d) for d, _ in b["rows"]] for c, b in nrl.prices.items()}

    def aligned(edge, back=60):
        def ok(row, held):
            day = DAYS[row["code"]][row["i"]]
            for h in held:
                j = bisect.bisect_right(DAYS.get(h["code"], []), day) - 1
                if j >= 0 and lab.kinship(steps, row, {"code": h["code"], "i": j}, back) >= edge:
                    return False
            return True
        return ok
    for e in (0.6, 0.5, 0.7):
        nrl.kin = aligned(e)
        T.once(f"날짜 맞춘 닮음 {e}")
else:
    for s in (9, 11, 12):
        T.once(f"{s}칸", slots=s)
print("끝", flush=True)
