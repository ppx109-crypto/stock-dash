"""15분봉 19회차 — 18회차(신호 하나하나): '오늘 +2% 위면 안 삼'은 앞 반만 진짜 이득(뒤 반은 좋은 신호를 거름),
'장중 시장 −1% 아래면 쉼'은 두 반 모두 나쁜 신호를 거름. 그래서 10:45 봉 뒤 사기에 시장 거르기만 얹은 판을 계좌로 봄. 161종목 · 씨앗 16.
Q_PART=1: 시장 −1% · −1.25% 아래 쉼 / Q_PART=2: 시장 −1% + 비용 0.5% · 시장 −0.75% 아래 쉼.
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q009.py", encoding="utf-8").read().split('span = os.environ')[0])

part = os.environ.get("Q_PART", "1")
print(f"== 15분봉 19회차({part}): 10:45 사기 + 장중 시장 거르기만 ({len(data)}종목) ==", flush=True)
mk = lambda x: cut_at("1045", lambda c, k: nan0(MKT[c])[k] < x)
if part == "1":
    run3("10:45 + 시장 −1% 아래 쉼", mk(-0.01))
    run3("10:45 + 시장 −1.25% 아래 쉼", mk(-0.0125))
else:
    run3("10:45 + 시장 −1% 아래 쉼 · 비용 0.5%", mk(-0.01), cost=0.5)
    run3("10:45 + 시장 −0.75% 아래 쉼", mk(-0.0075))
print("끝", flush=True)
