"""B3 — 봇 강화(docs/RL-BOTS.md): 15분봉(22회차 최종 후보) 후보 거르기 — 1일봉 B1과 다른 쪽 수급(가르침 문에 없는 투자자).
그 봉 재료(ATT · 전날까지 5일 수급 합 · 공시 20일)로: 연기금 5일 순매수 > 0 · 사모 5일 순매수 > 0 · 기관 5일 순매수 < 0 이면 안 삼.
(희석 · 자사주 공시 거르기는 26회차 q027에서 이미 짐 → 다시 안 함.) 한투 1년 161종목 · 씨앗 16 · 두 반 · 씨앗 폭보다 큰 차이만 믿음.
python research/z027.py
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
os.environ["Q_PART"] = "none"
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])

s5 = lambda x, col: ((x or {}).get("수급5") or {}).get(col)
print(f"== B3: 15분봉 후보 수급 거르기 ({len(data)}종목) ==", flush=True)
go("최종 후보 그대로")
go("연기금 5일 순매수 > 0 거르기", with_cut(lambda x: (s5(x, "연기금") or 0) > 0))
go("사모 5일 순매수 > 0 거르기", with_cut(lambda x: (s5(x, "사모") or 0) > 0))
go("기관 5일 순매도 거르기", with_cut(lambda x: (s5(x, "기관") or 0) < 0))
print("끝", flush=True)
