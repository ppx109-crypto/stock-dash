"""15분봉 22회차 — 21회차 가장 나은 판에서 하나씩 빼 보기: ① 정배열 사기의 +2% 거르기 ② 10:45 사기의 +2% 거르기 ③ 10:45 사기의 시장 −1% 쉼.
161종목 · 씨앗 16. Q_PART=1: ① 뺌 · ② 뺌 / Q_PART=2: ③ 뺌(=21회차 '모든 사기 +2%') 대신 시장 −1%를 정배열 사기에도.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])


def entry3(al_up=0.02, nn_up=0.02, nn_mkt=-0.01, al_mkt=None):
    def f(c, b):
        dr, mk = nan0(DR[c]), nan0(MKT[c])
        al = e_align(c, b).copy()
        if al_up is not None:
            al &= ~(dr > al_up)
        if al_mkt is not None:
            al &= ~(mk < al_mkt)
        nn = ctx_now(c, b) & (HH[c] == "1045")
        if nn_up is not None:
            nn &= ~(dr > nn_up)
        if nn_mkt is not None:
            nn &= ~(mk < nn_mkt)
        m, seen = np.zeros(len(al), bool), set()
        for k in np.flatnonzero(al | nn):
            if DAY[c][k] not in seen:
                m[k] = True
                seen.add(DAY[c][k])
        return m
    return f


part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 22회차({part}): 하나씩 빼 보기 ({len(data)}종목) ==", flush=True)
if part == "1":
    run3("① 정배열 사기 +2% 거르기 뺌", entry3(al_up=None))
    run3("② 10:45 사기 +2% 거르기 뺌", entry3(nn_up=None))
else:
    run3("시장 −1% 쉼을 정배열 사기에도", entry3(al_mkt=-0.01))
print("끝", flush=True)
