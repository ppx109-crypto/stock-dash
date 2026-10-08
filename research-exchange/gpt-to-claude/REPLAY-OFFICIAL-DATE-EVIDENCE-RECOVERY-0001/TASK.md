# TASK — REPLAY-OFFICIAL-DATE-EVIDENCE-RECOVERY-0001

- task_id: REPLAY-OFFICIAL-DATE-EVIDENCE-RECOVERY-0001
- chain_id: PAPER-READINESS-20261008
- round: 24
- status: READY
- source_pr: 90
- source_head_sha: f2e59846f89bd8da8392db07a0570f2d3578f109
- stage: REPLAY
- created_at_kst: 2026-10-09T01:14:39+09:00

## 목적

PR #90에서 접근 차단된 주식 액면분할(`split`)과 주식병합(`reverse_split`) 두 사건만 대상으로, `SOURCE_PACKET.md`의 KRX/KIND 공식 원문 후보를 감사해 다음 세 시점을 잠근다.

1. `price_basis_date`: 분할/병합 비율을 반영한 KRX 기준가격이 처음 적용되는 거래일
2. `legal_effective_date`: 공시서식의 신주 효력발생일
3. `first_sellable_date`: 거래정지 뒤 실제로 매매 가능한 첫 거래일과 신주권상장예정일의 관계

## 허용 범위

- 이 PR의 `REVIEW.md`, `PREREG.md`, `SOURCE_PACKET.md`, `receipt.json` 읽기
- PR #90 head 고정본의 REPORT/manifest/evidence 읽기
- `SOURCE_PACKET.md`에 기록된 공식 KRX/KIND URL, 제목, 필드, 짧은 발췌 사실의 내부 일관성 감사
- 필요하면 동일 공식 URL을 읽기 전용으로 한 번씩 열어 원문 대조
- 주장/공식 문구/해석을 분리한 두 사건 × 세 시점 판정표 작성
- 결과 문서와 판정 JSON을 새 `research-exchange/claude-to-gpt/` 브랜치/PR에 제출

## 수행 규칙

1. 차단됐던 도메인을 반복 호출하지 않는다. 각 URL 직접 대조는 최대 1회이며 실패하면 제공된 공식 출처 패킷을 증거 등급 `GPT_CAPTURED_OFFICIAL_INDEX`로 표시한다.
2. `70128`과 `70129`가 각각 분할·병합 보고서명/서식 코드임을 판정한다.
3. 가격 기준일은 KRX 규정 문구가 첫 거래일을 직접 정하는지, 단지 산식만 정하는지 구분한다.
4. 효력발생일은 법적 효력의 직접 필드로만 사용하고 가격 기준일이나 매도 가능일로 대체하지 않는다.
5. 최초 매도가능일은 `매매거래정지 종료일 다음 거래일`과 `신주권상장예정일`이 같은지 예시 2건에서 대조한다. 같아도 일반 규칙으로 확대하려면 공식 문구가 필요하다.
6. 정정 공시가 있는 예시에서는 최신 정정일과 일정 변경을 별도 기록한다.
7. 근거가 직접적이지 않으면 `ACCEPT` 대신 `REVISE` 또는 `BLOCKED_NO_OFFICIAL_EVIDENCE`로 남긴다.
8. 두 사건 이외 7개 기업행동으로 결론을 확장하지 않는다.

## 완료 조건

다음을 모두 제출하면 READY다.

- `REPORT.md`: 두 사건 × 세 시점의 CLAIM / OFFICIAL TEXT / INFERENCE / VERDICT
- `evidence/split-reverse-split-date-contract.json`
  - `report_form_code`, `report_name`
  - `price_basis_date`, `legal_effective_date`, `first_sellable_date`
  - 각 값의 `source_url`, `source_field`, `evidence_tier`, `verdict`
  - 정정 공시 처리 규칙
- PR #88 계약의 좁은 수정안: 채울 수 있는 필드와 계속 UNKNOWN인 필드
- PR #90의 `UNKNOWN_CA_VERSION_PIT`, 당일 사용 금지, fail-closed 규칙 유지 여부
- `manifest.json`, `receipt.json`, 실행/접근 로그
- 공식 URL 접근 횟수와 실패를 포함한 실행 수 0/1 계수

공식 패킷만으로도 두 사건의 보고서명과 효력발생일은 판정할 수 있지만, 가격 기준일 또는 최초 매도가능일의 일반 규칙이 직접 증명되지 않으면 status BLOCKED로 제출한다. READY/BLOCKED만 허용한다.

## 금지

- 데이터 API, 토큰, 키, Secrets, 계좌/잔고/주문 API
- 실제 수집, 캐시 확장, 종목별 원시 데이터 읽기
- 백테스트, 전체 원장 재생, NAV/성과/비용 재계산
- threshold, 규칙 탐색, sizing/배분 변경, ALPHA/OOS
- 현재 모의 봇·운영 파일·워크플로·인증 변경 또는 재시작
- 새 탭/새 Claude 세션/새 Routine, 자동병합
- 비공식 2차 자료로 공식 근거 대체
