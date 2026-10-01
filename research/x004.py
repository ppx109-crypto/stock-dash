"""호환 점검 C1 · C2 — 세 갈래 규칙의 매매 겹침과 주마다 확정 손익의 상관(같은 기간 2025-09-17 ~ 2026-08-31).
Q_PART=m15(15분봉 22회차 후보 · 0회차, 한투 15분봉) · h1k(1시간봉 94회차, 한투 15분봉을 1시간으로) · h1y(1시간봉 94회차, 야후 1시간봉) · d1(1일봉 새 82회차) → 매매 목록을 파일로
Q_PART=join → 겹침 표 · 주 손익 상관 · 나눠 굴린 계좌(같은 몫씩)의 합 · 가장 나쁜 주."""
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
OUT = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/x004_"
LO, HI = "20250917", "20260831"
part = os.environ.get("Q_PART", "join")


def dump(name, rows):
    json.dump(rows, open(OUT + name + ".json", "w"))
    print(name, len(rows), "건", flush=True)


if part == "m15":
    exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('\npart = os.environ')[0])
    for name, fn in (("m15_final", entry3(al_mkt=-0.01)), ("m15_base", entry())):
        sg = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
        res = M.simulate(data, lambda c, b: sg[c], exit_rule, size, rank=rank_plus(tiers(sg)), stale_of=stale90, seeds=1)
        dump(name, [(t["code"], t["산 때"][:8], t["판 때"].lstrip("끝")[:8], t["손익"], t["칸"]) for s in ("앞", "뒤") for t in res[s]["목록"]])
elif part == "h1k":
    os.environ["Q_BARS"] = "1h"
    exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
    res = M.simulate(data, lambda c, b: SIGS[c], exit_rule, size, rank=RANK, stale_of=stale90, seeds=1)
    dump("h1k", [(t["code"], t["산 때"][:8], t["판 때"].lstrip("끝")[:8], t["손익"], t["칸"]) for s in ("앞", "뒤") for t in res[s]["목록"]])
elif part == "h1y":
    exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
    PER = (("기간", ("2025091700", "2026090100")),)
    sigs = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
    KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
    r = H._one_run(data, sigs, EX, size, PER[0][1][0], PER[0][1][1], 10, 0, None, rk_of(tiers(20, 5, 3)), H.COST, None, None, stale90)
    dump("h1y", [(t["code"], t["산 때"][:8], t["판 때"].lstrip("끝")[:8], t["손익"], t["칸"]) for t in r["목록"]])
elif part == "d1":
    import ntools as T
    got = T.once("일봉 새 82회차")
    dump("d1", [(t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for s in ("앞", "뒤") if got.get(s)
                for t in got[s]["매매목록"] if LO <= t["산 날"] <= HI])
else:
    from datetime import date
    import numpy as np
    names = ("m15_final", "m15_base", "h1k", "h1y", "d1")
    R = {n: [r for r in json.load(open(OUT + n + ".json")) if LO <= r[1] <= HI] for n in names}
    D = lambda s: date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    print("== 호환 점검 C1: 매매 겹침(같은 종목 · 산 날 앞뒤 7일 안) — 줄 규칙의 매매 가운데 칸 규칙도 산 몫 ==")
    print("  " + " " * 10 + "".join(f"{n:>11}" for n in names))
    for a in names:
        line = []
        for b in names:
            pool = {}
            for r in R[b]:
                pool.setdefault(r[0], []).append(D(r[1]))
            hit = sum(1 for r in R[a] if any(abs((D(r[1]) - x).days) <= 7 for x in pool.get(r[0], [])))
            line.append(f"{hit / max(1, len(R[a])) * 100:10.0f}%")
        print(f"  {a:10s}" + "".join(line) + f"  ({len(R[a])}건)")
    wk = lambda s: D(s).isocalendar()[:2]
    weeks = sorted({wk(r[2]) for n in names for r in R[n]})
    W = {n: np.array([sum(r[3] * r[4] / 10 for r in R[n] if wk(r[2]) == w) for w in weeks]) for n in names}
    print("== C2: 주마다 확정 손익(계좌 몫 %)의 상관 ==")
    for a in names:
        print(f"  {a:10s}" + "".join(f"{np.corrcoef(W[a], W[b])[0, 1]:11.2f}" for b in names))
    print("== C2: 나눠 굴린 계좌(같은 몫씩 · 확정 손익 기준 어림) ==")
    for combo in (("d1",), ("h1y",), ("h1k",), ("m15_final",), ("d1", "h1y"), ("d1", "h1k"), ("d1", "h1k", "m15_final"), ("d1", "h1y", "m15_final")):
        w = sum(W[n] for n in combo) / len(combo)
        eq = np.cumsum(w)
        dd = float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min())
        print(f"  {' + '.join(combo):28s} 합 {w.sum():+7.1f}% · 가장 나쁜 주 {w.min():+6.1f}% · 확정 손익 골 {dd:+6.1f}%")
