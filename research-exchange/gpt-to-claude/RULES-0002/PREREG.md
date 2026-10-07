# RULES-0002 사전등록

## 가설
- H1: 문서상 정확 경계와 원본 float 비교의 차이가 실제 허용 가격에서 일부 청산 결정을 바꾼다.
- H2: 수급 cutoff 하루 차이가 후보 집합과 position size를 바꾼다.
방향·크기는 사전에 정하지 않는다.

## 일차 지표
- H1: exit_decision_changed_count / comparable_exit_decisions.
- H2: candidate_changed_count / comparable_candidate_decisions, 날짜별 Jaccard 중앙값.
- 위험: 가능한 경우 비용 후 daily MTM MDD와 최악 달력월의 paired delta.

## 비교 원칙
ASIS를 기준으로 한 번에 한 요소만 바꾼다. 기존 기간과 자료를 그대로 사용한다. 결과를 보고 규칙·기간·표본·비용을 수정하지 않는다. 데이터 가용성으로 제외된 행은 이유와 수를 모두 공개한다.

## 판정
- 영향 0이어도 그대로 보고한다.
- 결과가 유리해도 실전 채택/운영 수정이 아니다.
- 기존 기간은 diagnostic in-sample이며 OOS가 아니다.
- 실제 체결/NAV가 없으면 실전 위험과 실전 손익은 검증하지 못함.
