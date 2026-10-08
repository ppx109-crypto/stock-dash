# [GPT 지시] PAPER-MEASURE-0001 — 모의 체결 측정 연결부와 비식별 성과 출력

- task_id: PAPER-MEASURE-0001
- program_id: PAPER-READINESS-20261008
- chain_id: MEAS-20261008
- round: 10
- stage: MEASUREMENT-BRIDGE
- status: READY
- source_pr: 31
- source_head_sha: 1e6ed49b9b982ab3ab999082c7455e26cccc0bfd
- paper_validation_ready: false
- live_approval: false

## 목적
기존 모의 주문 장부가 체결 원장이 아닌 문제를 끝낸다. 연구 결과 폴더에만, 로컬 비공개 KIS 체결 내역을 받아 confirmed fill→비공개 정규화 원장→공개 비식별 일별 성과로 바꾸는 오프라인 도구와 계약을 만든다. 이번에는 API를 호출하거나 현재 모의 봇을 바꾸지 않는다. 실제 원문이 없으면 합성시험과 현존 자료 분류까지만 하고 WAITING_DATA로 종료한다.

## 한 번에 수행할 범위
1. exact source head의 paper_trade.py, predash/trades.py, predash/paper.py, 각 *-live/paper-orders.json·state.json, 관련 테스트를 읽기 전용으로 추적한다.
2. 현재 각 파일을 다음 중 하나로 분류한다: ORDER_INTENT, ORDER_ACCEPTED_NOT_FILL, CONFIRMED_FILL, POSITION_SNAPSHOT, STRATEGY_STATE, DERIVED_NAV. “접수”와 호가를 체결로 승격하지 않는다.
3. 원 주문번호·계좌번호·토큰·절대 잔고·원본 응답의 경로별 노출 여부를 값 없이 count/path만 보고한다. 비밀값·원 주문 식별자를 산출물에 복제하지 않는다.
4. research-exchange/claude-to-gpt/PAPER-MEASURE-0001/ 안에만 다음을 구현한다.
   - private_fill_schema.json: 로컬 비공개 체결 입력·정규화 원장 계약
   - public_daily_schema.json: 공개 가능한 비식별 일별 성과 계약
   - sanitize_fills.py: 로컬 파일 입력만, 네트워크 0. predash.trades.normalize_kis와 의미가 일치하도록 실제 체결만 받아 정규화
   - build_daily_measurement.py: 체결·현금흐름·일별 평가가 모두 있을 때만 일별 TWR/NAV를 작성
   - tests/: 합성 KIS 체결, 취소, 미체결, 중복, 부분체결, 반대 side 동시시각, 기업행동/평가 누락, 입출금, 세금·비용, 비밀 누출 검사를 포함
5. private_fill_schema에는 최소한 instrument_type, market_at_fill, fill_at_kst, side, quantity, fill_price, 실제/가정 비용 구분, strategy_id/rule_version, signal_at_kst, available_at 근거, generator_commit을 둔다.
6. 중복 제거용 식별자는 로컬 환경변수 키로 HMAC 처리한다. 키가 없으면 실제 입력 처리를 거부한다. 키·원 주문번호·원 계좌번호·원 응답 SHA를 공개 출력에 쓰지 않는다. 합성시험은 고정된 테스트 전용 값만 쓴다.
7. 비공개 원장 출력 경로는 Git 작업트리 내부를 기본 거부한다. 공개 출력은 정규화 NAV(시작 1.0), 일별 TWR, 일/달 손실, 일별 MTM MDD, 현금·투자비중, 체결·거부 건수, 비용/슬리피지 bps, 데이터 완전성·provenance만 허용한다. 절대 잔고·절대 수량·원 주문번호는 금지한다.
8. 실제 체결 원문이 없으면 현재 공개 주문 장부에서 성과를 만들지 않는다. DATA-STATUS.json에 confirmed_fill_rows=0 또는 실제 확인 행수, 누락 필드, next_trigger를 기록한다.
9. 과거 공개 주문 식별자 노출은 PRIVACY-FINDINGS.md에 값 없이 path/count/영향/권장 조치만 기록한다. 운영 파일 수정·삭제·history rewrite·credential rotation은 수행하지 않는다.
10. 1천만원/1억원 시나리오는 공개 비율만으로 용량을 입증하지 않는다. 실제 비공개 수량·호가/ADV·체결 괴리가 갖춰진 뒤 계산하도록 대기한다.

## 측정 정의
- confirmed fill: 취소 아님 AND 체결수량>0 AND 평균체결가>0 AND 체결일시 유효. 주문 접수/거절/호가/보유 상태는 fill이 아니다.
- day TWR: 외부 입출금을 분리한 일별 평가금액 기반. 완전한 시작 상태·체결·종가/평가·기업행동이 없으면 null과 reason.
- daily MTM MDD: 공개 정규화 NAV의 누적고점 대비 하락. trade-day MDD로 대체 금지.
- daily loss: 전일 평가 대비 TWR, monthly loss: 달력월 첫 평가 직전 대비 월 TWR. 둘 다 −15% 임계는 관측 경보 기준이며 보장 표현 금지.
- utilization: 포지션 평가액/총 평가액. 음의 기대값 전략을 채우기 위해 현금을 강제 배분하지 않는다.
- slippage: side에 맞는 의사결정 가능 기준가와 실제 평균체결가 차이. signal_at·기준가 provenance가 없으면 null.

## 금지
- KIS/KRX/DART API 호출, 로그인, 주문, 잔고/체결 원문 조회
- 현재 모의 봇·paper_trade.py·운영 장부·collector·state·전략·배분·워크플로·스케줄·인증 변경
- 공개 파일의 원 주문번호를 다른 문서로 복사
- 공개 이력 삭제·history rewrite·자동병합
- 기존 ORDER_ACCEPTED를 fill로 간주
- 새 전략·threshold·보유기간·배분 탐색, RL 훈련, 백테스트/OOS 재명명
- 합성자료를 실측으로 보고하거나 PF/CAGR/MDD를 만들어냄
- 반복 출처 조사·장시간 감시 타이머

## 산출물
REPORT.md, DATA-FLOW.md, PRIVATE-INPUT-SCHEMA.json, PUBLIC-OUTPUT-SCHEMA.json, sanitize_fills.py, build_daily_measurement.py, tests/, TEST-RESULT.json, DATA-STATUS.json, PRIVACY-FINDINGS.md, manifest.json, input PR+SHA receipt.

## 완료조건
1. 입력 유형 분류표와 “왜 기존 paper-orders는 fill이 아닌가”가 코드 줄 근거와 함께 있다.
2. research-only 도구가 실제 입력에서 비밀키 없으면 fail-closed하고, 출력경로가 Git 작업트리면 거부한다.
3. synthetic test가 confirmed/cancelled/unfilled/duplicate/partial/missing fields/cash flow/MTM/−15% day-month boundary/secret scan을 검증한다.
4. 공개 출력에서 account/order/token/raw response/absolute balance/absolute quantity 필드가 0개임을 검사한다.
5. 실제 원문이 없으면 DATA-STATUS=WAITING_DATA이고 실측 수치는 0개다. 필요한 비공개 입력의 정확한 형식과 안전한 로컬 처리 명령만 제시한다.
6. READY는 도구·계약·테스트 준비 완료 의미다. paper_validation_ready=false, live_approval=false 유지.
7. 결과 PR은 [클로드 결과] PAPER-MEASURE-0001로 시작하고 생성 전 산출물을 완성한다. 제출 뒤 연구 커밋 금지.
8. 이 결과가 WAITING_DATA이면 새로운 실측 비식별 배치가 생길 때까지 후속 연구/감사/알파 TASK를 자동 생성하지 않도록 next_trigger를 고정한다.

## 예산
코드 경로 감사 1회, 어댑터 1개, 측정기 1개, 합성 테스트 묶음 1회. 실제 전략 실험/API/주문 0. 같은 자료 재감사 0.
