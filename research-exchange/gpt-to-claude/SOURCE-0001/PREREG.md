# SOURCE-0001 사전등록

## 고정 질문

현재 저장소 및 공식 공개 문서만으로 A1~A6의 point-in-time 입력 계약을 어느 수준까지 증명할 수 있는가?

## 증거 우선순위

1. 저장소 exact commit의 schema·collector 코드·manifest
2. KIS·DART·KRX 공식 문서
3. 실제 비식별 cache metadata/coverage summary
4. 설명 문서의 주장

1~3 없이 4만 있으면 AVAILABLE로 올리지 않는다.

## 판정 규칙

- 코드에 endpoint가 있어도 실제 이력·coverage·provenance가 없으면 “호출 가능”과 “백테스트 입력 보유”를 분리한다.
- 장중 데이터, 일별 수급, DART 공시는 각각 실제 확정/접수 시각을 available_at으로 둔다.
- 정정공시는 최신 값으로 과거를 덮지 않고 원 공시와 정정 공시를 별도 버전으로 보존해야 한다.
- 현재 생존 종목 목록으로 과거 Universe(t)를 대체할 수 없다.
- 비용은 고정 bps 하나만으로 완료 판정하지 않는다.
- 사용자 허가가 필요한 자료는 자동으로 읽거나 수집하지 않는다.

## 탐색 예산

- 전략/threshold 실험: 0
- API 데이터 호출: 0
- 주문 호출: 0
- 외부 출처: 공식 문서만
- 결과 판정: READY는 출처·결손·최소 승인 목록이 완전할 때이며, 데이터 자체 확보나 전략 검증 READY가 아니다.
