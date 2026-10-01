"""탄력 배분 시험(사용자 2026-10-02): "1일봉 매수가 줄면 하락장으로 보고 15분봉(짧은 갈래) 거래를 줄이고,
1일봉 매수가 늘어난 상승장이면 1일봉 거래를 줄이는" 식으로 갈래마다 돈 몫을 그때그때 바꾸면 나은가.
- 장세 잣대 S(날) = 그날 '앞' 20거래일 동안 1일봉 규칙이 새로 산 수(그날 값은 안 씀 → 미래 참조 없음).
  약세 · 보통 · 강세는 S가 그날 앞 모든 날의 S 분포에서 아래 1/3 · 가운데 · 위 1/3(늘어나는 표 · 미래 참조 없음).
- 계좌 = Σ 몫(산 날 장세) × 그 갈래 매매의 계좌 몫(칸/10 × 손익%) — 판 날에 확정 손익으로 셈(나눠 굴린 어림 · x004와 같은 셈).
Q_PART=d1(1일봉 2017 ~ 매매 목록) · h1y3(1시간봉 야후 3년) · join(견줌). 1년 세 갈래는 x004 목록(15분봉 · 한투 1시간봉 · 1일봉)을 씀."""
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
OUT = SP + "x008_"
part = os.environ.get("Q_PART", "join")


def dump(name, rows):
    json.dump(rows, open(OUT + name + ".json", "w"))
    print(name, len(rows), "건", flush=True)


if part == "d1":
    import ntools as T
    got = T.once("일봉 새 82회차")
    dump("d1", [(t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for s in ("앞", "뒤") if got.get(s)
                for t in got[s]["매매목록"]])
elif part == "h1y3":
    exec(open("/home/user/stock-dash/research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
    sigs = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
    KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
    r = H._one_run(data, sigs, EX, size, H.EARLY[0], H.LATE[1], 10, 0, None, rk_of(tiers(20, 5, 3)), H.COST, None, None, stale90)
    dump("h1y3", [(t["code"], t["산 때"][:8], t["판 때"].lstrip("끝")[:8], t["손익"], t["칸"]) for t in r["목록"]])
else:
    import bisect
    from datetime import date
    import numpy as np
    days = [str(d) for d, _ in json.load(open("/home/user/stock-dash/price-data/005930.json"))["closes"]]
    d1 = json.load(open(OUT + "d1.json"))
    buys = {}
    for r in d1:
        buys[r[1]] = buys.get(r[1], 0) + 1
    S, hist, regime = {}, [], {}
    for k, d in enumerate(days):
        if d < "20170101":
            continue
        s = sum(buys.get(x, 0) for x in days[max(0, k - 20):k])
        if len(hist) >= 120:
            lo, hi = np.quantile(hist, 1 / 3), np.quantile(hist, 2 / 3)
            regime[d] = "약세" if s <= lo and s < hi else ("강세" if s >= hi and s > lo else "보통")
        else:
            regime[d] = "보통"
        S[d] = s
        hist.append(s)
    D = lambda s: date(int(s[:4]), int(s[4:6]), int(s[6:8]))

    def account(tracks, weights, lo, hi):
        """tracks: {이름: 매매 목록} · weights: {장세: {이름: 몫}} → 날마다 확정 손익(%) → (합, 골, 가장 나쁜 주, 해마다)."""
        daily = {}
        for name, rows in tracks.items():
            for code, b, s, g, k in rows:
                if not (lo <= b <= hi):
                    continue
                w = weights[regime.get(b, "보통")][name]
                daily[s] = daily.get(s, 0) + w * k / 10 * g
        eq, peak, dip = 1.0, 1.0, 0.0
        for d in sorted(daily):
            eq *= 1 + daily[d] / 100
            peak = max(peak, eq)
            dip = min(dip, eq / peak - 1)
        wk = {}
        for d, v in daily.items():
            wk[D(d).isocalendar()[:2]] = wk.get(D(d).isocalendar()[:2], 0) + v
        yr = {}
        for d, v in daily.items():
            yr[d[:4]] = round(yr.get(d[:4], 0) + v, 1)
        return round(sum(daily.values()), 1), round(dip * 100, 1), round(min(wk.values()) if wk else 0, 1), dict(sorted(yr.items()))

    share = {}
    for d, g in regime.items():
        share[g] = share.get(g, 0) + 1
    print("== 탄력 배분 시험(장세 = 앞 20거래일 1일봉 새로 산 수의 1/3 나눔) ==")
    for lo, hi, tag in (("20231001", "20260930", "2023-10 ~ 2026-09"), ("20250917", "20260831", "2025-09 ~ 2026-08")):
        ds = [d for d in regime if lo <= d <= hi]
        print(f"  {tag} 장세 날 수: " + " · ".join(f"{g} {sum(1 for d in ds if regime[d] == g)}" for g in ("약세", "보통", "강세")))

    # ① 두 갈래(1일봉 · 1시간봉 야후) · 3년
    two = {"1일봉": json.load(open(OUT + "d1.json")), "1시간봉": json.load(open(OUT + "h1y3.json"))}
    P2 = {
        "반반 고정": {"약세": {"1일봉": .5, "1시간봉": .5}, "보통": {"1일봉": .5, "1시간봉": .5}, "강세": {"1일봉": .5, "1시간봉": .5}},
        "사용자안(약세엔 짧은 것 ↓ · 강세엔 1일봉 ↓)": {"약세": {"1일봉": .7, "1시간봉": .3}, "보통": {"1일봉": .5, "1시간봉": .5}, "강세": {"1일봉": .3, "1시간봉": .7}},
        "반대안(약세엔 1일봉 ↓ · 강세엔 1일봉 ↑)": {"약세": {"1일봉": .3, "1시간봉": .7}, "보통": {"1일봉": .5, "1시간봉": .5}, "강세": {"1일봉": .7, "1시간봉": .3}},
        "1일봉만": {g: {"1일봉": 1, "1시간봉": 0} for g in ("약세", "보통", "강세")},
        "1시간봉만": {g: {"1일봉": 0, "1시간봉": 1} for g in ("약세", "보통", "강세")},
    }
    print("\n① 1일봉 + 1시간봉(야후) · 2023-10 ~ 2026-09 · 확정 손익 어림")
    for name, w in P2.items():
        tot, dip, worst, yr = account(two, w, "20231001", "20260930")
        print(f"  {name:34s} 합 {tot:+7.1f}% · 골 {dip:6.1f}% · 가장 나쁜 주 {worst:5.1f}% · 해마다 {yr}")
    # ② 세 갈래(1일봉 · 한투 1시간봉 · 15분봉 후보) · 1년
    three = {"1일봉": json.load(open(SP + "x004_d1.json")), "1시간봉": json.load(open(SP + "x004_h1k.json")),
             "15분봉": json.load(open(SP + "x004_m15_final.json"))}
    eq3 = {"1일봉": 1 / 3, "1시간봉": 1 / 3, "15분봉": 1 / 3}
    P3 = {
        "3등분 고정": {g: eq3 for g in ("약세", "보통", "강세")},
        "사용자안(약세엔 15분봉 ↓ · 강세엔 1일봉 ↓)": {"약세": {"1일봉": .45, "1시간봉": .45, "15분봉": .10}, "보통": eq3,
                                           "강세": {"1일봉": .10, "1시간봉": .45, "15분봉": .45}},
        "반대안(약세엔 1일봉 ↓ · 강세엔 15분봉 ↓)": {"약세": {"1일봉": .10, "1시간봉": .45, "15분봉": .45}, "보통": eq3,
                                           "강세": {"1일봉": .45, "1시간봉": .45, "15분봉": .10}},
        "1일봉 + 1시간봉 반반": {g: {"1일봉": .5, "1시간봉": .5, "15분봉": 0} for g in ("약세", "보통", "강세")},
    }
    print("\n② 1일봉 + 1시간봉(한투) + 15분봉 후보 · 2025-09-17 ~ 2026-08-31(15분봉 자료가 있는 1년)")
    for name, w in P3.items():
        tot, dip, worst, yr = account(three, w, "20250917", "20260831")
        print(f"  {name:34s} 합 {tot:+7.1f}% · 골 {dip:6.1f}% · 가장 나쁜 주 {worst:5.1f}% · 해마다 {yr}")
    print("끝")
