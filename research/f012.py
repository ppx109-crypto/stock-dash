"""F 12회차(사용자 2026-10-02 "이긴 매매를 더 오래 들고 가기 진행 · 들고 있는 게 자본이 빠르게 불어나는지 지금처럼 새로 거래하는 게 빠른지 비교").
1일봉 엔진(새 82 · 씨앗 8)에서 파는 법만 바꿈. 잣대: 연(복리 연수익 = 자본이 불어나는 빠르기) · 골 · 행운뺌 · 회전(1년 몇 번 갈아탐) · 가동 · 보유(가운데 날).
지금: 추세 = +5%에 절반 · +13% 전량 · −5% 손절 · 10일 / 정배열 = 정배열 깨짐 · −10% · +8% 닿은 뒤 +1% 아래.
Q_PART=1: 추세 쪽 늦추기 · 2: 추세 쪽 고점 대비 팔기 · 3: 정배열 쪽 · 둘 다."""
import os
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import lab
import nrl
import ntools as T

rule = nrl.rule


def trail_rule(first=5, stop=5, trail=10, days=60, take=None, arm=5):
    """추세: +first%에 처음 닿는 날 절반 · 나머지는 고점(산 뒤 가장 높은 종가)에서 trail% 빠지면(고점이 +arm% 넘은 뒤) 팖 · −stop% · days일 · take%면 전량."""
    def go(lane, start, price, step, peak, row=None):
        c = lane["closes"][start + step]
        now = (c / price - 1) * 100
        if now <= -stop or step >= days or (take and now >= take):
            return True
        if (peak / price - 1) * 100 >= arm and (c / peak - 1) * 100 <= -trail:
            return True
        if first and nrl.first_cross(lane, start, price, step, first):
            return max(1, nrl.BASE_SIZE(row) // 2)
        return False
    return go


def broken_trail(trail=None, guard=True, loss=10):
    """정배열: 정배열 깨짐 · −loss% · (guard면) +8% 닿은 뒤 +1% 아래 · (trail이면) 고점이 +10% 넘은 뒤 고점에서 trail% 빠지면."""
    def go(lane, start, price, step, peak, row=None):
        spot = start + step
        c = lane["closes"][spot]
        now = (c / price - 1) * 100
        pk = (peak / price - 1) * 100
        if now <= -loss:
            return True
        if guard and pk >= 8 and now <= 1:
            return True
        if trail and pk >= 10 and (c / peak - 1) * 100 <= -trail:
            return True
        return not nrl.shape[lane["code"]]["정배열"][spot]
    return go


def run(tag, trend=None, align=None):
    ex = lab.exit_per_tier(nrl.tier, {"규칙": trend or nrl.RULE_EXIT, "정배열": align or nrl.broken})
    T.once(tag, exit_at=ex)


part = os.environ.get("Q_PART", "1")
print(f"== F 12회차({part}): 이긴 매매를 더 오래 들고 가기 ==", flush=True)
if part == "1":
    run("지금(새 82)")
    for take, days in ((20, 10), (30, 10), (999, 10), (13, 20), (20, 20), (30, 40), (999, 60)):
        run(f"추세: 전량 +{take if take < 999 else '없음'} · {days}일", trend=nrl.half_rule(first=5, take=take, stop=5, days=days))
    run("추세: 절반 없이 +13% · 10일", trend=nrl.half_rule(first=0, take=13, stop=5, days=10))
elif part == "2":
    for trail, days in ((8, 30), (10, 30), (10, 60), (15, 60), (20, 60), (15, 120)):
        run(f"추세: 고점 −{trail}% · {days}일(+5% 절반)", trend=trail_rule(trail=trail, days=days))
    run("추세: 고점 −10% · 60일 · 절반 없이", trend=trail_rule(first=0, trail=10, days=60))
    run("추세: 절반 뒤 나머지는 정배열 깨짐까지", trend=lambda l, s, p, k, pk, row=None: (
        nrl.first_cross(l, s, p, k, 5) and max(1, nrl.BASE_SIZE(row) // 2)) or (l["closes"][s + k] / p - 1) * 100 <= -5
        or (k >= 5 and not nrl.shape[l["code"]]["정배열"][s + k]) or k >= 120)
else:
    run("정배열: +8 → +1 지키기 뺌", align=broken_trail(guard=False))
    for trail in (10, 15, 20):
        run(f"정배열: 지키기 대신 고점 −{trail}%", align=broken_trail(trail=trail, guard=False))
    run("정배열: 지키기 + 고점 −15%", align=broken_trail(trail=15))
    run("둘 다: 추세 고점 −10% · 60일 + 정배열 지키기 뺌", trend=trail_rule(trail=10, days=60), align=broken_trail(guard=False))
    run("둘 다: 추세 전량 없음 · 60일 + 정배열 고점 −15%", trend=nrl.half_rule(first=5, take=999, stop=5, days=60),
        align=broken_trail(trail=15, guard=False))
print("끝", flush=True)
