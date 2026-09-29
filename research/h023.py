"""1시간봉 23회차 — 두 자금 나눔: 긴 판(지금 규칙) X% + 짧은 판 B(센 재료만 · 반 +8% 지정가 · 반 20봉선 따라가기 · −5%) (100−X)%.
16회차(한 계좌에서 섞기)는 센 재료 매매를 짧게 잘라 이익을 잃었음 → 이번엔 **두 계좌를 따로** 굴려 날마다 합침(hlab.blend).
짧은 판 B는 긴 판과 같은 종목을 동시에 살 수 있음(따로 굴리는 두 계좌). 연 = 복리 없는 한 해 몫 · 골 = 합친 계좌 꼭대기 대비."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h021.py", encoding="utf-8").read().split('print("== 1시간봉 21회차')[0])

long_res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)
short_res = H.simulate(data, entry(), exit_trail, four, rank=rank, take_of=take_half, stop_of=stop5)
print("== 1시간봉 23회차 (두 자금 나눔: 긴 판 + 짧은 판 B) ==", flush=True)
print(f"  긴 판만   " + H.line(long_res), flush=True)
print(f"  짧은 판 B만 " + H.line(short_res), flush=True)
for w in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.0):
    parts = []
    for side in ("앞", "뒤"):
        pa = [(w, long_res[side]), (1 - w, short_res[side])]
        r = H.blend([p for p in pa if p[0] > 0])
        parts.append(f"{side} 연 {r['연']:>7} 골 {r['골']:>6}")
    print(f"  긴 판 {int(w * 100):>3}% + 짧은 판 {int((1 - w) * 100):>3}% (씨앗 0) · " + " | ".join(parts), flush=True)
print("끝", flush=True)
