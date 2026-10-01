"""호환 점검 C4 — 모의투자 한 계좌(1시간봉 · 1일봉이 반씩)에서 두 규칙이 ① 같은 종목을 같은 날 함께 들고 있는 일 ② 같은 날 한쪽은 사고 한쪽은 파는 일.
같은 기간(2025-09-17 ~ 2026-08-31) 연구 매매 목록(x004: 1일봉 d1 · 1시간봉 한투 h1k · 야후 h1y)으로 어림. 날 단위."""
import json
from datetime import date, timedelta
OUT = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/x004_"
D = lambda s: date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def held_days(rows):
    got = {}
    for code, a, z, *_ in rows:
        d = D(a)
        while d <= D(z):
            if d.weekday() < 5:
                got.setdefault((code, d), 0)
                got[(code, d)] += 1
            d += timedelta(days=1)
    return got


d1 = json.load(open(OUT + "d1.json"))
print("== 호환 점검 C4: 한 계좌 안 두 규칙의 겹침 ==")
for name in ("h1k", "h1y"):
    h1 = json.load(open(OUT + name + ".json"))
    A, B = held_days(d1), held_days(h1)
    both = set(A) & set(B)
    days = {d for _, d in set(A) | set(B)}
    buy_d = {(c, D(a)) for c, a, *_ in d1}
    sell_d = {(c, D(z)) for c, a, z, *_ in d1}
    buy_h = {(c, D(a)) for c, a, *_ in h1}
    sell_h = {(c, D(z)) for c, a, z, *_ in h1}
    opp = (buy_d & sell_h) | (sell_d & buy_h)
    same_buy = buy_d & buy_h
    print(f"  1일봉 + 1시간봉({'한투' if name == 'h1k' else '야후'}): 같은 종목을 함께 든 종목·날 {len(both)} (두 규칙이 든 종목·날의 {len(both) / max(1, len(set(A) | set(B))) * 100:.0f}%) · "
          f"같은 날 같은 종목 둘 다 삼 {len(same_buy)}번 · 같은 날 한쪽 사고 한쪽 팖 {len(opp)}번 (매매 1일봉 {len(d1)} · 1시간봉 {len(h1)})")
print("끝")
