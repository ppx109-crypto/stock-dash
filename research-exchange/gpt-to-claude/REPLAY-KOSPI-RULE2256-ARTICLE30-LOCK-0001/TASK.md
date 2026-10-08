# REPLAY-KOSPI-RULE2256-ARTICLE30-LOCK-0001

- task_id: `REPLAY-KOSPI-RULE2256-ARTICLE30-LOCK-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: `28`
- status: `READY`
- source_pr: `98`
- source_head_sha: `c5abe6943aefa031109a23aec12311dd7342e5e9`
- issued_at_kst: `2026-10-09T01:55:06+09:00`
- stage: `REPLAY`

## 목적

규정 제2256호(일부개정 2024-10-29, 시행 2024-11-04)의 공식 KRX 시행본과
제30조 제1항 제6호의 다음 정확 문구를 **같은 버전에서 직접 결속**한다.

> 주식분할 또는 주식병합된 종목은 전일종가에 분할 또는 병합의 비율을 곱한 가격으로 한다.

## 허용 범위

1. 이 PR의 `SOURCE_PACKET.md`와 PR #98의 REPORT/manifest/evidence만 읽는다.
2. 제공된 공식 KRX 색인 캡처와 URL 구조를 오프라인으로 대조한다.
3. 규정 제2256호 시행본 또는 동일 버전 식별자와 제30조 제1항 제6호가 직접 함께 나온 근거만 채택한다.
4. 주장·코드·실측을 분리해 REPORT/manifest/evidence/receipt를 완성한다.
5. 결과는 `READY` 또는 `BLOCKED`만 사용한다.

## 금지

- 새 외부 URL 열기, 네트워크/API/키/인증 사용, 새 수집·캐시·크롤
- 백테스트·리플레이·threshold 탐색·성과/NAV 재계산
- KOSDAQ, 비율 방향, 가격 기준일, 거래재개일, 최초 매도가능일로 범위 확장
- 모의/실계좌 주문 API, 현재 봇·전략·배분·워크플로·인증 변경
- 자동병합, 비밀·계좌·원본 계좌 응답·비공개 세션 식별자 기록
- 현재 결과 브랜치에 후속 연구 추가. 결과 제출 후에는 receipt 보정 외 변경 금지

## 완료 조건

다음을 모두 충족하면 `READY`:

1. 공식 KRX 근거가 규정 제2256호 또는 2024-11-04 시행본임을 직접 식별한다.
2. 같은 버전에서 제30조 제1항 제6호의 정확 문구를 직접 제시한다.
3. 개정·시행일이 Train 시작 2025-09-18보다 앞선다는 단순 날짜 비교를 공개한다.
4. 근거 등급을 과장하지 않고, 현재 통합본 색인인지 시행본 직접 원문인지 구분한다.
5. A(규정 정체성) ACCEPT는 보존하고 B만 ACCEPT로 갱신한다.
6. KOSDAQ·비율 방향·가격 기준일·거래재개일·최초 매도가능일과 NAV/성과는 미검증으로 유지한다.

하나라도 직접 결속되지 않으면 `BLOCKED`:

- 반복 검색이나 추정 URL 실행 없이 멈춘다.
- `NEEDS_DATA`에 부족한 공식 버전 식별자/발췌를 정확히 한 줄로 적는다.
- 기존 자료로 해결되지 않는다면 같은 과제를 숫자만 바꿔 반복하지 않는다.

## 제출 계약

- 결과는 별도 브랜치/PR로 제출한다.
- PR을 열기 전에 REPORT, manifest, evidence, receipt를 완성한다.
- receipt에 input PR 99의 실제 head SHA, source PR 98/head SHA, prereg commit, 상태를 기록한다.
- `result_pr`은 제출 전 알 수 없으므로 null이어도 된다. PR 번호는 본문에 기록한다.
