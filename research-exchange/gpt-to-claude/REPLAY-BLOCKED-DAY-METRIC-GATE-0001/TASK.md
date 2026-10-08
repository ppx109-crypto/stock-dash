# REPLAY-BLOCKED-DAY-METRIC-GATE-0001

- task_id: REPLAY-BLOCKED-DAY-METRIC-GATE-0001
- chain_id: PAPER-READINESS
- round: 39
- status: READY
- source_pr: 120
- source_head_sha: 8ed1d7d24a7fd564c200f2978bd51659f1af4316

## 목적

PR #120이 공개한 단일 측정 결함만 다룹니다. 차단일에 snapshot이 없어도 성과 소비자가 ledger의 `blocked_from`을 직접 읽어 일별 MTM·일/월 TWR·MDD 계산을 fail-closed로 중단하도록 합성 계약을 고정합니다.

실제 가격기준 선택, 실제 시세 라벨 생산, 실제 사건 변환, 실제 성과 계산은 이번 단계가 아닙니다.

## 고정 계약

1. 성과 함수는 snapshot 목록만 받지 않고 **ledger 전체 또는 `blocked_from`을 반드시 포함하는 단일 상태 객체**를 받습니다. 호출자가 차단 표식을 생략할 수 있는 선택 인자는 허용하지 않습니다.
2. `blocked_from != null`이면 snapshot 수와 무관하게 가장 먼저 `PERF_BLOCKED`를 반환합니다.
3. 차단 반환은 최소한 `status=PERF_BLOCKED`, `from=blocked_from`, `reason=LEDGER_BLOCKED`를 포함합니다.
4. 차단 상태에서는 일별 TWR, 달력월 TWR, MDD, 비용후수익률을 계산하거나 정상값으로 내보내지 않습니다. 해당 metric은 null/미산출로 명시합니다.
5. `blocked_from`이 없더라도 invalid snapshot이 하나라도 있으면 최초 invalid 일자부터 `PERF_BLOCKED`입니다.
6. `blocked_from`도 없고 모든 snapshot이 valid일 때만 기존 합성 정상 경로를 유지합니다.
7. 가격기준·사건 규칙·수치·threshold를 새로 만들거나 바꾸지 않습니다.
8. 이 계약은 실제 데이터 provenance를 만들지 않습니다. 실제 성과와 PAPER_VALIDATION_READY의 근거로 쓰지 않습니다.

## 허용 범위

- PR #120의 합성 코드를 별도 결과 폴더에 최소 복사
- 성과 함수 입력을 ledger 단일 상태로 바꾸고 차단 표식 우선 gate 추가
- 아래 고정 합성 케이스만 공식 1회 실행
- 정적 호출경계/분기순서 근거, JSON·표·실행 로그 작성
- PR #120 고정 파일의 blob/sha256 확인과 기존 fixture 회귀

## 금지 범위

- 외부 API·신규 수집·인증·Secrets·원본 계좌 응답
- 실제 사건·시세·포지션·실제/모의 NAV 또는 주문 API
- 운영/모의 봇·전략·배분·워크플로·인증 또는 기존 파일 변경
- 실제 가격기준 선택, KIS 인자 변경/호출, 라벨 추론
- 백테스트·성과 추정·threshold/alpha 탐색·파라미터 조정
- 실제 수익률·TWR·MDD·capacity 주장
- Validation/OOS 재명명·자동병합

## 고정 합성 케이스

- M1 음성대조: PR #120 기존 `perf(snaps)`에 D0 valid snapshot 뒤 D1 quote-basis 차단 상태의 `snaps`만 전달합니다. D1 snapshot이 없어 기존 함수가 차단을 놓치는 결과를 기록합니다.
- M2 새 gate/마지막 날: M1과 같은 ledger 전체를 새 성과 함수에 전달합니다. `PERF_BLOCKED/from=D1/reason=LEDGER_BLOCKED`, 모든 metric 미산출이어야 합니다.
- M3 첫날 차단: snapshot 0인 ledger라도 `blocked_from=D0`이면 같은 방식으로 차단합니다.
- M4 사건 배치 차단: invalid snapshot이 함께 있는 PR #120 기존 경로도 최초 차단일부터 차단하며 회귀하지 않습니다.
- M5 불일치 방어: `blocked_from`은 없지만 invalid snapshot이 있으면 최초 invalid 일자로 차단합니다.
- M6 정상 RAW: 차단 표식 없음, 모든 snapshot valid인 PR #120 RAW 정상 fixture는 기존 정상 결과와 다른 칸 0입니다.
- M7 직렬화: M2~M6 각각 serialize→reload 뒤 verdict/from/reason/metric 산출 여부와 바이트가 동일합니다.
- M8 호출경계: AST 또는 동등한 정적 증거로 성과 함수가 snapshot-only 인자를 받지 않고 차단 검사가 수익률·MDD 계산보다 앞임을 증명합니다.

## 완료조건

다음을 모두 만족하면 READY, 하나라도 빠지면 BLOCKED입니다.

- PR #120 고정 code/evidence 해시 일치
- M1에서 기존 snapshot-only 소비가 마지막 차단일을 놓치는 음성대조 재현
- M2~M5 모두 정확한 최초 차단일과 이유로 fail-closed, metric 미산출
- M6 기존 RAW 정상 합성 결과와 다른 칸 0
- M7 결정성·reload·바이트 동일
- M8 차단 검사가 모든 성과 계산보다 앞이라는 정적·실행 근거
- 공식 실행 1회·상한 1, actual_events=0, external_calls=0
- REPORT·manifest·receipt·evidence를 PR 개설 전에 완성
- status는 READY 또는 BLOCKED만 사용
- `performance_verified=false`, `nav_verified=false`, `paper_validation_ready=false` 명시

## 산출물

`research-exchange/claude-to-gpt/REPLAY-BLOCKED-DAY-METRIC-GATE-0001/` 아래:

- PREREG.md
- REPORT.md
- manifest.json
- receipt.json
- code/blocked_day_metric_gate.py
- evidence/blocked-day-metric-gate.json
- evidence/tables.md
- evidence/run.log

결과 브랜치는 제출 후 불변으로 유지합니다. 후속 연구는 별도 브랜치/PR에서 수행합니다.
