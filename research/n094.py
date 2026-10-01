"""일봉 새 94회차(연구 ↔ 운영 맞춤) — 코드 대조에서 찾은 다름을 연구 엔진에 하나씩 넣어 운영(daily_live)이 실제로 내는 판의 성적을 잼.
① 후보 보는 수: 연구는 빈 칸 수만큼 위 후보만 보고(그중 이미 든 · 닮음 · 상한가면 그 칸은 그날 비움) · 운영은 칸이 찰 때까지 다음 후보로 내려감(greedy).
② 닮음 창: 연구는 들고 있는 종목을 산 날 창 · 운영은 오늘 창(새 91 · 92회차).
③ 판 날 다시 사기: 연구는 판 날 종가에 같은 종목을 다시 살 수 있고(cooldown 0) · 운영은 아침 보유 목록으로 막음(= cooldown 1).
Q_PART=2: ③과 ① + ② + ③(운영과 완전히 같은 판).
기준 = 새 82회차 · 씨앗 8."""
import bisect
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import lab

steps = lab.moves(nrl.prices)
DAYS = {c: [str(d) for d, _ in b["rows"]] for c, b in nrl.prices.items()}
research_kin = nrl.kin


def aligned(edge=0.6, back=60):
    def ok(row, held):
        day = DAYS[row["code"]][row["i"]]
        for h in held:
            j = bisect.bisect_right(DAYS.get(h["code"], []), day) - 1
            if j >= 0 and lab.kinship(steps, row, {"code": h["code"], "i": j}, back) >= edge:
                return False
        return True
    return ok


import os
part = os.environ.get("Q_PART", "1")
print(f"== 일봉 새 94회차({part}): 연구 ↔ 운영 맞춤 ==", flush=True)
if part == "2":
    T.once("③ 판 날 다시 안 삼(운영 방식)", cooldown=1)
    nrl.kin = aligned()
    T.once("① + ② + ③ (운영과 완전히 같은 판)", greedy=True, cooldown=1)
    nrl.kin = research_kin
    T.once("① + ③ (닮음은 연구 판)", greedy=True, cooldown=1)
    print("끝", flush=True)
    raise SystemExit
T.once("기준(연구 판)")
T.once("① 칸 찰 때까지 다음 후보(운영 방식)", greedy=True)
nrl.kin = aligned()
T.once("② 닮음 오늘 창(운영 방식)")
T.once("① + ② (운영과 같은 판)", greedy=True)
nrl.kin = lambda row, held: True
T.once("① + 닮음 거르기 끔", greedy=True)
print("끝", flush=True)
