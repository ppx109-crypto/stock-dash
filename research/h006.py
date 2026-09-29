"""1시간봉 6회차(탐색 줄) — 사는 순서 · 칸. 3회차에서 씨앗 폭이 컸음(뒤 14~26%p): 같은 시각 후보가 많아 순서가 담는 종목을 크게 바꿈.
사는 때 = 1시간봉 A 정배열 된 봉 다음, 없으면 12시 · 파는 법 = 일봉 규칙(4회차 결론).
순서(모두 신호 봉까지 아는 값): 지금(추세 문 → 3일 연속 → 흔들기) · + 1시간봉 20봉 이격 작은 것(덜 뜬 것) 먼저 · + 1시간봉 60봉 기울기 큰 것 먼저
· + 일봉 선 간격 작은 것 먼저 · + 수급 5일(외국인+투신) 큰 것 먼저(순위 · 종목 크기 차이는 무시한 날것)
칸: 1시간봉 정배열로 산 것 +1칸(최대 4칸)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

E = e_align_or_noon
def base_key(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1)
def r_gap(c, b, k): return base_key(c, b, k) + (float(H.states(c, b, "A")["이격20"][k]),)
def r_slope(c, b, k): return base_key(c, b, k) + (-float(H.states(c, b, "A")["기울기60"][k]),)
def r_spread(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    return base_key(c, b, k) + ((x["간격"] if x else 99),)
def r_flow(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    f = x["수급5"] if x else {}
    return base_key(c, b, k) + (-((f.get("외국인") or 0) + (f.get("투신") or 0)),)
def size_plus(c, b, k):
    s = size(c, b, k)
    al = H.states(c, b, "A")["정배열"][k] == 1
    return min(4, s + 1) if al else s

print("== 1시간봉 6회차 (사는 순서 · 칸) ==", flush=True)
for tag, rk, sz in (("지금 순서", rank, size), ("+ 20봉 이격 작은 것 먼저", r_gap, size), ("+ 60봉 기울기 큰 것 먼저", r_slope, size),
                    ("+ 일봉 선 간격 작은 것 먼저", r_spread, size), ("+ 수급 5일 큰 것 먼저", r_flow, size),
                    ("칸: 1시간봉 정배열로 산 것 +1칸", rank, size_plus)):
    res = H.simulate(data, E, exit_daily, sz, rank=rk)
    print(f"  {tag:26s} " + H.line(res), flush=True)
print("끝", flush=True)
