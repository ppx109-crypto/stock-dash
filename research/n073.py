"""일봉 새 73회차 — 표(guard.py가 검사하는 일봉 특징) 안의 모양 재료로 같은 날 후보 순서(35회차에 안 본 것).

전고점 거리(250 · 120일) · 거래량비 · 밴드 폭(조임) · 추세 가속도 · 정배열일수 · 장기 기울기를 같은 날 후보끼리 3무리로 나눠
좋은 쪽 먼저(양쪽 방향 모두), 같으면 180일선 기울기. 밀린 매매 손익을 직접 봄.
실행: NRL_CACHE=... python3 research/n073.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T

print("== 일봉 새 73회차: 표 안 모양 재료로 같은 날 순서 ==", flush=True)
base = T.once("지금: 180일선 기울기 순")
best = []
for key, label in (("250일 전고점 대비", "250일 전고점에 가까운"), ("120일 전고점 대비", "120일 전고점에 가까운"),
                   ("거래량비", "거래량 많은"), ("밴드 폭", "밴드 넓은"), ("추세 가속도", "추세 가속 큰"),
                   ("정배열일수", "정배열 오래된"), ("장기 기울기", "장기 기울기 큰")):
    for low, way in ((False, label), (True, label.replace("가까운", "먼").replace("많은", "적은").replace("넓은", "좁은")
                                       .replace("큰", "작은").replace("오래된", "막 된"))):
        got = T.once(f"순서: {way} 것 먼저", rank=T.rank_by([(lambda r, k=key: r.get(k), low)]))
        if got.get("앞") and got.get("뒤"):
            best.append((got["앞"]["연수익"] - base["앞"]["연수익"] + (got["뒤"]["연수익"] - base["뒤"]["연수익"]) / 4, way, got))
best.sort(key=lambda x: -x[0])
for score, way, got in best[:2]:
    print(f"  ▶ 상위: {way} → 해마다 {T.years(got)}", flush=True)
    T.diff_check(base, got)
print("끝", flush=True)
