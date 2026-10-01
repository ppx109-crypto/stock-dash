"""15분봉 36회차 — 거꾸로 옮기기: 15분봉에서 찾은 두 거르기('그날 이미 +2% 위면 안 삼' · '장중 시장 흐름 −1% 아래면 안 삼')를
운영 중인 1시간봉 최고 규칙에 얹으면 나아지나. 같은 15분봉 자료를 1시간으로 묶어(Q_BARS=1h) 돌림. 161종목 · 씨앗 16.
1시간봉 규칙: 1시간봉 EMA 정배열 된 봉 다음 시가, 없으면 11시 봉 뒤(12:00) — 재료는 그 봉이 닫힌 때까지.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])


def entry_h(noon=NOON, up=None, mkt=None):
    def f(c, b):
        dr, mk = nan0(DR[c]), nan0(MKT[c])
        good = np.ones(len(b["t"]), bool)
        if up is not None:
            good &= ~(dr > up)
        if mkt is not None:
            good &= ~(mk < mkt)
        al = e_align(c, b) & good
        nn = ctx_now(c, b) & (HH[c] == noon) & good
        m, seen = np.zeros(len(al), bool), set()
        for k in np.flatnonzero(al | nn):
            if DAY[c][k] not in seen:
                m[k] = True
                seen.add(DAY[c][k])
        return m
    return f


print(f"== 15분봉 36회차: 15분봉 거르기를 1시간봉 규칙에 (같은 자료 1시간 묶음 · {len(data)}종목 · 정오 봉 {NOON}) ==", flush=True)
run3("1시간봉 최고 규칙 그대로", entry_h())
run3("+ 그날 +2% 위면 안 삼", entry_h(up=0.02))
run3("+ 장중 시장 −1% 아래면 안 삼", entry_h(mkt=-0.01))
run3("+ 둘 다", entry_h(up=0.02, mkt=-0.01))
run3("+ 둘 다 · 정오 대신 10시 봉 뒤(11:00)", entry_h(noon="1000", up=0.02, mkt=-0.01))
print("끝", flush=True)
