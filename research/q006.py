"""15분봉 5회차 — 4회차 후보 '10:45 사기: 오늘 +3% 위면 안 삼'의 고원(2 · 2.5 · 3 · 4 · 5%) · 비용 0.5% · 장중 시장 흐름 거르기와 함께.
이미 많이 오른 날 늦게(11:00) 따라 사지 않는 것. 정배열 신호로 사는 것은 그대로. 씨앗 16 · 두 반.
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q005.py", encoding="utf-8").read().split('best = entry(noon="1045")')[0])

print(f"== 15분봉 5회차: 10:45 사기 '오늘 많이 올랐으면 안 삼' 고원 ({len(data)}종목) ==", flush=True)
run3("기준: 10:45 봉 뒤", entry(noon="1045"))
for th in (0.02, 0.025, 0.03, 0.04, 0.05):
    run3(f"10:45 사기: 오늘 +{th * 100:g}% 위면 안 삼", noon_cut(lambda c, k, th=th: nan0(DR[c])[k] > th))
run3("+3% · 비용 0.5%", noon_cut(lambda c, k: nan0(DR[c])[k] > 0.03), cost=0.5)
run3("+3% + 장중 시장 −0.5% 아래 안 삼", noon_cut(lambda c, k: nan0(DR[c])[k] > 0.03 or nan0(MKT[c])[k] < -0.005))
run3("0회차(정오 사기) 견줌", entry())
print("끝", flush=True)
