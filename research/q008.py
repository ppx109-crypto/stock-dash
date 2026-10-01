"""15분봉 7회차 — 0회차에서 앞 · 뒤 모두 나았던 'EMA A4(1시간봉과 같은 길이 = 15분봉 20 · 80 · 240 · 480 · 720)'에
1 · 4 · 5 · 6회차 사는 때 후보(10:45 봉 뒤 · 10:45 사기 거르기)를 얹음. Q_SPAN=A4로 돌림. 씨앗 16 · 두 반.
견줌: 같은 15분봉 자료를 1시간으로 묶은 1시간봉 최고 규칙 = 앞 137.0 · 뒤 22.2(142종목, q001).
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q005.py", encoding="utf-8").read().split('best = entry(noon="1045")')[0])

print(f"== 15분봉 7회차: EMA {os.environ.get('Q_SPAN', 'A')} + 사는 때 후보 ({len(data)}종목) ==", flush=True)
run3("정오(11:45 봉 뒤) 그대로", entry())
run3("10:45 봉 뒤", entry(noon="1045"))
run3("10:45 + 오늘 +2% 위면 안 삼", noon_cut(lambda c, k: nan0(DR[c])[k] > 0.02))
run3("10:45 + 오늘 +3% 위면 안 삼", noon_cut(lambda c, k: nan0(DR[c])[k] > 0.03))
run3("10:45 + −1% ~ +2% 사이만", noon_cut(lambda c, k: not (-0.01 <= nan0(DR[c])[k] <= 0.02)))
run3("10:45 + +2% · 비용 0.5%", noon_cut(lambda c, k: nan0(DR[c])[k] > 0.02), cost=0.5)
print("끝", flush=True)
