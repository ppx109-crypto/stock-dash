"""I 11회차 — '약세장 돌리기': 한국 시장이 약할 때(1일봉 규칙이 쉬는 날) 인버스 대신 **한국에 상장된 1배 해외 · 안전자산 ETF** 가운데 오르는 것을 듦.
까닭: 한국 약세장엔 원화가 약해지고(달러 ↑) · 미국 지수 · 금 · 채권은 한국과 따로 놂 → 인버스(되돌림에 잃음)보다 '쉬는 돈'을 크게 굴릴 수 있음.
후보: 133690 TIGER 미국나스닥100 · 143850 TIGER 미국S&P500선물(H) · 138230 KOSEF 미국달러선물 · 132030 KODEX 골드선물(H) · 148070 KOSEF 국고채10년 · 114800 KODEX 인버스.
판:
  켜는 때(G): 언제나 / 코스피(KODEX 200) < 200일선 / 시장 폭 < 50(2017 ~ · 1일봉 쉬는 날과 같음)
  고르기: 하나 고정 / 주마다(그 주 마지막 날 종가) L일 수익 1등(L = 20 · 60 · 120) · 수익 > 0 인 것만(다 − 면 현금) · 1등 또는 위 2개 반반
  바꾸는 비용 0.2%(사고팔기 합). 정한 날 다음 날 수익부터 반영.
기간: A 2011 ~ 2016(자료 시작이 2010 ~ 2011) · B · C. 잣대: 세 기간 연 · 골(−15 안)."""
import sys
from datetime import datetime

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I

ALL = ["133690", "143850", "138230", "132030", "148070", "114800", "153130"]
NAME = {"133690": "나스닥", "143850": "S&P(H)", "138230": "달러", "132030": "금", "148070": "국채10년", "114800": "인버스", "153130": "단기채권"}
D, n = I.DAYS, len(I.DAYS)
P = {c: I.px(c) for c in ALL}
R = {c: np.nan_to_num(np.concatenate([[0], P[c][1:] / P[c][:-1] - 1]), nan=0) for c in ALL}
k = I.K200
G = {"언제나": np.ones(n, bool), "코스피<200일선": np.nan_to_num(k < I.ma(k, 200), nan=0).astype(bool)}
try:
    br = I.breadth()
    G["시장 폭<50"] = np.nan_to_num(br, nan=100) < 50
except Exception as e:  # noqa: BLE001
    print("시장 폭 못 읽음", e)
wk = [datetime.strptime(d, "%Y%m%d").isocalendar()[:2] for d in D]
week_end = np.array([i == n - 1 or wk[i + 1] != wk[i] for i in range(n)])
PER = (("A", "20110101", "20170101"), ("B", "20170101", "20210101"), ("C", "20210101", "20991231"))


week_start = np.array([i == 0 or wk[i - 1] != wk[i] for i in range(n)])


def run(gate, pick, cost=0.002, reb="week"):
    """pick(i) → {코드: 몫}. 다시 고르는 날(reb: week = 주 끝 · mon = 주 첫날 · day = 날마다)에 고르고, 켜는 때가 꺼지면 바로 현금. 날마다 계좌 수익률."""
    daily = np.zeros(n)
    w, chosen = {}, {}
    when = {"week": week_end, "mon": week_start, "day": np.ones(n, bool)}[reb]
    for i in range(1, n):
        daily[i] = sum(x * R[c][i] for c, x in w.items())
        if when[i] or not chosen:
            chosen = pick(i)
        new = chosen if gate[i] else {}
        turn = sum(abs(new.get(c, 0) - w.get(c, 0)) for c in set(new) | set(w))
        daily[i] -= turn * cost / 2
        w = new
    return daily


def fixed(c):
    return lambda i: {c: 1.0} if not np.isnan(P[c][i]) else {}


MA = {}


def momentum(L, top, cands, ma_n=0, skip=None):
    """주 끝에 L일 수익 1등(위 top개 · 몫 같게) · 수익 > 0 인 것만. ma_n > 0 이면 그 상품이 ma_n일선 위일 때만.
    skip: {코드: 날마다 참/거짓} — 참인 날은 그 상품을 고르지 않음(예: 코스피 하락 추세면 나스닥 뺌)."""
    def pick(i):
        sc = []
        for c in cands:
            if skip and c in skip and skip[c][i]:
                continue
            if i - L < 0 or np.isnan(P[c][i]) or np.isnan(P[c][i - L]):
                continue
            if ma_n:
                m = MA.setdefault((c, ma_n), I.ma(np.nan_to_num(P[c], nan=0), ma_n))
                if not P[c][i] > m[i]:
                    continue
            r = P[c][i] / P[c][i - L] - 1
            if r > 0:
                sc.append((r, c))
        sc.sort(reverse=True)
        sc = sc[:top]
        return {c: 1 / top for _, c in sc}
    return pick


def show(tag, daily):
    parts = []
    worst = 99
    for name, lo, hi in PER:
        s = I.stats(daily, lo, hi)
        parts.append(f"| {name} 연 {s[0]:+5.1f} 골 {s[1]:6.1f}")
        worst = min(worst, s[0] if s[1] > -15 else -99)
    print(f"  {tag:40s} " + " ".join(parts), flush=True)
    return worst


def main():
    print("== I 11회차: 약세장 돌리기(해외 · 안전자산 1배 ETF) ==", flush=True)
    for gname, gate in G.items():
        on = {name: gate[[i for i, d in enumerate(D) if lo <= d < hi]].mean() * 100 for name, lo, hi in PER}
        print(f"\n######## 켜는 때: {gname} (켜진 날 A {on['A']:.0f}% · B {on['B']:.0f}% · C {on['C']:.0f}%) ########", flush=True)
        for c in ALL:
            show(f"{NAME[c]} 고정", run(gate, fixed(c)))
        for cands, cname in ((ALL[:5], "5개"), (ALL, "5개+인버스+단기채"), (["133690", "138230", "132030", "148070"], "나스닥·달러·금·채권")):
            for L in (20, 60, 120):
                for top in (1, 2):
                    show(f"{cname} · {L}일 1등{'' if top == 1 else ' 2개'}", run(gate, momentum(L, top, cands)))
    print("끝", flush=True)


if __name__ == "__main__":
    main()
