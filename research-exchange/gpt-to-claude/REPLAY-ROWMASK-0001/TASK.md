# REPLAY-ROWMASK-0001 — 미래가격 존재에 의존한 표본선택 복구 한 단계
task_id: REPLAY-ROWMASK-0001
chain_id: PAPER-READINESS-20261008
round: 15
status: READY
source_pr: 72
source_head_sha: 1f965e88b0bca34b5777344d44a11ff3c5239869
stage: REPLAY (확인된 입력·시점 결함 복구만)
## 목적·경계
수익률 튜닝이 아니라 PR72 rf_cache의 orig=5 in ahead 때문에 과거 입력행이 미래자료 존재에 의존하는 결함을 제거하고, 고정된 기존 규칙에 실제 영향이 있었는지 한 번 계산한다. 9월 결과에 맞춘 신호/threshold/매도 규칙 수정은 금지. 이미 진행 중인 동일 복구가 있으면 새 계산하지 말고 기존 실행을 이 TASK에 연결한다.
## 한 번에 수행
1. 손익 계산 전에 코드 diff/입력경로+SHA/캐시 provenance/표본생성 사전등록을 완성한다. PR68/72가 쓴 옛 입력 버전만 사용. 미확인·추정 배율 가격을 새로 만들지 않는다. 로컬 캐시/기존 git 버전으로 복구 가능성을 확인하고, 핵심 입력 결손이면 BLOCKED/NEEDS_DATA로 exact 경로·필요 버전만 보고한다. 외부 API/새 수집 금지.
2. 연구 복사본에서 feature의 존재 조건을 그날까지 가격으로만 정한다(horizons=(0,) 동등). 앞날 수익(ahead)와 orig 존재 조건을 제거한다. 판단 feature 계산식·TOP/Universe 규칙·월별calm 숫자·수급T-2·기존 entry/exit/비용2배·정수floor·seed0는 변경하지 않는다. 기존 Universe(t)/수급 provenance 미해결은 그대로 공개; 고쳤다고 인증하지 않는다. 새 자료 추가·종목 제외·새 imputation 금지.
3. 구조 검사 cut은 사전 고정 2026-01-30 / 02-27 / 03-31 세 개. 각 prefix vs 같은 옛 입력의 더 긴 prefix(최대2026-03-31)에서 당일까지 feature 존재·과거행 값·그날 상위100·신호 동일성을 확인한다. 끝날 이후 label 필요를 평가행 요건으로 삼지 않는다. 필요한 warmup은 해당 판단일 이전만; 월calm의 수치 재최적화 금지. 마지막 cut은 그날 미보유/현금·중단 종목이 사라지지 않는 합성사례로 보완한다. 포트폴리오 수익 재실행 없이 작은 합성3사례(정상추가/마지막5일/중단)로 사전검사 가능.
4. 미리 고정한 Train은 2025-09-18~2026-03-31이다. 2026-04~08은 이미 본 재사용 진단으로 이번 계산 안 함. 9월 USED/10월holdout 모두 열거나 재평가하지 않는다. 과거수익label로 행을 거르지 않는다.
5. 제거 전후의 행수·상위100·D1신호 차이를 Train 날짜별로 계산한다. 신호차이0이면 불필요한 포트폴리오 재계산0회, 기존 저장된 baseline값만 인용하고 영향0(이 결함 한정)을 보고한다.
6. 신호차이가 있으면 repaired 통제 P4만 Train에서 최대1판 돌린다(현금1천만원·250만원x4, PR68 동일 시작/비용2배/다음봉·다음날 체결). 옛 baseline은 PR72 nav_signal_path.csv의 동일 Train prefix로 비교하고 다시 돌리지 않는다. 변하지 않은 M15/Basket은 동일 시작 저장경로 재사용 허용, 달라진 D1 및 이에 의존한 ETF만 재계산할 수 있다. 보조 D1x1 used계산은 기존 엔진 필요항목이지 신규 수익최적화 실험이 아님; 실행수를 정확히 공개한다. 후보 risk overlay 신규실행0, 새 ALPHA0.
7. 변화한 매수·매도·NAV/비용/최악하루·달/MDD·현금비중을 요약. 개선됐어도 '편향 복구 진단'이지 독립 성능/OOS/실전 준비가 아니다. 이전 백테스트 영향 유/무/검증불가를 명확히 끝낸다. 수급/공시available_at/수정가격/생존자편향이 남으면 BASELINE 전체 통과 금지.
## 금지
새 API·수집·키/계좌 조회·모의/실 주문, 현재 봇/전략/배분/워크플로/인증 변경, 자동병합/레버리지, 9월 재실행/10월 열기, 새 threshold/grid/seed/캘린더/익절/위험규칙 실험, 실패를 숨긴 재시도, 원가격/비밀/비공개 세션주소 공개.
## 완료
READY: 합성/prefix 검사·행/신호 차이와 영향 진단 완료(원문증거 없는 전체 PIT 합격 아님). BLOCKED: 입력결손/한 번 복구로 해결 안 되는 차이를 정확히 설명. 구조검사 실패면 손익실행하지 않고 BLOCKED. 동일 실패를 다시 TASK로 돌리지 않는다.
REPORT/manifest/evidence/receipt를 결과 PR 전에 완성; task_id/chain_id/round/status/source_pr/source_head_sha/code_commit/evidence_paths/completed_at_kst 필수(미확인null허용). 원자료는 공개하지 말고 해시·정규화/파생요약만. 별도 결과 브랜치·[클로드 결과] 비초안 PR, 제출 뒤 receipt외 수정 금지/result_pr=null 허용. 기존세션만 이용. 복구로 해결 안 되는 권한/자료 결손은 요청 범위를 정확히 보고하고 스스로 확장하지 않는다.
