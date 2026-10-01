"""1시간봉 98회차 — 최고 규칙을 '매매가 끝날 때마다 바뀐 시드로' 굴린 계좌(사용자 2026-10-01: 연복리가 아니라 거래마다 시드가 커지거나 작아지는 복리).

96회차와 같은 계좌 셈(산 때 그때 시드(현금 + 들고 있는 매매의 산 값)의 칸/10을 넣음 · 판 돈은 바로 시드에 더해 다음 매매 크기에 씀)을
1,000만 원으로 시작해 석 달마다 잔고 · 끝 잔고로 보임. 씨앗 16의 가운데 끝 잔고를 낸 판을 보여 줌. 단리(시드 고정)도 나란히.
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h096.py", encoding="utf-8").read().split('print("== 1시간봉 96회차')[0])
START = 1000.0     # 만 원


def path(ledger, simple=False):
    """매매 목록 → [(날, 시드)]: 매매가 끝날 때마다 바뀐 시드."""
    pos = {}
    for t in ledger:
        key = (t["code"], t["산 때"])
        pos.setdefault(key, {"칸": 0})
        pos[key]["칸"] += t["칸"]
    ev = []
    for key in pos:
        ev.append((key[1], 1, "buy", key, None))
    for t in ledger:
        ev.append((t["판 때"].replace("끝", ""), 0, "sell", (t["code"], t["산 때"]), t))
    ev.sort(key=lambda e: (e[0], e[1]))
    cash, book, alloc, out = START, {}, {}, []
    for when, _, kind, key, t in ev:
        if kind == "buy":
            seed = START if simple else cash + sum(book.values())
            n = pos[key]["칸"]
            put = seed / 10 * n if simple else min(seed / 10 * n, cash)
            alloc[key] = put / n
            book[key] = put
            cash -= put
        else:
            money = alloc[key] * t["칸"]
            cash += money * (1 + t["손익"] / 100)
            book[key] -= money
            if book[key] <= 1e-9:
                book.pop(key)
            out.append((when[:8], cash + sum(book.values())))
    return out


print("== 1시간봉 98회차: 매매마다 바뀐 시드로 굴린 계좌(1,000만 원 시작 · 만 원) ==", flush=True)
for s, (lo, hi) in (("앞(2023-10 ~ 2025-03)", H.EARLY), ("뒤(2025-04 ~ 2026-09)", H.LATE)):
    runs = [H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, RK, H.COST, None, None, stale90) for seed in range(16)]
    paths = [path(r["목록"]) for r in runs]
    ends = [p[-1][1] for p in paths]
    k = int(np.argsort(ends)[len(ends) // 2])
    p, ps = paths[k], path(runs[k]["목록"], simple=True)
    print(f"  {s}: 매매 {len(runs[k]['목록'])}건 · 끝 시드 {ends[k]:,.0f}만 원(씨앗 16: {min(ends):,.0f} ~ {max(ends):,.0f}) · 시드 고정(단리)이면 {ps[-1][1]:,.0f}만 원", flush=True)
    marks, seen = [], set()
    for d, v in p:
        q = d[:4] + ("1" if d[4:6] <= "03" else "2" if d[4:6] <= "06" else "3" if d[4:6] <= "09" else "4")
        if q not in seen:
            seen.add(q)
        marks = [m for m in marks if m[0] != q] + [(q, v)]
    print("      석 달 끝 시드: " + " · ".join(f"{q[:4]}년 {q[4]}분기 {v:,.0f}" for q, v in marks), flush=True)
    low = min(v for _, v in p)
    peak, dd = START, 0.0
    for _, v in p:
        peak = max(peak, v)
        dd = min(dd, (v / peak - 1) * 100)
    print(f"      가장 낮았던 시드 {low:,.0f}만 원 · 시드 꼭대기에서 가장 크게 줄어든 몫 {dd:.1f}%(매매가 끝난 때 기준)", flush=True)
print("끝", flush=True)
