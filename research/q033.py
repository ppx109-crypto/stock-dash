"""15분봉 32회차 — 옮기기 ⑤.
Q_PART=1: 비킬 매매를 한투 수급으로 고르기(1시간봉 87회차): 그 봉 재료의 5일 외국인 + 투신 순매수가 약한 것부터 · 강한 것부터
Q_PART=2: 파는 판단 시각(1시간봉 61회차): 09:00 칸(장 시작 첫 15분)에서는 팔기 판단을 하지 않음 · 15:15 칸(마감 칸)에서는 팔기 판단을 하지 않음(밤사이 틈을 다음 날 09:00 칸 종가로 다시 봄)
최종 후보(22회차) 위 · 161종목 · 씨앗 16.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q030.py", encoding="utf-8").read().split('\npart = os.environ')[0])


def flow_of(q):
    x = ATT[q["code"]][q["now"]]
    s = (x or {}).get("수급5") or {}
    return (s.get("외국인") or 0) + (s.get("투신") or 0)


def skip_at(hhs):
    def f(c, b, p, k):
        if HH[c][k] in hhs:
            return 0
        return exit_rule(c, b, p, k)
    return f


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 32회차({part}): 옮기기 ⑤ ({len(data)}종목) ==", flush=True)
if part == "1":
    go2("비킬 차례: 수급 약한 것부터", key=flow_of)
    go2("비킬 차례: 수급 강한 것부터", key=lambda q: -flow_of(q))
else:
    go2("09:00 칸에선 팔기 판단 안 함", ex=skip_at({"0900"}))
    go2("15:15 칸에선 팔기 판단 안 함", ex=skip_at({"1515"}))
print("끝", flush=True)
