# PR #124 검토 — REPLAY-EMPTY-LEDGER-METRIC-GATE-0001

- 검토 입력: PR #124
- 고정 head: `13e031b32186aca7e1286bb4b9119bcd9cd39700`
- 상태: open / non-draft
- 결과 판정: **READY — 합성 빈 원장 지표 게이트 계약에만 한정**
- 프로그램 판정: `PAPER_VALIDATION_READY=false`

## 수용 근거

1. PR #122의 음성대조에서 빈 원장이 `IndexError`를 내는 결함을 재현했다.
2. 새 게이트는 `blocked_from → invalid snapshot → empty snapshots → metrics` 순서를 고정했다.
3. 빈 원장은 `PERF_BLOCKED / from=null / NO_SNAPSHOTS`이고 모든 성과 지표가 null이며 지표 함수 호출은 0이다.
4. 기존 M1~M8 회귀 18항목, 직렬화·반복 결정성, AST 호출경계가 제출 증거에서 모두 통과했다.
5. 공식 실행은 사전등록 후 1회였고 실제 사건·시세·NAV·성과·외부 호출은 없었다.

## 제한과 다음 결함 후보

- valid snapshot 1개에서 일별 수익률은 빈 배열인데 `all_zero=true`인 것은 0수익의 실측 증거가 아니다.
- 현재 게이트는 snapshot 존재 여부만 보며 거래일 사이 누락을 탐지하지 않는다.
- 누락 탐지에는 권위 있는 기대 거래일 집합과 snapshot 생산 계약이 먼저 필요하다. 저장소에서 그 출처·시점·개정판·소비 연결을 확인하지 않은 채 평일 계산이나 임의 holiday 목록을 넣을 수 없다.
- 실제 가격기준, available_at, 정정 계보, 실제 비용·체결·NAV·성과는 계속 검증되지 않았다.

따라서 다음 한 단계는 구현이 아니라 **기존 저장소 읽기 전용 거래일·snapshot provenance 감사**다. 증거가 없으면 `NEEDS_DATA`이며 무증거 상태를 유효성 없음으로 바꾸지 않는다.
