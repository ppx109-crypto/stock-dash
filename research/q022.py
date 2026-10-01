"""15분봉 21회차 — 20회차(신호 하나하나): 정배열 신호도 '오늘 +2% 위'면 두 반 모두 나쁨(앞 이김 28% · 뒤 0/7), 09:30 ~ 10:30 정배열 신호도 약함.
그래서 '오늘 +2% 위면 안 삼'을 정배열 신호에도 넓히고(그날 그 뒤 신호 · 10:45 사기는 다시 볼 수 있음), 시장 −1% 쉼과 합쳐 봄. 161종목 · 씨앗 16.
Q_PART=1: 모든 사기에 +2% / + 시장 −1%(10:45만) · Q_PART=2: 위 둘째 판 비용 0.5% · 09:30 ~ 10:30 정배열 신호도 뺌.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])


def entry2(noon="1045", up=0.02, mkt=None, skip_mid=False):
    """그날 처음 한 번: 정배열 된 봉(오늘 +up 위 아님 · skip_mid면 09:30 ~ 10:30 봉 뺌) 또는 noon 봉(오늘 +up 위 아님 · 시장 mkt 아래 아님)."""
    def f(c, b):
        al = e_align(c, b).copy()
        dr = nan0(DR[c])
        if up is not None:
            al &= ~(dr > up)
        if skip_mid:
            al &= ~((HH[c] >= "0930") & (HH[c] < "1045"))
        nn = ctx_now(c, b) & (HH[c] == noon)
        if up is not None:
            nn &= ~(dr > up)
        if mkt is not None:
            nn &= ~(nan0(MKT[c]) < mkt)
        m, seen = np.zeros(len(al), bool), set()
        for k in np.flatnonzero(al | nn):
            if DAY[c][k] not in seen:
                m[k] = True
                seen.add(DAY[c][k])
        return m
    return f


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 21회차({part}): +2% 거르기를 모든 사기에 ({len(data)}종목) ==", flush=True)
if part == "1":
    run3("모든 사기 +2% 위면 안 삼", entry2())
    run3("모든 사기 +2% + 10:45 시장 −1% 쉼", entry2(mkt=-0.01))
else:
    run3("모든 사기 +2% + 시장 −1% · 비용 0.5%", entry2(mkt=-0.01), cost=0.5)
    run3("모든 사기 +2% + 시장 −1% + 09:30~10:30 뺌", entry2(mkt=-0.01, skip_mid=True))
print("끝", flush=True)
