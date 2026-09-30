"""1시간봉 42회차(확인 줄) — '시장 폭이 낮은 날만 150위로 넓히기'의 문턱 고원(41회차: 폭<70 좋음 · 폭<60 나쁨 → 고원인지 의심).
문턱 50 · 60 · 65 · 70 · 75 · 80 · 늘(100) × 지금 규칙 / 자리 바꾸기, 씨앗 16. 시장 폭은 전 거래일 값."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
stale = lambda p: (p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
IN100 = IN
UW = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=150)
INW = {c: np.array([UW.ok(c, t) for t in data[c]["t"]]) for c in data}
print("== 1시간봉 42회차 (폭 낮은 날 150위 · 문턱 고원 · 씨앗 16) ==", flush=True)
for th in (0, 50, 60, 65, 70, 75, 80, 101):
    IN = {c: np.where(np.array([bool(x) and (x["시장폭"] if x["시장폭"] is not None else 100) < th for x in ATT[c]]), INW[c], IN100[c]) for c in data}
    for tag, st in (("지금 규칙", None), ("자리 바꾸기", stale)):
        res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st, seeds=16)
        name = "100위(넓히지 않음)" if th == 0 else "늘 150위" if th == 101 else f"폭<{th}이면 150위"
        print(f"  {f'{name} · {tag}':26s} " + H.line(res), flush=True)
print("끝", flush=True)
