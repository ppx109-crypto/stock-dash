"""1시간봉 복리 연수익 — 오래 들고 가기 vs 빨리 갈아타기(사용자 2026-10-02 "1H로도 복리 연수익 다양한 방법으로 시도해줘").
기준 = 1시간봉 123회차 기준(90 · 94회차 · 야후 3년: 앞 39.19 / 뒤 112.76) · 씨앗 16. 연 = 복리 연수익(자본이 불어나는 빠르기).
지금 파는 법: 추세 = +5%에 절반 · +13% 전량 · −5% · 60봉 / 정배열 = −10% · +8%에 닿은 뒤 +1% 아래 · 다음 봉 일봉 정배열 깨짐
 · 자리 바꾸기(stale90) = 7봉 지나도 +4% 못 미친 매매는 새 후보가 오면 팔고 갈아탐(전날 시장 폭 < 90%일 때).
Q_PART=1: 추세 쪽 오래 들기 · 2: 추세 고점 대비 · 이동평균 · 정배열 쪽 · 3: 갈아타기 빠르기(자리 바꾸기 세기). Q_SRC=yahoo · kis."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import hlab as H
import kis1h

src = os.environ.get("Q_SRC", "yahoo")
PER = kis1h.use() if src == "kis" else None
exec(open("/home/user/stock-dash/research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
SG = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
rk = rk_of(tiers(20, 5, 3))


def ex(take=13, tstop=5, bars=60, trail=None, arm=13, line=None, astop=10, guard=True, atrail=None, half=True):
    def f(c, b, p, k):
        now = (b["c"][k] / p["price"] - 1) * 100
        pk = (p["peak"] / p["price"] - 1) * 100
        kind = door(ATT[c][p["i"]]) or "정배열"
        held = k - p["i"]
        if kind == "추세":
            armed = pk >= arm
            if now <= -tstop or held >= bars:
                return "all"
            if take and now >= take:
                return "all"
            if trail and armed and b["c"][k] <= p["peak"] * (1 - trail / 100):
                return "all"
            if line and armed and b["c"][k] < ema(c, line)[k]:
                return "all"
            before = b["c"][p["i"]:k].max() if k > p["i"] else -1
            if half and now >= 5 and (before / p["price"] - 1) * 100 < 5 and p["칸"] == p["처음칸"]:
                return max(1, p["처음칸"] // 2)
            return 0
        if now <= -astop:
            return "all"
        if guard and pk >= 8 and now <= 1:
            return "all"
        if atrail and pk >= 10 and b["c"][k] <= p["peak"] * (1 - atrail / 100):
            return "all"
        if k + 1 < len(b["t"]):
            nx = ATT[c][k + 1]
            if nx is not None and not nx["정배열"]:
                return "all"
        return 0
    return f


def stale(n, x):
    """자리 바꾸기 후보: 산 뒤 n봉 지났는데 지금 손익이 +x% 아래(전 봉까지 값 · hguard_world와 같은 꼴)."""
    return lambda p: (p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x


def go(tag, exit_rule, stale_of=stale90):
    kw = {"periods": PER} if PER else {}
    res = H.simulate(data, lambda c, b: SG[c], exit_rule, size, rank=rk, stale_of=stale_of, seeds=16, **kw)
    extra = []
    for s, r in res.items():
        if r:
            extra.append(f"{s} 가운데 보유 {r['보유봉']}봉 · 회전 {r['회전']}배 · 가동 {r['가동']}")
    print(f"  {tag:36s} " + H.line(res) + " || " + " · ".join(extra), flush=True)


part = os.environ.get("Q_PART", "1")
print(f"== 1시간봉 복리 연수익 ({part}) · {'한투 1년' if src == 'kis' else '야후 3년'} · {len(data)}종목 ==", flush=True)
if part == "1":
    go("기준(지금 파는 법 · EX)", EX)
    go("같은 꼴로 다시 짠 지금(검산)", ex())
    for take, bars in ((20, 60), (30, 60), (None, 60), (13, 120), (20, 120), (None, 120), (None, 240)):
        go(f"추세 전량 {('+' + str(take)) if take else '없음'} · {bars}봉", ex(take=take, bars=bars))
    go("추세 절반 없이 +13 · 60봉", ex(half=False))
elif part == "2":
    for trail, arm in ((8, 8), (10, 8), (10, 13), (15, 13), (20, 13)):
        go(f"추세 +{arm}% 뒤 고점 −{trail}% · 240봉", ex(take=None, bars=240, trail=trail, arm=arm))
    for line in (20, 40):
        go(f"추세 +13% 뒤 {line}봉 이평 아래면 · 240봉", ex(take=None, bars=240, line=line))
    go("정배열 +8→+1 지키기 뺌", ex(guard=False))
    for at in (10, 15, 20):
        go(f"정배열 지키기 대신 고점 −{at}%", ex(guard=False, atrail=at))
    go("둘 다 오래: 추세 고점 −10% · 정배열 고점 −15%", ex(take=None, bars=240, trail=10, guard=False, atrail=15))
else:
    go("자리 바꾸기 끔(끝까지 들고 감)", EX, stale_of=None)
    for n, x in ((4, 2), (5, 3), (7, 2), (7, 4), (10, 4), (14, 6), (21, 8)):
        go(f"자리 바꾸기 {n}봉 · +{x}% 못 미치면", EX, stale_of=stale(n, x))
    go("자리 바꾸기(늘 · 시장 폭 상관없이 7봉 · +4%)", EX, stale_of=stale(7, 4))
print("끝", flush=True)
