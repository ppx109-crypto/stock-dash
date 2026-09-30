"""1시간봉 49회차(확인 줄) — 자리 바꾸기를 하루 중 언제 허락하나(장 시작/마감 시간대).
38회차: 야후 09시 시가는 ±1% 흔들림 · 새 매수 대부분이 09시(전날 신호) 또는 12시(11시 봉 신호). 비킴은 새 매수와 같은 봉 시가에 일어남.
① 새 매매(자리 바꾸기로 새로 생긴 것)의 산 시각별 손익 ② 비킴을 09시에만 · 09시 빼고 · 12시 뒤에만 허락(bumps: 새 매수 봉 시각으로)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
stale = lambda p: (p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
def at_hours(hs):
    return lambda c, b, k: k + 1 < len(b["t"]) and b["t"][k + 1][8:] in hs
print("== 1시간봉 49회차 (자리 바꾸기를 언제 허락하나) ==", flush=True)
base = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)
swap = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=stale)
for s in ("앞", "뒤"):
    kb = {(t["code"], t["산 때"]) for t in base[s]["목록"]}
    g, m = {}, {}
    for t in swap[s]["목록"]:
        h = t["산 때"][8:]
        (g if (t["code"], t["산 때"]) not in kb else m).setdefault(h, []).append(t["손익"])
    print(f"  {s} 새 매매(바꾸기로 생김) 산 시각별: " + " · ".join(f"{h}시 {len(v)}건 {np.mean(v):+.2f}%" for h, v in sorted(g.items())), flush=True)
    mv = {}
    for t in swap[s]["목록"]:
        if t["비킴"]: mv.setdefault(t["판 때"][8:], []).append(t["손익"])
    print(f"  {s} 비킨 매매 판 시각별: " + " · ".join(f"{h}시 {len(v)}건 {np.mean(v):+.2f}%" for h, v in sorted(mv.items())), flush=True)
print(f"  {'지금 규칙':22s} " + H.line(base), flush=True)
print(f"  {'바꾸기(늘 허락)':22s} " + H.line(swap), flush=True)
for tag, hs in (("09시에만", {"09"}), ("09시 빼고", {"10", "11", "12", "13", "14"}), ("12시 뒤에만", {"12", "13", "14"}), ("09 · 12시만", {"09", "12"})):
    res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=stale, bumps=at_hours(hs))
    print(f"  {f'바꾸기 {tag}':22s} " + H.line(res), flush=True)
print("끝", flush=True)
