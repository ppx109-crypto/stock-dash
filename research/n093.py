"""일봉 새 93회차(세 갈래 공통 G10 · 1일봉) — 하루에 새로 사는 종목 수 한도(새 30회차에 뺌 · 그때 규칙에선 빼도 같았음)를 지금 규칙(새 82)에서 다시.
한도 2 · 3 · 4 · 그리고 닷새에 4종목까지(per_window). 기준 = 새 82회차 · 씨앗 8."""
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T

print("== 일봉 새 93회차: 하루 새로 사는 수 ==", flush=True)
T.once("기준(한도 없음)")
for n in (2, 3, 4):
    T.once(f"하루 {n}종목까지", per_day=n)
T.once("닷새에 4종목까지", per_window=(4, 5))
print("끝", flush=True)
