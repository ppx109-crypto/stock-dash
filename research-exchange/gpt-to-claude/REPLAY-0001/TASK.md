# TASK — REPLAY-0001 순수 회계·일별 평가 커널 복구
task_id: REPLAY-0001
program_id: PAPER-READINESS-20261008
chain_id: MEAS-20261008
round: 2
stage: REPLAY-1A
status: READY
source_pr: 15
source_head_sha: 6c7e1f0f0bbafcca4d8c0e555b7b5711601fe206
code_baseline: 00b98ab1655c84806357f44f2de6f1509ef1447f
execution_mode: isolated_offline_accounting_kernel
program_reference: PR14@bbf384dec3e5c26ad0570d20e993af523bed5532 / research-exchange/gpt-to-claude/MEAS-0001/PROGRAM.md

## 목적과 이번 단계 상한
현재 수익률을 더 좋게 만드는 것이 아니라 현금·수량·비용·일별 평가금액의 잘못된 측정을 제거한다. 이번은 한 개 순수 회계 커널 구현+작은 합성 시험+기존 장부 입력 가능성 검사만. 아직 전체 전략 재생/알파/실제 모의 측정 시작 단계가 아님.
같은 작업 진행 중이면 중복 계산하지 말고 범위 정합성만 확인. 기존 지정 세션에서 이어가고 이전 결과 PR15 브랜치는 불변.

## 허용범위
새 연구 문서 브랜치에서 research-exchange/claude-to-gpt/REPLAY-0001/ 하위에만 소스·스키마·합성 입력·결과·보고서를 작성.
코드 기준점의 a_mtm 및 PR15의 검토된 순수 코드/산출물은 읽기만. 운영 모듈 import/실행 금지. 표준 라이브러리 중심 순수 함수, 네트워크 차단, 입력값 주입. 원본 a_mtm은 정의만 떼어 합성 대조 가능.
RULES-0002@a61f033ecd16ba0976c955a93bfec70c7463ad53의 기존 d1_ledger_ASIS.csv(495행)는 스키마/필수 필드·원 거래 식별/부분청산 연결 여부만 읽기 점검. 새 원장/캐시/API를 찾거나 전체 가격 재생하지 않음.
문서·오프라인 코드·합성 데이터만이며 현행 봇에 연결하지 않는다.

## 커널 계약(먼저 PREREG-LOCK으로 고정)
1. 입력 source_mode(SYNTHETIC / HISTORICAL_MODEL / OBSERVED_KIS_PAPER) 명시. evidence 없는 실제 모드 금지. 주문 의도/접수/거절/취소는 포지션을 바꾸지 않으며 confirmed fill만 현금·수량 변화. 합성은 MODEL_FILL로 구분.
2. fill: 가명 event/order/trade_id, strategy_id, security_id, 시각(timezone 포함), buy/sell, 정수 qty, Decimal 가격·비용·세금, 증거 유형/버전. broker 원문/계좌/주문번호 저장 금지. 반복 fill_id 멱등, 충돌된 중복은 실패.
3. 현금·정수 수량 보존. 매수대금+매수비용≤사용가능현금. 부족시 미리 고정된 정책으로 정수 수량 축소/0주 제외하고 이유 기록. 비용 무시한 min(원금,현금) 계산 금지. 비용 후 현금≥0, 보유이상 매도 금지. 현물 무차입 모드에서 순자산 초과 노출을 보이지 않도록 대사.
4. 자본 입력 10,000,000 / 100,000,000원은 합성 회계 시나리오일 뿐. 칸·종목 배분 규칙을 최적화하지 않음. 10칸 요청/단가/비용을 입력으로 주어 현금 한도·정수주 결과만 검증. 주문한도와 투자금액/NAV 값은 매 사건마다 명시.
5. 같은 날 매수·매도, 부분청산, 여러 전략의 같은 종목을 trade/strategy_id로 분리. 원 장부 부분청산을 별도 독립 매수로 중복 생성 금지.
6. 비용은 발생 사건에서 한 번만 현금 차감. slippage를 fill 가격에 넣었으면 별도 현금비용으로 중복 차감하지 않음. 실제 세율/수수료·충격 모델은 이번에 확정 안 함; 합성 비용 입력과 실제 비용근거 null을 분리.
7. NAV=현금+정수 보유×그 시점 평가가격+미결제채권−채무−미지급비용. 현금이 trade-date 경제현금인지 settled cash인지 명시하고 결제항목 중복 금지. 주문가능현금은 별도 필드. 이번 결제 모델은 합성 입력의 정책이며 증권사 실측으로 부르지 않음.
8. 평가 가격 source/market_session/available_at/version, stale/missing 명시. 미래값·불명확 가격으로 자동 채우기 금지. missing이면 해당 NAV/risk null 또는 사전에 고정한 평가 정책+경고. 정정값은 정정시각 이후에만. split 등 입력변환 없으면 UNSUPPORTED로 표시(이번 기업행동 엔진 확장 없음).
9. 원장 pnl_pct는 대사 참고일 뿐 매도대금/매도가를 역산하거나 NAV를 강제맞춤하지 않음. 매도대금은 qty×fill_px에서 계산.
10. 외부 입출금은 손익 제외. TWR 구간 연결·달력월 복리·unitized daily MTM MDD, 세 기준 각각 −15% 판정. 원 NAV 고점 기반 MDD도 외부입출금 없는 때만 비교, 최초원금 기준으로 바꾸지 않음. partial month/가격결손/자산≤0 구간은 명시.
11. 사건순서는 event_at/명시 sequence, 같은 시각 순서 불명은 AMBIGUOUS로 거부. '매도 먼저'를 원 실제순서로 지어내지 않음. 이 kernel 통과가 판단시점/체결가능성/유니버스/OOS 통과를 뜻하지 않음.

## 금지범위
실·모의 주문/계좌/KIS/DART API, 새 수집/운영 로거 활성화, 인증·봇·규칙·배분·워크플로·Routine·타이머 변경, 새 탭/세션, 자동병합.
전체 과거 전략백테스트/성과/새 신호·threshold·calm·수급 lag 탐색/ML/포트폴리오 조합 금지. 운영 주문 함수/과거 캐시 unsafe pickle/운영 폴더 import 금지.
원본 계좌 응답·비밀·계좌/원 주문번호·실계좌자료·비공개 세션 주소 열람/공개 금지. 현재 paper 원장에 없는 fill을 만들지 않음.

## 완료조건
- 구현/시험/결과 보기 전에 PREREG-LOCK(입력·골든 기대값·이벤트순서·금액/비용 반올림·거부/축소정책·budget·판정) 기록. 이번 이전 탐색결과를 사전검정이라고 하지 않음.
- account_kernel.py, schema/CONTRACT.md, fixtures/golden.json, tests와 TEST-RESULT.json: 아래 PREREG의 고정20사례 실행. 원본과 달라진 의미·failure/수정 이력 공개. 테스트가 구현을 그대로 복제하지 않게 손검산 가능한 골든 결과.
- INPUT-FEASIBILITY.json: 기존495행의 실제 컬럼/hash/부분청산 그룹·모형화할 수 있는 필드·필수 결손. 필수 fill time/price/qty 없는 행은 그대로 결손. 해당 작업이 끝났으면 결과 READY+역사재생BLOCKED/NEEDS_DATA도 허용.
- REPORT.md: 커널 계약 판정/검증한 범위/미검증 범위, 계좌보존 사례 결과, 다음필수입력. 전략 CAGR/PF/승률 표는 '이번 미수행'. 전략 수익성 증거 또는 PAPER_VALIDATION_READY 선언 금지.
- manifest: code/hash/input/hash/실행환경·명령/실제 결과경로/상태/검사전 LOCK 시각, receipt는 입력 PR/SHA 포함. 결과 및 receipt 완성 후 새 불변 [클로드 결과] PR 제출, result_pr null. 제출 후 연구 결과 추가 금지.
예산: 커널1판, 고정20골든사례와 이를 위한 구현 결함 수정만, 최대2분/256MB 목표; 장부스키마 검사495행 선형1회. 예산 초과/미지원은 구체적으로 보고하며 큰 계산으로 넓히지 않음.
