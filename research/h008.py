"""1시간봉 8회차(확인 줄) — 약한 장 표본 늘리기: 종목 모음을 시총 100위 → 150위로 넓혀 5회차의 '약한 장에서 흔들림'을 다시 봄.
(일봉 규칙은 100위 안이지만, 여기선 사는 때 비교의 표본을 늘리려는 확인용. 넓힌 모음 자체의 성적도 함께 봄.)
사는 때: 아침 09시 시가(= 일봉 신호 다음 날) vs 후보(1시간봉 A 정배열 된 봉 다음, 없으면 12시) · 자리 8 · 10 · 12."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
src = open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0]
src = src.replace("uni = H.Universe({d: v for d, v in ranks.items() if d >= \"20230801\"}, top=100)",
                  "uni = H.Universe({d: v for d, v in ranks.items() if d >= \"20230801\"}, top=150)")
assert "top=150" in src
exec(src)

print("== 1시간봉 8회차 (확인: 150위까지 넓혀 사는 때 비교) ==", flush=True)
for slots in (8, 10, 12):
    for tag, e in (("아침 09시 시가", e_morning), ("후보(정배열, 없으면 12시)", e_align_or_noon)):
        res = H.simulate(data, e, exit_daily, size, rank=rank, slots=slots)
        print(f"  자리 {slots:>2} · {tag:22s} " + H.line(res), flush=True)
print("끝", flush=True)
