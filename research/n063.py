"""일봉 새 63회차 — 자리 바꾸기(1시간봉 최고 규칙의 뼈대)를 일봉에.

새 신호에 칸이 모자라면, N거래일 이상 들고 있는데 오늘 종가 손익이 X% 아래인 종목을 손익이 나쁜 것부터 오늘 종가에 팔고
새 신호를 담습니다(lab.run swap). 문: 전 거래일 시장 폭 < 90(1시간봉 90회차와 같은 뜻) 또는 늘.
점검: 바꿔서 판 매매의 손익 vs 기준 규칙에서 같은 매매의 손익 · 새로 담긴 매매의 손익.
실행: NRL_CACHE=... python3 research/n063.py
"""
import bisect
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import ntools as T
import nrl

DAYS = sorted(nrl.BR)


def gate_below(level):
    def ok(day):
        k = bisect.bisect_left(DAYS, day)
        return (nrl.BR.get(DAYS[k - 1], 0) if k else 0) < level
    return ok


def swapped(base, got):
    for side in ("앞", "뒤"):
        b, g = base.get(side), got.get(side)
        if not b or not g:
            continue
        keep = {}
        for t in b["매매목록"]:
            keep.setdefault((t["code"], t["산 날"]), []).append(t)
        sw = [t for t in g["매매목록"] if t.get("자리 바꿈")]
        f = lambda ts: sum(t["손익"] * t["자리"] for t in ts) / nrl.SLOTS
        then = [x for t in sw for x in keep.get((t["code"], t["산 날"]), [])]
        print(f"      {side} 바꿔서 판 매매 {len(sw)}건 {f(sw):+.1f}%(계좌 몫) · 기준 규칙에선 같은 매매가 {f(then):+.1f}%", flush=True)


print("== 일봉 새 63회차: 자리 바꾸기 ==", flush=True)
base = T.once("지금 규칙(기준)")
print("      해마다", T.years(base), flush=True)
T.once("후보 끝까지 보기만(바꾸지 않음 · 대조)", swap=(9999, -999, None))
best = []
for days in (3, 5, 7, 10):
    for below in (0, 2, 4):
        for gname, gate in (("늘", None), ("폭<90", gate_below(90))):
            got = T.once(f"바꾸기 {days}일↑ · +{below}% 못 감 · {gname}", swap=(days, below, gate))
            if got.get("앞") and got.get("뒤"):
                best.append((got["앞"]["연수익"] + got["뒤"]["연수익"], days, below, gname, got))
best.sort(key=lambda x: -x[0])
for score, days, below, gname, got in best[:3]:
    print(f"  ▶ 상위: {days}일 · +{below}% · {gname} → 해마다 {T.years(got)}", flush=True)
    swapped(base, got)
    T.diff_check(base, got)
print("끝", flush=True)
