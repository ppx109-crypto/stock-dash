# 설명용(공개): 씨앗 0 판의 해마다 수익률(달력 연도 · NAV 복리) — 지금 규칙(장치 없음) · H3 × 1.0 · × 1.5 · × 2.0
import sys; sys.path.insert(0, "/home/user/stock-dash"); sys.path.insert(0, "/home/user/stock-dash/research")
import z078, z080
for which in ("앞", "뒤"):
    g = z078.ledgers(which)[0]
    for name, kw in (("장치 없음", {}), ("×1.0", {"cap": .4, "vol": z080.VOL_DAY}), ("×1.5", {"cap": .4, "vol": z080.VOL_DAY * 1.5}), ("×2.0", {"cap": .4, "vol": z080.VOL_DAY * 2})):
        _, navs = z080.account(g["led"], g["still"], g["since"], g["end"], want_navs=True, **kw)
        ends = {}
        for d, v in navs:
            ends[d[:4]] = v
        prev, row = 1.0, []
        for y in sorted(ends):
            row.append(f"{y} {((ends[y] / prev) - 1) * 100:+.0f}%"); prev = ends[y]
        print(f"[{which}] {name}: " + " · ".join(row) + f" · 기간 {navs[0][0]}~{navs[-1][0]} · 끝 {navs[-1][1]:.2f}배", flush=True)
