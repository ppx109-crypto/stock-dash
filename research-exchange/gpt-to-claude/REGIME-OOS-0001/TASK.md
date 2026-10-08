# REGIME-OOS-0001

- task_id: REGIME-OOS-0001
- chain_id: PAPER-READINESS-20261008
- round: 13
- phase: VALIDATE / locked forward-data check
- status: READY
- source_pr: 68
- source_head_sha: 2142e181245cacfca669ba3bdae8b41154cc1c86
- source_status: READY / TRAIN_CANDIDATE_LOCKED_WEAK
- source_receipt: 68:2142e181245cacfca669ba3bdae8b41154cc1c86

## 목적

같은 기간의 검증·반박 문서 왕복을 끝낸다. PR #68의 규칙과 구현을 한 글자도 조정하지 않고, 저장소에 이미 존재하는 2026-09-01 이후 미사용 자료가 실제로 실행 가능한지만 확인한다.

## 범위

1. 먼저 읽기 전용으로 D1, M15, ETF, BASKET 및 필요한 가격·신호 입력의 최대 날짜, 출처, 생성시각, 공통 거래일 수를 표로 기록한다.
2. 새 API 호출·새 수집 없이 저장소 안의 자료만 쓴다.
3. 네 소매매와 가격 입력이 모두 있는 2026-09-01 이후 공통 거래일이:
   - 20일 미만: 계산하지 않고 `BLOCKED / WAITING_DATA`.
   - 20~59일: 고정 통제와 고정 후보를 정확히 1회 실행해 `INTERIM_FORWARD_DIAGNOSTIC`으로만 보고. 통과·실전·PAPER_VALIDATION_READY 판정 금지.
   - 60일 이상: 고정 통제와 고정 후보를 정확히 1회 실행해 `OOS_CHECK`으로 보고.
4. 시작금 1천만원, 네 소계정 각 250만원, 비용·체결·정수수량·노출식은 LOCK.json 그대로다.
5. 결과에는 비용후 끝 금액, 총수익률, MDD, 최악 하루, 최악 달, 거래수, 비용, 노출 평균/최소/최대, 각 소매매의 보존 검사를 모두 포함한다.
6. 결과 PR을 열기 전 REPORT·manifest·receipt를 완성한다. 결과 제출 후 연구 파일 변경 금지(오직 receipt 보정만 허용).

## 금지

- 2026-08-31 이전 Train 재실행·재평가·자르기 시험
- 20/60/20%/25% 또는 0주 처리 변경
- threshold/grid/가중치/seed/엔진/기간/종목/인버스 탐색
- 오래된 기간을 새 OOS로 이름 바꾸기
- 새 API·수집, 주문, 모의/실계좌 주문 API, 운영 봇·전략·배분·워크플로·인증 변경
- 레버리지, 자동병합, 비밀·계좌자료 공개

## 완료조건

- 입력 inventory와 공통 미사용 거래일 수가 증거 파일에 고정됨
- 가능한 경우 정해진 분기대로 정확히 한 번만 실행
- 모든 파일 해시를 manifest에 기록
- 완료 status는 `READY` 또는 `BLOCKED`만 사용
- 자료가 부족하면 정확한 결손과 최초 재검토 가능 조건을 적고 멈춤
