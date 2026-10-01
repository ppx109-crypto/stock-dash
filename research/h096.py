"""1시간봉 96회차 — 최고 규칙(90회차 · 94회차 최종)을 복리로 다시 셈(사용자 2026-10-01: "연 +39.2%가 단리인데 복리라면?").

엔진(hlab)의 '연'은 칸 크기를 처음 자금으로 고정한 단리(번 돈을 다시 굴리지 않음). 같은 매매 목록(씨앗 16)을 그대로 두고,
산 때마다 '그때 계좌 값(현금 + 들고 있는 매매의 산 값)'의 칸/10을 넣는 복리 계좌로 다시 굴림. 같은 시각엔 팔기 먼저.
남은 현금보다 많이 넣지 않음(빚 없음). 하루 끝 평가로 골도 다시 셈.
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h094.py", encoding="utf-8").read().split('print("== 1시간봉 94회차')[0])
RK = rk_of(tiers(20, 5, 3))


def compound(ledger, days):
    """매매 목록 → (끝 계좌 배수, 하루 끝 계좌 값 목록으로 잰 골%)."""
    pos = {}
    for t in ledger:
        key = (t["code"], t["산 때"])
        pos.setdefault(key, {"칸": 0, "parts": []})
        pos[key]["칸"] += t["칸"]
        pos[key]["parts"].append(t)
    ev = []
    for key, p in pos.items():
        ev.append((key[1], 1, "buy", key))
        for t in p["parts"]:
            ev.append((t["판 때"].replace("끝", ""), 0, "sell", key, t))
    ev.sort(key=lambda e: (e[0], e[1]))
    cash, book, alloc = 1.0, {}, {}
    marks, last = [], None
    for e in ev:
        day = e[0][:8]
        if last and day != last:
            marks.append(cash + sum(book.values()))
        last = day
        if e[2] == "buy":
            key = e[3]
            per = (cash + sum(book.values())) / 10
            n = pos[key]["칸"]
            put = min(per * n, cash)
            alloc[key] = put / n
            book[key] = put
            cash -= put
        else:
            key, t = e[3], e[4]
            money = alloc[key] * t["칸"]
            cash += money * (1 + t["손익"] / 100)
            book[key] -= money
            if book[key] <= 1e-12:
                book.pop(key)
    marks.append(cash + sum(book.values()))
    eq = np.array(marks)
    return float(eq[-1]), float(((eq / np.maximum.accumulate(eq)) - 1).min() * 100)


print("== 1시간봉 96회차: 최고 규칙 단리 vs 복리 (씨앗 16) ==", flush=True)
for s, (lo, hi) in (("앞(2023-10 ~ 2025-03)", H.EARLY), ("뒤(2025-04 ~ 2026-09)", H.LATE)):
    simple, comp, cagr, dd_s, dd_c = [], [], [], [], []
    for seed in range(16):
        r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, RK, H.COST, None, None, stale90)
        years = max(len(r["곡선"]) / 245, 0.25)
        end, dd = compound(r["목록"], years)
        simple.append(r["연"]); dd_s.append(r["골"])
        comp.append(end); dd_c.append(dd)
        cagr.append((end ** (1 / years) - 1) * 100)
    m = lambda v: round(float(np.median(v)), 2)
    print(f"  {s}: 기간 {years:.2f}년 · 단리 연 {m(simple)}%(골 {m(dd_s)}) → 복리 끝 {m(comp)}배 · 복리 연 {m(cagr)}%(골 {m(dd_c)}) "
          f"· 씨앗 폭 복리 연 {round(min(cagr), 1)} ~ {round(max(cagr), 1)}", flush=True)
print("끝", flush=True)
