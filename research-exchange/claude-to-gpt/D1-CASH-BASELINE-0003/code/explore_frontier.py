# 탐색(채택 근거 아님 · 공개): H3 흔들림 상한을 1.5배 · 2배로 넓히면 수익 · 손실이 어떻게 바뀌나. 뒤 반을 이미 본 뒤의 탐색이라 고르는 데 쓰지 않음.
import sys; sys.path.insert(0, "/home/user/stock-dash"); sys.path.insert(0, "/home/user/stock-dash/research")
import z078, z080
for which in ("앞", "뒤"):
    gs = z078.ledgers(which)
    for m in (1.5, 2.0):
        xs = [z080.account(g["led"], g["still"], g["since"], g["end"], cap=z080.CAP, vol=z080.VOL_DAY * m) for g in gs]
        c = sorted(x["cagr"] for x in xs)
        print(f"[{which}] 상한 ×{m} 연복리 가운데 {c[len(c)//2]} · 하루 최악 {min((x['worst_day'] for x in xs), key=lambda v: v[1])} · "
              f"달 최악 {min((x['worst_month'] for x in xs), key=lambda v: v[1])} · 고점 대비 {min((x['mdd_daily'] for x in xs), key=lambda v: v[1])}", flush=True)
