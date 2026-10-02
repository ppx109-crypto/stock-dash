"""15분봉 복리 연수익 — 오래 들고 가기 vs 빨리 갈아타기(사용자 2026-10-02 "15m도 진행해줘 복리 연수익 최대로 나오는 방법").
기준 = 15분봉 최종 후보(22회차 · q027 · 한투 1년 160종목 · 씨앗 16). 파는 법은 1시간봉과 같되 봉 수 × 4(SCALE).
Q_PART=1: 추세 쪽 오래 들기 · 2: 고점 대비 · 정배열 쪽 · 3: 자리 바꾸기 세기."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])


def trail_ex(trail=10, arm=13, hold=240, half=5, guard=True, atrail=None, take=None):
    def ex(c, b, p, k):
        now = (b["c"][k] / p["price"] - 1) * 100
        pk = (p["peak"] / p["price"] - 1) * 100
        kind = door(ATT[c][p["i"]]) or "정배열"
        if kind == "추세":
            if now <= -5 or k - p["i"] >= hold * SCALE or (take and now >= take):
                return "all"
            if trail and pk >= arm and b["c"][k] <= p["peak"] * (1 - trail / 100):
                return "all"
            before = b["c"][p["i"]:k].max() if k > p["i"] else -1
            if half and now >= half and (before / p["price"] - 1) * 100 < half and p["칸"] == p["처음칸"]:
                return max(1, p["처음칸"] // 2)
            return 0
        if now <= -10:
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
    return ex


def go(tag, ex=None, st="기준"):
    stale = stale90 if st == "기준" else st
    res = M.simulate(data, lambda c, b: SGF[c], ex or exit_rule, size, rank=RKF, stale_of=stale, seeds=16)
    extra = [f"{s} 보유 {r['보유봉']}봉 · 회전 {r['회전']}배 · 가동 {r['가동']}" for s, r in res.items() if r]
    print(f"  {tag:36s} " + H.line(res) + " || " + " · ".join(extra), flush=True)


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 복리 연수익 ({part}) · {len(data)}종목 · 한투 1년 ==", flush=True)
if part == "1":
    go("기준(지금 파는 법)")
    for take, hold in ((20, 60), (30, 60), (999, 60), (13, 120), (20, 120), (999, 120), (999, 240)):
        go(f"추세 전량 {('+' + str(take)) if take < 999 else '없음'} · {hold}×4봉", make_exit(take=take, hold=hold))
    go("추세 절반 없이", make_exit(half=0))
elif part == "2":
    for trail, arm in ((8, 8), (10, 8), (10, 13), (15, 13), (20, 13)):
        go(f"추세 +{arm}% 뒤 고점 −{trail}% · 240×4봉", trail_ex(trail=trail, arm=arm))
    go("정배열 +8→+1 지키기 뺌", make_exit(keep=None))
    for at in (10, 15, 20):
        go(f"정배열 지키기 대신 고점 −{at}%", trail_ex(trail=None, take=13, hold=60, guard=False, atrail=at))
    go("둘 다 오래: 추세 고점 −10% · 정배열 고점 −15%", trail_ex(trail=10, arm=13, guard=False, atrail=15))
else:
    go("자리 바꾸기 끔(끝까지 들고 감)", st=None)
    for n, x in ((4, 2), (5, 3), (7, 2), (10, 4), (14, 6), (21, 8)):
        go(f"자리 바꾸기 {n}×4봉 · +{x}% 못 미치면", st=make_stale(n, x))
print("끝", flush=True)
