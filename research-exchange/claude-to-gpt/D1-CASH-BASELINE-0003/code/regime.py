# 설명용(공개 · 고르기에 안 씀): 씨앗 0 판 NAV를 달마다 → 코스피 그 달 등락으로 상승(>+3%) · 횡보(−3~+3%) · 하락(<−3%) 나눠 장별 연 환산 수익
import json, sys; sys.path.insert(0, "/home/user/stock-dash"); sys.path.insert(0, "/home/user/stock-dash/research")
import z078, z080
k = json.load(open("/home/user/stock-dash/market-data/index_KOSPI.json"))["rows"]
kc = {}
for r in k: kc[r["date"][:6]] = r["종가"]
def monthly(navs):
    end = {}
    for d, v in navs: end[d[:6]] = v
    ms = sorted(end); out = {}; prev = 1.0
    for m in ms: out[m] = end[m] / prev - 1; prev = end[m]
    return out
VAR = (("장치 없음", {}), ("×2.0", {"cap": .4, "vol": z080.VOL_DAY * 2}), ("×1.5", {"cap": .4, "vol": z080.VOL_DAY * 1.5}), ("×1.0", {"cap": .4, "vol": z080.VOL_DAY}))
rets = {n: {} for n, _ in VAR}
for which in ("앞", "뒤"):
    g = z078.ledgers(which)[0]
    for n, kw in VAR:
        _, navs = z080.account(g["led"], g["still"], g["since"], g["end"], want_navs=True, **kw)
        rets[n].update(monthly(navs))
ms = sorted(rets["장치 없음"])
km = {}
prevk = None
for m in sorted(kc):
    if prevk: km[m] = kc[m] / kc[prevk] - 1
    prevk = m
km["201701"] = kc["201701"] / 2026.16 - 1
reg = {m: ("상승" if km[m] > .03 else "하락" if km[m] < -.03 else "횡보") for m in ms}
def ann(xs):
    p = 1.0
    for x in xs: p *= 1 + x
    return (p ** (12 / len(xs)) - 1) * 100 if xs else float("nan")
print("기간", ms[0], "~", ms[-1], "· 달 수", len(ms))
for g in ("상승", "횡보", "하락"):
    sel = [m for m in ms if reg[m] == g]
    line = f"[{g}장 {len(sel)}달 · 코스피 연 환산 {ann([km[m] for m in sel]):+.0f}%] "
    for n, _ in VAR:
        xs = [rets[n][m] for m in sel]
        line += f"{n}: 연 {ann(xs):+.0f}% · 오른 달 {sum(x > 0 for x in xs)}/{len(xs)} · 최악 달 {min(xs)*100:+.1f}% | "
    print(line)
full = "[전체 9년 9개월] " + " | ".join(f"{n}: 연 {ann([rets[n][m] for m in ms]):+.1f}%" for n, _ in VAR) + f" | 코스피: 연 {ann([km[m] for m in ms]):+.1f}%"
print(full)
print("[해마다 코스피] " + " · ".join(f"{y} {((kc[max(m for m in kc if m.startswith(y))] / (kc[max(m for m in kc if m.startswith(str(int(y)-1)))] if y != '2017' else 2026.16)) - 1)*100:+.0f}%" for y in sorted({m[:4] for m in ms})))
