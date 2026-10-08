# REPLAY-EMPTY-LEDGER-METRIC-GATE-0001

- task_id: REPLAY-EMPTY-LEDGER-METRIC-GATE-0001
- chain_id: PAPER-READINESS
- round: 40
- status: READY
- source_pr: 122
- source_head_sha: 2ec2e13b55578290c3bcb822a3b78b30b77c9047

## 목적

PR #122가 공개한 단일 잔여 결함만 다룹니다. `blocked_from`이 없고 snapshot도 0개인 합성 원장을 정상 계산이나 예외로 보내지 않고 `PERF_BLOCKED/NO_SNAPSHOTS`로 명시적으로 차단합니다.

실제 Train 가격기준 선택, 실제 데이터, 실제 성과 계산은 이번 단계가 아닙니다.

## 고정 계약

1. 기존 우선순위를 유지합니다: `blocked_from` → invalid snapshot → empty snapshots → 정상 metric.
2. `blocked_from != null`이면 snapshot 수와 무관하게 기존 `LEDGER_BLOCKED`와 그 날짜를 유지합니다.
3. `blocked_from == null`이고 invalid snapshot이 있으면 기존 `INVALID_SNAPSHOT`과 최초 invalid 날짜를 유지합니다.
4. 둘 다 없고 `snaps == []`이면 `status=PERF_BLOCKED`, `from=null`, `reason=NO_SNAPSHOTS`를 반환합니다.
5. 빈 원장 차단 시 일별수익률·달력월 TWR·MDD·비용후수익률은 모두 null이며 metric 함수 호출은 0입니다.
6. snapshot이 하나 이상이고 모두 valid일 때만 기존 정상 경로로 갑니다. 정상 수치와 비용모델 표시는 바꾸지 않습니다.
7. 가격기준·사건·threshold·비용모델을 새로 만들거나 바꾸지 않습니다.
8. 이 합성 계약을 실제 NAV·성과·PAPER_VALIDATION_READY 근거로 쓰지 않습니다.

## 허용 범위

- PR #122 합성 코드를 별도 결과 폴더에 최소 복사
- empty-snapshot gate 한 분기 추가
- 아래 E1~E8 고정 케이스만 공식 1회 실행
- AST/호출 수/JSON·표·로그 증거
- PR #122 고정본 해시와 기존 M1~M8 회귀

## 금지 범위

- 외부 API·신규 수집·인증·Secrets·원본 계좌 응답
- 실제 사건·시세·포지션·NAV·성과·주문 API
- 실제 가격기준 선택 또는 KIS 인자 변경/호출
- 운영 봇·전략·배분·워크플로·인증·기존 파일 변경
- 백테스트·threshold/alpha·파라미터 탐색
- Validation/OOS 재명명·자동병합

## 고정 합성 케이스

- E1 음성대조: PR #122 `perf_gate`에 `blocked_from=None, snaps=[]` 원장을 넣어 `IndexError`를 재현합니다.
- E2 새 gate: E1 입력이 `PERF_BLOCKED/from=null/reason=NO_SNAPSHOTS`, metric 모두 null, metric 호출 0이어야 합니다.
- E3 우선순위: `blocked_from=D0, snaps=[]`은 `LEDGER_BLOCKED/from=D0`를 유지합니다.
- E4 invalid 우선순위: 표식 없음, invalid snapshot이 있으면 기존 `INVALID_SNAPSHOT/from=최초 invalid일`을 유지합니다.
- E5 최소 정상: 표식 없음, valid snapshot 1개는 기존 정상 결과와 다른 칸 0입니다.
- E6 PR #122 회귀: M1~M8 고정 증거의 verdict/from/reason/metric 산출 여부와 다른 칸 0입니다.
- E7 직렬화·결정성: E2~E5 reload 뒤 출력·바이트가 같고 반복 결과가 같습니다.
- E8 호출경계: AST 또는 동등한 정적 근거로 empty gate가 모든 metric 호출보다 앞이고 snapshot-only/선택 인자가 없음을 증명합니다.

## 완료조건

다음을 모두 만족하면 READY, 하나라도 빠지면 BLOCKED입니다.

- PR #122 code/evidence 고정 해시 일치
- E1 예외 음성대조 재현
- E2 정확한 NO_SNAPSHOTS 차단과 metric 호출 0
- E3~E6 기존 우선순위·정상·M1~M8 회귀의 다른 칸 0
- E7 reload·바이트·반복 결정성
- E8 empty gate가 모든 metric 계산보다 앞이라는 정적·실행 근거
- 공식 실행 1회·상한 1, actual_events=0, external_calls=0
- REPORT·manifest·receipt·evidence를 PR 개설 전에 완성
- status는 READY 또는 BLOCKED만 사용
- `performance_verified=false`, `nav_verified=false`, `paper_validation_ready=false` 명시

## 산출물

`research-exchange/claude-to-gpt/REPLAY-EMPTY-LEDGER-METRIC-GATE-0001/` 아래:

- PREREG.md
- REPORT.md
- manifest.json
- receipt.json
- code/empty_ledger_metric_gate.py
- evidence/empty-ledger-metric-gate.json
- evidence/tables.md
- evidence/run.log

결과 브랜치는 제출 후 불변으로 유지합니다. 후속 연구는 별도 브랜치/PR에서 수행합니다.
