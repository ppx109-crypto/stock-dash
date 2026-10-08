# PORTFOLIO-CAP-0001 사전등록

- phase: ALPHA / Train-only
- source: PR #62 head `f68eab60c9e8949dbf58ec6d1528e710bb0cadc0`
- hypothesis: 소액계좌에서 매수 25% 상한과 30% 초과 시 다음 봉 정수 1주 이상 축소가 R30의 0주 무작동을 제거하고 집중·MDD를 제한한다.
- experiment budget: 정확히 4판(C25 × seed 0..3)
- capital: 2,500,000원 × 4
- cost: 2배
- fixed inputs/period: PR #62와 동일
- comparison: PR #62 저장 R4_ACTUAL, 재실행 없음
- multiple testing: 단일 가설·단일 숫자쌍, 추가 숫자 시험 금지

## LOCK 조건

4판 보존 통과, 하루·월 -15% 초과 0, MDD ≥ -15%, 최대 단일종목 <30%, 비용 후 끝 금액 >1천만원을 모두 만족하면 `TRAIN_CANDIDATE_LOCKED`입니다. 그 외는 `AXIS_ENDED`입니다.

결과를 본 뒤 조건이나 25/30을 바꾸지 않습니다. 통과해도 미사용 OOS 검증 전에는 PAPER_VALIDATION_READY나 실전 후보가 아닙니다.
