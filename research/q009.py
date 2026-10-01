"""15분봉 8회차 — 사는 시각은 정오(11:45 봉 뒤)로 두고 '오늘 +2 · 3% 위면 정오 사기 안 함'만 얹음(7회차: A4는 10:45로 당기면 나빠짐).
Q_SPAN=A와 A4로 각각 돌림. 씨앗 16 · 두 반.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q005.py", encoding="utf-8").read().split('best = entry(noon="1045")')[0])


def cut_at(noon, test):
    base = entry(noon=noon)

    def f(c, b):
        m = base(c, b).copy()
        al = e_align(c, b)
        for k in np.flatnonzero(m):
            if not al[k] and HH[c][k] == noon and test(c, k):
                m[k] = False
        return m
    return f


span = os.environ.get("Q_SPAN", "A")
print(f"== 15분봉 8회차: EMA {span} · 정오 사기 + 많이 오른 날 거르기 ({len(data)}종목) ==", flush=True)
for th in (0.02, 0.03):
    run3(f"정오 + 오늘 +{th * 100:g}% 위면 안 삼", cut_at("1145", lambda c, k, th=th: nan0(DR[c])[k] > th))
run3("정오 + +2% · 비용 0.5%", cut_at("1145", lambda c, k: nan0(DR[c])[k] > 0.02), cost=0.5)
run3("정오 그대로 · 비용 0.5%", entry(), cost=0.5)
print("끝", flush=True)
