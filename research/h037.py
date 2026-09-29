"""1시간봉 37회차(확인 줄) — '조용함' 문턱을 지난 자료로만 정하도록 고친 뒤(미래 참조 제거) 지금 규칙 · 자리 바꾸기 · 짧은 판 B 다시 재기.
예전 문턱은 전체 기간(2017~2026) 표의 아래 40% 자리 하나 → 2024년 판단에 2026년 변동성이 섞였음. 이제 달마다 그 달 앞 자료로만."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h021.py", encoding="utf-8").read().split('print("== 1시간봉 21회차')[0])
def stale(n, x):
    return lambda p: (p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x
print("== 1시간봉 37회차 (문턱 고친 뒤 다시 재기, 씨앗 16) ==", flush=True)
print("  추세 문 날 수(종목 · 날):", len(trend), flush=True)
for tag, kw in (("지금 규칙", dict(entry=e_align_or_noon, exit_rule=exit_daily, size=size, rank=rank)),
                ("자리 바꾸기 7봉 · <4%", dict(entry=e_align_or_noon, exit_rule=exit_daily, size=size, rank=rank, stale_of=stale(7, 4))),
                ("자리 바꾸기 10봉 · <4%", dict(entry=e_align_or_noon, exit_rule=exit_daily, size=size, rank=rank, stale_of=stale(10, 4))),
                ("짧은 판 B", dict(entry=entry(), exit_rule=exit_trail, size=four, rank=rank, take_of=take_half, stop_of=stop5))):
    e = kw.pop("entry")
    res = H.simulate(data, e, seeds=16, **kw)
    print(f"  {tag:22s} " + H.line(res), flush=True)
    print(f"      반기(씨앗 0): 앞 {res['앞']['반기']} · 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
