"""15분봉 34회차 — ① 장중 손절 · 익절(1시간봉 60회차: 봉 안에서 선에 닿으면 바로 그 값에 팖, 시가가 이미 넘었으면 시가)
② 15분봉만의 것: 10:45에 '오늘 +2% 위'로 걸렀던 종목이 13:45 봉에 +2% 아래로 내려와 있으면 그때 삼(되밀림 사기 · 1시간봉 24회차와 비슷).
Q_PART=1: 장중 손절(추세 −5% · 정배열 −10%) · 장중 익절(추세 +13%) · 둘 다
Q_PART=2: 13:45 되밀림 사기
최종 후보(22회차) 위 · 161종목 · 씨앗 16.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])


def stop_line(p):
    kind = door(ATT[p["code"]][p["i"]]) or "정배열"
    return p["price"] * (0.95 if kind == "추세" else 0.90)


def take_line(p):
    kind = door(ATT[p["code"]][p["i"]]) or "정배열"
    return (p["price"] * 1.13, "all") if kind == "추세" else (None, 0)


def go5(tag, sig=None, stop=None, take=None):
    sg = SGF if sig is None else {c: np.asarray(sig(c, b), bool) for c, b in data.items()}
    rk = RKF if sig is None else rank_plus(tiers(sg))
    res = M.simulate(data, lambda c, b: sg[c], exit_rule, size, rank=rk, stale_of=stale90, seeds=16, stop_of=stop, take_of=take)
    print(f"  {tag:36s} " + H.line(res), flush=True)


def pullback(c, b):
    dr, mk = nan0(DR[c]), nan0(MKT[c])
    ctx = ctx_now(c, b)
    skipped = ctx & (HH[c] == "1045") & (dr > 0.02)
    later = ctx & (HH[c] == "1345") & (dr <= 0.02) & ~(mk < -0.01)
    sk_days = set(DAY[c][np.flatnonzero(skipped)])
    base = SGF[c].copy()
    have = set(DAY[c][np.flatnonzero(base)])
    for k in np.flatnonzero(later):
        d = DAY[c][k]
        if d in sk_days and d not in have:
            base[k] = True
            have.add(d)
    return base


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 34회차({part}): 장중 손절 · 익절 / 되밀림 사기 ({len(data)}종목) ==", flush=True)
if part == "1":
    go5("장중 손절(추세 −5 · 정배열 −10%)", stop=stop_line)
    go5("장중 익절(추세 +13%)", take=take_line)
    go5("장중 손절 + 익절", stop=stop_line, take=take_line)
else:
    go5("10:45에 걸렀다가 13:45 +2% 아래면 삼", pullback)
print("끝", flush=True)
