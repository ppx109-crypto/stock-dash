# BRK-FLOW-0044 개발 기록(진 것까지 모두 · 번호 = evals.jsonl STARTED 번호)

- 계획: PLAN.md round 3(GPT #199 6096543686 '계획 인정') · 도구 research/brk_dev.py · 실행기 research/brk_rules.py(PLAN의 좌표 하강 · 멈춤 · 덜어냄을 코드로 그대로 따름)
- 축 · 값(PLAN round 2 고침 1): A 돌파 창 20 · 40 · 60 · 120 / B1 수급 창 3 · 5 · 10 / B2 수급 칸 FT(외국인 + 투신) · F(외국인) · FI(외국인 + 기관) / C 시장 거르기 none · br40 · br50 · ix200 / D1 익절 5 · 8 · 12 / D2 손절 5 · 7 · 10 / D3 기간 10 · 20 / E 칸 2 · 3
- R0: 돌파 60 · 수급 5일 FT · 거르기 없음 · +5 / −7 / 10일(next_exit) · 2칸 · 순서 20일 상대 강세 · t 신호 → t + 1 종가 체결 · align_days · settle_end
