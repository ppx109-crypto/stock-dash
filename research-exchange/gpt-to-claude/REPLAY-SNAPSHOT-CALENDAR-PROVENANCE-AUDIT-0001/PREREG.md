# PREREG — REPLAY-SNAPSHOT-CALENDAR-PROVENANCE-AUDIT-0001

- 입력 고정: PR #124 / `13e031b32186aca7e1286bb4b9119bcd9cd39700`
- 연구 유형: 기존 공개 저장소 정적·읽기 전용 provenance 감사
- 실행 상한: 코드·테스트·스크립트 실행 0회
- 외부 호출 상한: 데이터/API/웹 0회
- 결과 상태: 감사 완료 시 READY, 접근 결손으로 감사 자체 불완전 시 BLOCKED
- readiness 판정: 달력 계약 근거가 부족하면 NEEDS_DATA

## 사전 고정 감사 축

- 권위 있는 거래일/session source
- KST·시장·휴장·임시휴장·기간 경계
- source/version/revision/available_at
- snapshot day 생산과 저장
- 무보유·무시세·차단일·누락의 구분
- 완전성 gate와 성과 소비 연결
- 실제 Train/연구 구간 재현 가능성
- 기존 중복 연구 여부

## 사전 고정 산출 형식

각 행은 `component, claim_or_code_or_measurement, path, lines, blob_sha, producer, transformer, consumer, available_at, revision, classification, first_break, note` 필드를 가진다. 값이 없으면 null로 남기며 추정하지 않는다.

필수 연결 중 하나라도 `PRESENT_VERIFIED`가 아니면 snapshot 완전성 구현으로 진행하지 않고 최소 추가 자료만 보고한다. 실제 데이터가 없다는 사실은 전략 무효 판정이 아니다.
