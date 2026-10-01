"""1시간봉 115회차(P1 계좌 확인) — 1시간봉 엔진으로 1일봉 규칙을 흉내 내고 파는 판단 단위만 바꿈.
사기: 그날(D) 마지막 1시간봉이 닫힐 때 D 재료로 문이 열린 종목 → 다음 봉(D+1 09시) 시가(1일봉은 종가에 사지만 112회차에서 사는 때 차이는 작음).
칸: 추세 · 3일 연속 4칸 · 그 밖 2칸 · 자리 바꾸기 없음(1일봉처럼). 순서: 같은 시각 무리(94회차).
파는 판단 A = 하루 한 번(그날 마지막 봉 종가로 1일봉 숫자: 추세 +5% 절반 · +13 · −5% · 10거래일 / 정배열 −10% · +8 → +1% · 정배열 깨짐) → 다음 봉 시가
             B = 1시간봉마다(1시간봉 규칙 EX). Q_SRC=yahoo · kis · 씨앗 16."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
src = os.environ.get("Q_SRC", "yahoo")
if src == "kis":
    os.environ["Q_BARS"] = "1h"
    exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
    EXF, SZ = exit_rule, size
    def RK(sg):
        return rank_of(tiers(sg))
    SIM = M.simulate
else:
    exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
    EXF, SZ = EX, size
    def RK(sg):
        global sigs, KEYS
        sigs = sg
        KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sg[c])]
        return rk_of(tiers(20, 5, 3))
    SIM = H.simulate

LAST = {}
for c, b in data.items():
    t = b["t"]
    LAST[c] = np.array([k + 1 >= len(t) or t[k + 1][:8] != t[k][:8] for k in range(len(t))])


def daily_sig(c, b):
    m = np.zeros(len(b["t"]), bool)
    for k in np.flatnonzero(LAST[c][:-1]):
        x = ATT[c][k + 1]
        if x and ok(x) and IN[c][k + 1]:
            m[k] = True
    return m


def exit_daily(c, b, p, k):
    if not LAST[c][k]:
        return 0
    now = (b["c"][k] / p["price"] - 1) * 100
    kind = door(ATT[c][min(p["i"], len(b["t"]) - 1)]) or "정배열"
    days = len({s[:8] for s in b["t"][p["i"]:k + 1]})
    if kind == "추세":
        if now >= 13 or now <= -5 or days >= 10:
            return "all"
        before = max(b["c"][q] for q in range(p["i"], k) if LAST[c][q]) if any(LAST[c][p["i"]:k]) else -1
        if now >= 5 and (before / p["price"] - 1) * 100 < 5 and p["칸"] == p["처음칸"]:
            return max(1, p["처음칸"] // 2)
        return 0
    if now <= -10 or ((p["peak"] / p["price"] - 1) * 100 >= 8 and now <= 1):
        return "all"
    nx = ATT[c][k + 1] if k + 1 < len(b["t"]) else None
    return "all" if nx is not None and not nx["정배열"] else 0


SG = {c: daily_sig(c, b) for c, b in data.items()}
rk = RK(SG)
print(f"== 1시간봉 115회차(P1): 1일봉 규칙 흉내 · 파는 판단 단위 ({src} · {len(data)}종목) ==", flush=True)
for tag, ex in (("A 하루 한 번", exit_daily), ("B 1시간봉마다", EXF)):
    for cost in (0.3, 0.5):
        res = SIM(data, lambda c, b: SG[c], ex, SZ, rank=rk, stale_of=None, seeds=16, cost=cost)
        print(f"  {tag} · 비용 {cost}% " + H.line(res), flush=True)
print("끝", flush=True)
