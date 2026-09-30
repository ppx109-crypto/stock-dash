"""일봉 새 64회차 — 같은 날 후보의 사는 순서를 1시간봉 90회차처럼.

같은 날 후보(지금 규칙을 채운 종목)끼리만 셈: (가) 외국인+투신 순매수 n일 합(전날까지) ÷ 20일 평균 거래량(전날까지) — 약할수록 먼저,
(나) m일 수익(오늘 종가까지 · 오늘 종가에 사므로 앎) — 클수록 먼저. 각각 k무리로 나눠 더한 점수가 큰 것부터, 같으면 180일선 기울기 순.
35회차(60일 오름 · 이격 · 시총 · 3일 연속 순)에는 '수급이 약한데 이미 오른' 순서가 없었음.
실행: NRL_CACHE=... python3 research/n064.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import ntools as T

print("== 일봉 새 64회차: 같은 날 후보 순서 ==", flush=True)
print("후보 날", len(T.BY_DAY), "· 둘 이상인 날", sum(1 for v in T.BY_DAY.values() if len(v) > 1),
      "· 수급 세기 값 있는 몫", T.cover(T.flow_strength), "%", flush=True)
FLOW = (T.flow_strength, True)
RET = (T.ret, False)
base = T.once("지금: 180일선 기울기 순")
print("      해마다", T.years(base), flush=True)
got = T.once("수급 약 + 20일 수익 큼 (3무리)", rank=T.rank_by([FLOW, RET]))
print("      해마다", T.years(got), flush=True)
T.diff_check(base, got)
got = T.once("추세 → 3일 연속 → 수급 약 + 수익 큼", rank=T.rank_by([FLOW, RET], first=("trend", "steady")))
T.diff_check(base, got)
T.once("수급 약만", rank=T.rank_by([FLOW]))
T.once("20일 수익 큼만", rank=T.rank_by([RET]))
for k in (2, 4, 5):
    T.once(f"수급 약 + 수익 큼 ({k}무리)", rank=T.rank_by([FLOW, RET], k=k))
for m in (10, 40):
    T.once(f"수급 약 + {m}일 수익 큼", rank=T.rank_by([FLOW, (lambda r, m=m: T.ret(r, m), False)]))
T.once("수급 10일 약 + 20일 수익 큼", rank=T.rank_by([(lambda r: T.flow_strength(r, 10), True), RET]))
print("끝", flush=True)
