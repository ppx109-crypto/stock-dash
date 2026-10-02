"""E 1회차 — DART 실적을 여러 갈래로 비교해 앞으로 수익과 견줌(사용자 제안 2026-10-02).
갈래: 이번 분기 vs 작년 같은 분기 · 올해 누적 vs 작년 누적 · 최근 한 해 vs 앞해 · 재작년 대비(분기 · 누적 · 한 해) · 최근 네 분기 · 이어진 증가.
[1] 그날 시총 100위 전체(nrl.inside) — 20 · 60일 뒤 수익에서 그날 100위 평균을 뺀 값(두 반)
[2] 1일봉 사는 조건(nrl.BASE_HOLD) 안에서만
접수일이 신호 날 **앞**인 보고서만 씀. 다음 날 종가에 산다고 봄."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import etools as E
import nrl

MID = nrl.rule.MID
book = E.Book()
rows = list(nrl.inside)
F = {}
for r in rows:
    F[(r["code"], r["date"])] = book.feats(r["code"], r["date"])
fw, mean = {}, {}
for r in rows:
    c = nrl.lanes[r["code"]]["closes"]
    i = r["i"]
    for h in (20, 60):
        v = c[i + 1 + h] / c[i + 1] - 1 if i + 1 + h < len(c) and c[i + 1] else None
        fw[(r["code"], r["date"], h)] = v
        if v is not None:
            mean.setdefault((r["date"], h), []).append(v)
mean = {k: float(np.mean(v)) for k, v in mean.items()}


def ex(r, h):
    v = fw[(r["code"], r["date"], h)]
    return None if v is None else v - mean[(r["date"], h)]


def show(name, picked):
    out = [f"  {name:26s}"]
    for side, test in (("앞", lambda d: d < MID), ("뒤", lambda d: d >= MID)):
        sel = [r for r in picked if test(r["date"])]
        a = [ex(r, 20) for r in sel if ex(r, 20) is not None]
        b = [ex(r, 60) for r in sel if ex(r, 60) is not None]
        if len(a) < 20:
            out.append(f"| {side} {len(a)}건(적음)")
            continue
        out.append(f"| {side} {len(a):6d}건 20일 {np.mean(a) * 100:+5.2f} 60일 {np.mean(b) * 100:+5.2f} 이김 {np.mean(np.array(a) > 0) * 100:4.1f}")
    print(" ".join(out), flush=True)


def tier(v):
    if v is None:
        return "뜻 없음(밑이 0 이하·빈칸)"
    for lo, nm in ((50, "+50% 넘게"), (20, "+20~50%"), (0, "0~+20%"), (-20, "−20~0%")):
        if v >= lo:
            return nm
    return "−20% 넘게 줄음"


ORDER = ("+50% 넘게", "+20~50%", "0~+20%", "−20~0%", "−20% 넘게 줄음", "뜻 없음(밑이 0 이하·빈칸)")
NAMES = {"q": "이번 분기 vs 작년 같은 분기", "ytd": "올해 누적 vs 작년 누적", "yr": "최근 한 해 vs 앞해",
         "q2": "이번 분기 vs 재작년", "ytd2": "올해 누적 vs 재작년 누적", "yr2": "최근 한 해 vs 두 해 전", "ttm": "최근 네 분기 vs 앞 네 분기"}


def study(label, pool):
    have = [r for r in pool if F[(r["code"], r["date"])]]
    print(f"\n==== {label}: {len(pool)}줄 중 실적 있는 {len(have)}줄 ====", flush=True)
    show("실적 있는 것 전체", have)
    show("실적 없는 것", [r for r in pool if not F[(r["code"], r["date"])]])
    for x, xn in (("o", "영업이익"), ("s", "매출")):
        for key in ("q", "ytd", "yr", "q2", "ytd2", "yr2", "ttm"):
            print(f" -- {xn} · {NAMES[key]}", flush=True)
            groups = {}
            for r in have:
                groups.setdefault(tier(F[(r["code"], r["date"])].get(f"{key}_{x}")), []).append(r)
            for nm in ORDER:
                if nm in groups:
                    show(nm, groups[nm])
    for key, kn in (("q_turn", "영업이익 갈래 · 이번 분기"), ("ytd_turn", "영업이익 갈래 · 올해 누적"), ("yr_turn", "영업이익 갈래 · 최근 한 해")):
        print(f" -- {kn}", flush=True)
        for t in ("흑전", "늘음", "줄음", "적전", "적지"):
            show(t, [r for r in have if F[(r["code"], r["date"])].get(key) == t])
    print(" -- 영업이익이 작년 같은 분기보다 늘어난 분기가 이어진 수", flush=True)
    for lo, hi, nm in ((0, 0, "0번"), (1, 1, "1번"), (2, 3, "2~3번"), (4, 99, "4번 넘게")):
        show(nm, [r for r in have if lo <= F[(r["code"], r["date"])]["run"] <= hi])
    print(" -- 겹치기(영업이익)", flush=True)
    g = lambda r, k: (F[(r["code"], r["date"])].get(k) or -1e9)
    show("분기 · 누적 · 한 해 모두 늘음", [r for r in have if g(r, "q_o") > 0 and g(r, "ytd_o") > 0 and g(r, "yr_o") > 0])
    show("분기 · 누적 · 한 해 모두 줄음", [r for r in have if -1e9 < g(r, "q_o") < 0 and -1e9 < g(r, "ytd_o") < 0 and -1e9 < g(r, "yr_o") < 0])
    show("작년 · 재작년 대비 모두 +20%↑(누적)", [r for r in have if g(r, "ytd_o") >= 20 and g(r, "ytd2_o") >= 20])
    show("분기 > 누적(빨라짐)", [r for r in have if g(r, "q_o") > g(r, "ytd_o") > 0])
    show("매출 · 영업이익 누적 모두 +20%↑", [r for r in have if g(r, "ytd_o") >= 20 and g(r, "ytd_s") >= 20])
    show("매출↑ 영업이익↓(누적)", [r for r in have if g(r, "ytd_s") > 0 and -1e9 < g(r, "ytd_o") < 0])


study("그날 시총 100위 전체", rows)
study("1일봉 사는 조건 안", [r for r in rows if nrl.BASE_HOLD(r)])
print("끝", flush=True)
