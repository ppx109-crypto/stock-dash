"""1시간봉 7회차(탐색 줄) — 사는 순간의 1시간봉 정보로 거르기(모두 신호 봉까지 아는 값). 막은 매매 점검 함께.
사는 때 = 1시간봉 A 정배열 된 봉 다음, 없으면 12시 · 파는 법 = 일봉 규칙.
- 시장: 코스피 1시간봉 A 배열이 1 이하(장중 내림 흐름)면 안 삼 / 코스피가 오늘 전날 마지막 봉 종가보다 1% 넘게 내렸으면 안 삼
- 쫓기: 종목이 오늘 전날 마지막 봉 종가보다 4% 넘게 올랐으면 안 삼(이미 뜀)
- 거래량: 신호 봉 거래량이 지난 20봉 평균의 0.7배 아래면 안 삼(힘없는 오름)"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import collections
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

MK = H.load(["KOSPI"])["KOSPI"]
MK_AT = {t: i for i, t in enumerate(MK["t"])}
MK_ST = H.states("KOSPI", MK, "A")
def prev_close_idx(b, k):
    day = b["t"][k][:8]
    j = k
    while j >= 0 and b["t"][j][:8] == day: j -= 1
    return j
def mk_down_trend(c, b, k):
    i = MK_AT.get(b["t"][k]); return i is not None and MK_ST["배열"][i] <= 1
def mk_fell(c, b, k):
    i = MK_AT.get(b["t"][k])
    if i is None: return False
    j = prev_close_idx(MK, i)
    return j >= 0 and (MK["c"][i] / MK["c"][j] - 1) * 100 <= -1
def chased(c, b, k):
    j = prev_close_idx(b, k)
    return j >= 0 and (b["c"][k] / b["c"][j] - 1) * 100 >= 4
def thin(c, b, k):
    if k < 20: return False
    avg = b["v"][k - 20:k].mean()
    return avg > 0 and b["v"][k] < 0.7 * avg

E0 = e_align_or_noon
def filtered(bad):
    def e(c, b):
        m = E0(c, b).copy()
        for k in np.flatnonzero(m):
            if bad(c, b, k): m[k] = False
        return m
    return e

print("== 1시간봉 7회차 (사는 순간 1시간봉 거르기) ==", flush=True)
base = H.simulate(data, E0, exit_daily, size, rank=rank)
print(f"  {'기준':24s} " + H.line(base), flush=True)
for tag, bad in (("코스피 1시간봉 내림 흐름", mk_down_trend), ("코스피 오늘 −1% 넘게", mk_fell),
                 ("종목 오늘 +4% 넘게 뜀", chased), ("신호 봉 거래량 얇음", thin)):
    res = H.simulate(data, filtered(bad), exit_daily, size, rank=rank)
    print(f"  {'안 삼: ' + tag:24s} " + H.line(res), flush=True)
    for side in ("앞", "뒤"):
        by = collections.defaultdict(lambda: [0, 0.0])
        for t in base[side]["목록"]:
            c = t["code"]; b = data[c]
            k = b["t"].index(t["산 때"]) - 1
            if k >= 0 and bad(c, b, k):
                h = t["산 때"][:4] + ("상" if t["산 때"][4:6] <= "06" else "하")
                by[h][0] += 1; by[h][1] += t["손익"] * t["칸"] / 10
        print(f"      막았을 매매 {side}: {sum(v[0] for v in by.values())}건 · 계좌 몫 {sum(v[1] for v in by.values()):+.1f}% · "
              + ", ".join(f"{h} {v[0]}건 {v[1]:+.1f}" for h, v in sorted(by.items())), flush=True)
print("끝", flush=True)
