"""1시간봉 120회차(세 갈래 공통 G10 · 1시간봉) — 하루에 새로 사는 종목 수 한도 2 · 3 · 4(지금은 없음 · research/kinpatch.set_daycap).
12:00 묶음처럼 한날에 몰아 사는 것을 나누면 나은가. 기준 = 94회차 · 씨앗 16 · Q_SRC=yahoo · kis."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/h116.py", encoding="utf-8").read().split("\nVOL, RUN = {}, {}")[0])
import kinpatch as KP

rk = RK(SG)
print(f"== 1시간봉 120회차(G10 하루 새로 사는 수 · {src} · {len(data)}종목) ==", flush=True)


def book(res):
    """반마다 하루에 새로 산 종목 수의 나눔(씨앗 0)."""
    out = []
    for side in ("앞", "뒤"):
        days = {}
        for t in (res.get(side) or {}).get("목록", []):
            if not t.get("나눠"):
                days.setdefault(t["산 때"][:8], set()).add(t["code"])
        n = [len(v) for v in days.values()]
        out.append(f"{side} 산 날 {len(n)} · 하루 1 {sum(x == 1 for x in n)} · 2 {sum(x == 2 for x in n)} · 3↑ {sum(x >= 3 for x in n)}")
    return " / ".join(out)


for cap in (None, 2, 3, 4):
    KP.set_daycap(cap)
    res = SIM(data, lambda c, b: SG[c], EXF, size, rank=rk, stale_of=stale90, seeds=16)
    tag = "기준(한도 없음)" if cap is None else f"하루 {cap}종목까지"
    print(f"  {tag:24s} " + H.line(res), flush=True)
    if cap is None:
        print("    " + book(res), flush=True)
print("끝", flush=True)
