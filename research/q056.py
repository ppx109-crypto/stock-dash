"""15분봉 56회차(세 갈래 공통 G10 · 15분봉) — 하루에 새로 사는 종목 수 한도 2 · 3 · 4(지금은 없음 · research/kinpatch.set_daycap).
기준 = 22회차 후보 · 160종목 · 씨앗 16 · 두 반."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
import kinpatch as KP

print(f"== 15분봉 56회차: 하루 새로 사는 수 ({len(data)}종목) ==", flush=True)
for cap in (None, 2, 3, 4):
    KP.set_daycap(cap)
    res = M.simulate(data, lambda c, b: SGF[c], exit_rule, size, rank=RKF, stale_of=stale90, seeds=16)
    tag = "기준(한도 없음)" if cap is None else f"하루 {cap}종목까지"
    print(f"  {tag:24s} " + H.line(res), flush=True)
print("끝", flush=True)
