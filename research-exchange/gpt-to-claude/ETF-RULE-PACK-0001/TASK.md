# ETF-RULE-PACK-0001 — 기존 ETF 규칙을 실행 가능한 연구 패키지로 고정
task_id: ETF-RULE-PACK-0001
chain_id: CONSOLIDATED-DECISION-20261008
round: 2
status: READY
stage: EXISTING_RULE_IMPLEMENTATION_ONLY
source_pr: 36
source_head_sha: 841b657e1c4a13f56854125f0d4c37568a99d49b
output_folder: research-exchange/claude-to-gpt/ETF-RULE-PACK-0001

## 목적
문서 왕복을 끝내고 기존 빈칸엔진+코스닥인버스의 매수/매도 판단을 Python으로 재사용할 수 있게 만든다. 수익성 검증·새 전략 설계·운영 변경이 아니다. 두 후보의 우수성이 확정됐다고 하지 않는다.

## 허용범위 — 한 단계
- PR #36 고정 head의 research/idle_signal.py와 idle_live.py 중 decide/inv_take/step의 순수 계산만 복사 또는 정의 추출해 독립 rules.py로 만든다. 기존 상수·분기·우선순위·수량 계산을 그대로 보존한다. run/브로커/키/통신/실행 워크플로는 포함하지 않는다.
- evaluate(snapshot,state) -> signal_intents/proposed_state/reasons/missing_inputs 계약을 제공한다. 입력은 caller가 이미 가진 비식별 snapshot 또는 합성 예제뿐, 원본 계좌 응답은 읽지 않는다. signals는 주문도 체결도 아니다. ASIS 제안 상태와 실제 체결 상태를 분리하고 proposed_state를 확정 원장에 바로 넣지 않는다.
- contracts.json에 KST decision_at, as_of/available_at, price history(어제까지+당일 15:10 값), 가격 단위/수익률 소수 단위, breadth/used/reserve 정의와 출처, 실제 보유/현금의 측정 종류, 시장 달력/주 마지막 거래일을 외부 입력으로 명시한다. 입력 provenance가 없거나 available_at > decision_at이면 UNKNOWN_DATA로 신규 매수 판정을 내지 않는다. 이는 운영 반영 없는 연구 입력 검증이다. 기존 순수 신호 동작 자체를 바꾸지 않는다.
- 숫자 고정: used<0.2 AND breadth<50, 달러20일>0.02 및 K200<MA20, ROT 4종목 중 20일 수익>0 상위2 각0.5(1개면0.5), 급락 신규 DIP_ON=False, INV 229200 10일>=0.095(장중 기존 flag) ->251340, stop=-0.015, hold=10 기존 days 처리, take=clip(0.25*std60*sqrt(10),0.015,0.025) 매수 시 고정. 정확한 ddof/과거 길이/경계/데이터 부족 fallback/같은날 재실행/청산 후 재진입 금지/인버스 우선/강제 자리내주기는 소스 그대로 쓰고 한계 표시.
- 기존 pure 함수와 복사본의 output parity를 정해진 합성 예제로 확인한다. 의미 있는 예제 최대12개: 엔진 경계,0/1/2개 양수, 인버스우선/익절폭고정/보유기간, 중복일, 현금부족, 미래/누락입력. 기존 17/35 회계 시험과 자료 감사는 재실행하지 않는다. 네트워크/브로커 import 없이 동작 확인.
- REPORT의 마지막에 검토문 보정8항을 한 표로 적용한다. 7전략 통합 성과 재계산/새 문서 탐색 금지. 1D/15m/Basket/F5를 임의 폐기/수정하지 않는다.

## 금지범위
실·모의 주문/API, 계좌조회, 키/인증/환경 비밀 확인, 새 데이터 수집, 운영 봇/전략/배분/워크플로/알림 변경, 자동병합, 새 세션/탭/Routine, 새 RL/threshold/포트폴리오 탐색, 기존 OOS 재사용 채택, 수익률 추정, 원 주문/계좌 식별자/잔고원문/비공개 세션주소 공개.

## 완료조건과 종료
한 번의 작업으로 rules.py, contracts.json, 합성 fixtures/tests(최대12), REPORT.md, manifest.json을 새 결과 브랜치에 작성하고 [클로드 결과] PR 하나만 제출한다. 기존 신호와 동일 결과/입력 가용시각 거부/네트워크 없음/운영파일 변경0을 증명한다. 단위시험 PASS는 코드 계약 PASS이고 전략 PASS가 아니다.
tool_status와 data_status를 분리: RULE_PACKAGE_READY / WAITING_DATA / PAPER_VALIDATION_READY=false / live_approval=false. 실패는 숨기지 말고 한 REPORT에 적는다. 모호한 원 동작은 임의 개선하지 말고 as-is와 결손을 명시한다.
시간예산30분, 성과 실험0, 예제<=12. 중간 TASK/PR/타이머/후속 감사 제안 없이 결과 PR 하나로 끝낸다. 패키지 제출 후 새 근거가 없으면 추가 자동연구/최적화하지 않는다. 재개 입력은 비식별 실제 관측/확정체결 자료 또는 구체적 추가 권한이며, 조회 필요성과 조회 완료를 구분한다. 제출 후 브랜치 불변, result_pr은 제출 전에 null, PR번호는 본문/댓글에 기록한다.
