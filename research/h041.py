"""1시간봉 41회차(확인 줄) — 약한 장에서만 종목 넓히기(11 · 12회차 관찰 후보: 전날 시장 폭 < 70%면 150위) + 자리 바꾸기.
33회차: 101~150위 매매는 약한 장(앞) +4.2% · 센 장(뒤) −0.4%. → 시장 폭이 낮은 날만 모음을 넓히면 두 반 모두 좋을까.
넓히는 크기 150 · 200 · 300위 × 시장 폭 문턱 60 · 70% × 지금 규칙 / 자리 바꾸기. 시장 폭은 전 거래일 값(hlab 재료 '시장폭')."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
stale = lambda p: (p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
IN100 = IN
print("== 1시간봉 41회차 (약한 장에서만 넓히기 + 자리 바꾸기) ==", flush=True)
for tag, st in (("지금 규칙", None), ("자리 바꾸기", stale)):
    IN = IN100
    print(f"  {f'100위 · {tag}':26s} " + H.line(H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st)), flush=True)
for wide in (150, 200, 300):
    UW = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=wide)
    INW = {c: np.array([UW.ok(c, t) for t in data[c]["t"]]) for c in data}
    for th in (60, 70):
        IN = {}
        for c in data:
            weak = np.array([bool(x) and (x["시장폭"] if x["시장폭"] is not None else 100) < th for x in ATT[c]])
            IN[c] = np.where(weak, INW[c], IN100[c])
        for tag, st in (("지금 규칙", None), ("자리 바꾸기", stale)):
            res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st)
            print(f"  {f'폭<{th}이면 {wide}위 · {tag}':26s} " + H.line(res), flush=True)
            print(f"      반기(씨앗 0): 앞 {res['앞']['반기']} · 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
