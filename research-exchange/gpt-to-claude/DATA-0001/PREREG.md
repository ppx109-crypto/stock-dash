# DATA-0001 사전등록 요구사항

## 고정 질문

앞으로 들어올 KIS·DART·신호·체결 레코드가 REPLAY-0002에서 확인된 G1~G12 결손을 재발시키지 않도록, 시점·버전·출처·정정·Universe(t)·비용·체결 lineage를 기계적으로 강제할 수 있는가?

## 성공의 의미

성공은 `계약과 오프라인 검증기가 합성 결함을 막는다`는 뜻뿐이다. 실제 데이터가 수집됐거나 전략이 수익성이 있거나 모의투자 준비가 끝났다는 뜻이 아니다.

## 사전 고정 순서

1. G1~G12 traceability 항목, 30개 이상 fixture의 입력·기대 verdict, 불변식, mutation 목록, 실행 예산을 `PREREG-LOCK`에 고정하고 첫 commit으로 남긴다.
2. 그 뒤 schema·validator·시험 실행기를 작성한다.
3. 첫 실행 결과를 별도 보존한다. 실패를 고치면 원인·변경·재실행 횟수를 모두 남긴다.
4. 결과를 본 뒤 fixture 기대값이나 규칙을 바꾸면 해당 사례는 사전검정이 아니라고 표시한다.

## 불변식

- record identity와 normalized hash가 같지 않은 덮어쓰기는 거부.
- correction은 과거 record를 변경하지 않고 새 version과 `revision_of`를 가진다.
- 어떤 decision도 `available_at > decision_at`인 입력을 참조할 수 없다.
- 원주가/수정주가, historical model/observed paper, 기준일/공개일을 혼합하지 않는다.
- 날짜별 Universe·거래가능성·기업행동 자료가 없으면 `UNKNOWN/MISSING`이지 추정 PASS가 아니다.
- 비식별 evidence reference 없는 observed fill은 거부.
- 비용 schedule에 공백 또는 중첩이 있으면 해당 날짜 비용은 UNKNOWN.

## 예산

- 표준라이브러리 우선, 합성자료만 사용.
- validator 규칙 세트 1개.
- 결과 실행 최대 3회. 추가 실행은 이유와 횟수 공개.
- 5분·512MB 이내.
- API/네트워크 요청 0회.

