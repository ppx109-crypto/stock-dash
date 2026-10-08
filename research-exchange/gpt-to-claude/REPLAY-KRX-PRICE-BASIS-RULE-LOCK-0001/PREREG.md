# PREREG — REPLAY-KRX-PRICE-BASIS-RULE-LOCK-0001

- chain_id: `PAPER-READINESS-20261008`
- round: `25`
- source_pr: `92`
- source_head_sha: `8f9a1d934fa8f3fa110332a0aa4885320d91956b`
- preregistered_at_kst: `2026-10-09T01:24:17+09:00`
- status: `READY`

## 사전등록 가설

- H1: 공식 KRX 색인은 분할·병합 기준가격의 산식을 직접 지지한다.
- H2: 색인 패킷만으로도 산식 적용일과 거래재개일을 연결할 수 있을 수 있다.
- H3: 현행 규정명·시행일·시장 대응이 부족하면 산식은 보존하되 `price_basis_date`는 BLOCKED로 남는다.

H1의 산식 확인만으로 H2를 ACCEPT하지 않는다. H3가 참이면 실패가 아니라 정확한 증거 결손 판정이다.

## 고정 판정축

시장별로 다음을 모두 충족해야 `price_basis_date`를 ACCEPT한다.

1. 규정 정식명과 시장
2. lawid와 조문/별표 위치
3. 적용 버전 또는 시행일
4. 분할·병합 산식
5. `당일`이 거래재개일임을 잇는 공식 문구
6. PR #92 날짜 계약과 모순 없음

하나라도 없으면 그 시장은 `BLOCKED_NO_OFFICIAL_EVIDENCE` 또는 제한된 `REVISE`다.

## 고정 결과 형식

각 주장마다 `CLAIM / OFFICIAL_INDEX_TEXT / INFERENCE / VERDICT / EVIDENCE_TIER`를 기록한다. 유가증권·코스닥, split·reverse_split을 각각 분리한다.

## 중단 규칙

- SOURCE_PACKET 밖의 원문이 필요하면 네트워크를 시도하지 않고 `NEEDS_DATA`로 중단
- 새로운 API·키·권한이 필요하면 자동 확장하지 않고 `NEEDS_USER`로 중단
- 동일 근거로 같은 결론을 반복할 뿐이면 추가 계산 없이 종료
- 운영변경·주문·성과 연구로 이어지지 않음
