# TASK — REPLAY-KOSPI-INTEGRATED-SNAPSHOT-LOCK-0001

- task_id: `REPLAY-KOSPI-INTEGRATED-SNAPSHOT-LOCK-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 27
- status: READY
- source_pr: 96
- source_head_sha: `e6c4f9d56621f4cc50b913ba86be98444ed9728e`

## 목적

고정된 공식 KRX 색인 스냅샷만 사용해 다음 두 축을 독립 판정한다.

1. `lawid=000111`의 정식 규정명이 `유가증권시장 업무규정 시행세칙`인지.
2. 통합본 머리글의 최종 일부개정일·규정번호·시행일과 제30조 제1항 제6호 문구를 함께 보았을 때, Train(2025-09-18~2026-03-31)에 해당 산식이 시행 중이었다고 잠글 수 있는지.

## 허용 범위

- 이 PR의 `SOURCE_PACKET.md`와 기존 PR #96 산출물 읽기
- 문자열·날짜 포함관계의 오프라인 비교
- 주장, 공식 색인 발췌, 추론을 분리한 보고서 작성
- 별도 불변 `[클로드 결과]` PR 제출

## 판정 축

### A — 규정 정체성

- ACCEPT: 같은 공식 KRX 색인 스냅샷의 URL에 `lawid=000111`이 있고 정식 규정명이 직접 표시됨.
- REVISE: 연결은 추론으로만 가능.
- BLOCKED: 식별 불가 또는 모순.

### B — Train 시행본·산식

- ACCEPT: 같은 통합 스냅샷에서 최종 일부개정일·시행일이 Train 시작 전이고, 크롤 시점이 Train 종료 후이며, 제30조 제1항 제6호의 정확 문구가 존재하고, 머리글상 더 늦은 개정이 없음.
- REVISE: 위 요소 중 하나가 간접적이거나 서로 다른 스냅샷이라 연결에 추론이 필요.
- BLOCKED: 날짜·문구가 연결되지 않거나 모순.

A와 B 모두 ACCEPT일 때만 READY. 그 외는 BLOCKED.

## 반드시 공개할 것

- 공식 색인 발췌와 GPT 요약을 구분
- `Published`, `Crawled`, 일부개정일, 시행일을 서로 혼동하지 않음
- Train 날짜 포함관계
- 증거 등급과 한계
- 실행 횟수와 미수행 항목
- PR #96 head를 제출 직전 재확인

## 금지

- 외부 URL·네트워크·API·키·신규수집·캐시 확장
- KOSDAQ, 비율 방향, 가격 기준일, 거래재개일, 최초 매도가능일 연구
- replay·백테스트·성과·threshold·새 알파 탐색
- 모의/실계좌 주문, 운영 봇·전략·배분·워크플로·인증 변경
- 새 Claude 세션·탭·Routine, 자동병합
- `+19.90%` 또는 NAV를 검증됐다고 표현

## 완료조건

`PREREG.md`, `REPORT.md`, `manifest.json`, `receipt.json`, 판정 evidence를 결과 PR 개설 전에 완성한다. 결과 status는 READY 또는 BLOCKED만 허용한다.
