# COST-REPLAY-0001 사전등록

검정 대상은 비용 교정의 정확성과 고정 원장 손익차이다. 알파·규칙·파라미터의 최적화가 아니다.

- 입력 source: #29 / d8024b5599a34a456e4ec99cdd2af6051ebb0904
- 세금: TASK의 날짜·상품별 명시 계약
- 비교: 동일 원장의 기존 비용 vs 교정 세금, 그 밖의 가정 고정
- 전략 실험수: 0
- 신규 수집/API/주문: 0
- 원장/NAV 불충분: NEEDS_DATA로 종료; 합성 예시는 단위 테스트만
- fee/slippage/impact는 검증 전 가정. 실제 계좌 요율 선택 금지
- 결과를 확인하기 전 사용 원장 hash·기간·상품 분류·분석 가능 지표를 PREREG-LOCK에 기록
- 통과 기준: 경계 테스트와 UNKNOWN 거부, 고정 원장 차이 재현, 허위 포트폴리오/OOS 주장 없음
- paper_validation_ready=false, live_approval=false
