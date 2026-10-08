# PR #120 검토 — REPLAY-CA-QUOTE-BASIS-GATE-0001

- task_id: REPLAY-BLOCKED-DAY-METRIC-GATE-0001
- chain_id: PAPER-READINESS
- round: 39
- status: READY
- source_pr: 120
- source_head_sha: 8ed1d7d24a7fd564c200f2978bd51659f1af4316
- reviewed_at_kst: 2026-10-09T03:35:17+09:00

## 판정

**합성 시세 가격기준 게이트 범위에 한해 READY**입니다.

- `process_day`의 시세 기준 검사가 사건 적용, 시세 대입, snapshot보다 먼저입니다.
- RAW 정상 케이스와 ADJUSTED·누락·빈 값·다른 문자열·혼합 차단 케이스가 고정 기대값과 일치했습니다.
- 차단 8건은 `apply_batch` 호출 0, 감시 상태 대입 0, 가격 변경 0, snapshot 증가 0이었습니다.
- PR #118 P1 및 PR #114 고정 fixture 11개는 기존 증거와 다른 칸 0이었습니다.
- 공식 실행 1회, actual_events=0, external_calls=0입니다.

이 판정은 합성 경계에만 해당합니다. 실제 시세 라벨 provenance, 실제 기업행위, 실제 NAV·성과는 검증하지 않았습니다. `performance_verified=false`, `nav_verified=false`, `paper_validation_ready=false`를 유지합니다.

## 주장·코드·실측 구분

- 주장: RAW 장부에 ADJUSTED/UNKNOWN 시세가 들어오는 날은 사건·시세·snapshot 전체를 먼저 차단합니다.
- 코드: source head의 `process_day` 143~151줄은 bad quote 검사와 조기 return 뒤에만 `apply_batch`, quote 대입, snapshot 추가를 둡니다.
- 합성 실측: Q1~Q8은 통과했습니다. Q2의 NAV 387,020→1,935,100은 PR #118 고정 합성 음성대조입니다.
- 실제 실측: 실제 사건·시세·포지션·NAV·외부 호출은 0입니다.

## 확인된 측정 결함

source head의 `perf(snaps)`는 snapshot 목록만 읽습니다.

- quote 기준 차단일에는 snapshot을 만들지 않습니다.
- 따라서 마지막 날이 차단되면 그 날은 `snaps`에 존재하지 않습니다.
- 이전 snapshot이 모두 valid라면 기존 `perf(snaps)`는 `blocked_from`을 보지 못하고 OK를 반환할 수 있습니다.
- 이는 일별 MTM·일/월 TWR·MDD의 날짜 완전성 계약을 깨는 **코드로 확인된 결함**입니다. 수익률이 유효하지 않다는 실측 결론이 아니라, 계산 허용 여부를 판정할 입력이 누락된 것입니다.

## 남은 미검증

- 실제 Train 가격기준 선택은 아직 하지 않습니다.
- RAW로 잘못 라벨된 수정주가는 게이트를 통과할 수 있습니다.
- 실제 KIS 수정주가 의미, 재작성/정정 시점, available_at, 캐시 버전 provenance가 저장소 근거만으로 확정되지 않았습니다.
- 원문·시점 증거가 없으므로 실제 가격기준과 성과는 검증하지 못합니다.

다음 단계는 새 데이터나 가격기준 선택이 아니라, 위에서 확인된 snapshot-only 성과 소비 결함 하나만 합성 복사본에서 fail-closed로 고칩니다.
