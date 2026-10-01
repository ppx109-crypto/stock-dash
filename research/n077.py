"""일봉 새 77회차(셈만) — 일봉 최고 규칙을 '매매가 끝날 때마다 바뀐 시드로' 굴린 계좌(사용자 질문 · 1시간봉 98회차와 같은 셈).

산 날 그때 시드(현금 + 들고 있는 매매의 산 값)의 칸/10을 넣고, 판 돈은 바로 시드에 더해 다음 매매 크기에 씀. 1,000만 원 시작.
"""
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import lab
import nrl
import rule
START = 1000.0


def path(ledger, simple=False):
    pos = {}
    for t in ledger:
        key = (t["code"], t["산 날"])
        pos[key] = pos.get(key, 0) + t["자리"]
    ev = [(k[1], 1, "buy", k, None) for k in pos] + [(t["판 날"], 0, "sell", (t["code"], t["산 날"]), t) for t in ledger]
    ev.sort(key=lambda e: (e[0], e[1]))
    cash, book, alloc, out = START, {}, {}, []
    for when, _, kind, key, t in ev:
        if kind == "buy":
            seed = START if simple else cash + sum(book.values())
            put = seed / 10 * pos[key] if simple else min(seed / 10 * pos[key], cash)
            alloc[key] = put / pos[key]
            book[key] = put
            cash -= put
        else:
            money = alloc[key] * t["자리"]
            cash += money * (1 + t["손익"] / 100)
            book[key] -= money
            if book[key] <= 1e-9:
                book.pop(key)
            out.append((when, cash + sum(book.values())))
    return out


print("== 일봉 새 77회차: 매매마다 바뀐 시드로 굴린 계좌(1,000만 원 시작 · 만 원 · 씨앗 0) ==", flush=True)
for side, pool, since in (("2017 ~ 2020", nrl.early, rule.SINCE), ("2021 ~ 2026-09", nrl.inside, rule.MID), ("2017 ~ 2026-09 한 번에", nrl.inside, rule.SINCE)):
    g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=since,
                apart=nrl.kin, realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE)
    p, ps = path(g["매매목록"]), path(g["매매목록"], simple=True)
    years = {}
    for d, v in p:
        years[d[:4]] = v
    peak, dd = START, 0.0
    for _, v in p:
        peak = max(peak, v)
        dd = min(dd, (v / peak - 1) * 100)
    print(f"  {side}: 매매 {len(g['매매목록'])}건 · 끝 시드 {p[-1][1]:,.0f}만 원 · 시드 고정(단리)이면 {ps[-1][1]:,.0f}만 원 · 시드 꼭대기에서 가장 크게 줄어든 몫 {dd:.1f}%", flush=True)
    print("      해 끝 시드: " + " · ".join(f"{y} {v:,.0f}" for y, v in years.items()), flush=True)
print("끝", flush=True)
