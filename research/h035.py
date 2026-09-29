"""1시간봉 35회차(탐색 줄) — 자리 바꾸기 다듬기: 무엇을 비키고 무엇이 밀어낼 수 있나.
31회차 고원(7 ~ 10봉 · +2 ~ 5%)에서 7봉 · <4%와 10봉 · <4%로:
① 비킬 것 = 묵음 + **그 종목 재료가 꺼짐**(전 거래일 기준 A그룹 꼴 + 가르침이 더는 아님) ② 비킬 것 = 묵음 + 재료 아직 켜짐(대조)
③ 밀어낼 수 있는 새 매수 = 센 것(4칸: 추세 문 또는 3일 연속)만 ④ 추세 문 새 매수만.
판단은 모두 전 봉까지 값(재료는 전 거래일)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
def stale(n, x, ctx=None):
    def f(p):
        if not ((p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x): return False
        if ctx is None: return True
        on = bool(ok(ATT[p["code"]][p["now"]]))
        return (not on) if ctx == "꺼짐" else on
    return f
strong_new = lambda c, b, k: size(c, b, k) == 4
def trend_new(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    return bool(x and x["추세문"])
print("== 1시간봉 35회차 (자리 바꾸기 다듬기) ==", flush=True)
print(f"  {'지금':28s} " + H.line(H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)), flush=True)
for n in (7, 10):
    for tag, st, bp in (("묵음(31회차)", stale(n, 4), None), ("묵음 + 재료 꺼짐", stale(n, 4, "꺼짐"), None),
                        ("묵음 + 재료 켜짐", stale(n, 4, "켜짐"), None), ("센 새 매수만 밀어냄", stale(n, 4), strong_new),
                        ("추세 문 새 매수만 밀어냄", stale(n, 4), trend_new)):
        res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st, bumps=bp)
        mv = {s: sum(1 for t in res[s]["목록"] if t["비킴"]) for s in ("앞", "뒤")}
        print(f"  {f'{n}봉 · <4% · {tag}':28s} " + H.line(res) + f" · 비킨 {mv}", flush=True)
print("끝", flush=True)
