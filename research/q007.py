"""15분봉 6회차 — 5회차 고원(+2 ~ 3%에서 두 반 모두 나음, +4%부터 뒤 반 짐)을 더 낮은 쪽으로: 0 · 1 · 1.5 · 2%,
그리고 '−1% ~ +2% 사이일 때만 10:45에 삼'(너무 내린 날 · 많이 오른 날 모두 거름) · +2% 비용 0.5%. 씨앗 16 · 두 반.
"""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q005.py", encoding="utf-8").read().split('best = entry(noon="1045")')[0])

print(f"== 15분봉 6회차: 10:45 사기 문턱 더 낮게 ({len(data)}종목) ==", flush=True)
for th in (0.0, 0.01, 0.015, 0.02):
    run3(f"10:45 사기: 오늘 +{th * 100:g}% 위면 안 삼", noon_cut(lambda c, k, th=th: nan0(DR[c])[k] > th))
run3("10:45 사기: −1% ~ +2% 사이만", noon_cut(lambda c, k: not (-0.01 <= nan0(DR[c])[k] <= 0.02)))
run3("+2% · 비용 0.5%", noon_cut(lambda c, k: nan0(DR[c])[k] > 0.02), cost=0.5)
print("끝", flush=True)
