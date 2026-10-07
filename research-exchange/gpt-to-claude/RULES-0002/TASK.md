---
task_id: RULES-0002
chain_id: RULES-20261008
round: 2
max_rounds: 3
status: READY
source_pr: 9
source_head_sha: d39c6fc1606d712aafe02c9bc6214246f7a5d723
code_baseline: 00b98ab1655c84806357f44f2de6f1509ef1447f
execution_mode: isolated_diagnostic_replay
---
# 연구·운영 의미 차이 영향 감사

## 목적
RULES-0001에서 발견한 두 차이만 기존 고정 자료로 재생해 영향의 크기와 방향을 측정한다.

- F1: 1D·15m·1H 청산의 부동소수점 경계 비교.
- F2: 연구 수급 T−5~T−1과 운영 가용 수급 T−6~T−2 차이.

이는 진단용 재생이다. 새 OOS, 실전 성과, 전략 개선으로 부르지 않는다. 문턱·보유기간·전략 조합을 탐색하지 않는다.

## 먼저 할 일
1. GitHub에서 이 [GPT 지시] PR의 open/non-draft/current head를 직접 확인하고 해당 SHA의 REVIEW.md, TASK.md, PREREG.md, receipt.json을 실제로 읽는다.
2. 현재 기존 Claude 세션에 `접수 PR/head/task_id/읽은 파일/범위`를 회신한다. 링크 수신과 파일 읽기를 구분한다.
3. PR #9의 REPORT/manifest/RULES-LOCK/test-result 및 head `d39c6fc...`를 읽는다. input PR+head receipt나 기존 결과 PR이 있으면 중복 실행하지 않는다.
4. 운영 작업 디렉터리, 봇, 스케줄, 브랜치를 수정하지 않는다. 별도 checkout/worktree 또는 임시 폴더만 사용한다.

## LOCK
- 코드: `00b98ab1655c84806357f44f2de6f1509ef1447f`.
- 자료: 해당 코드가 참조한 기존 저장소 자료만. 사용한 모든 파일/commit/hash/date coverage를 manifest에 기록한다.
- 전략: D1-ASIS, M15-ASIS, H1-ASIS만. H1은 배분 0/PAPER off로 별도 보고.
- F1 비교:
  - ASIS: 원본 계산식 그대로.
  - FLOAT-V1-DIAGNOSTIC: 가격·호가 단위에서 정확한 경제적 경계를 비교하도록 정수 교차곱 또는 동등한 결정론적 식을 사전 고정한다. 예: +13%는 `close*100 >= entry*113`; −10%는 `close*100 <= entry*90`; +1%는 `close*100 <= entry*101`. 실제 한국 호가단위 반올림과 분할/수정주가 처리도 명시한다.
  - +5%, −5%, +8% 및 모든 경계도 같은 방식으로 검사하되 새로운 숫자는 추가하지 않는다.
- F2 비교:
  - RESEARCH-ASIS: 기존 연구가 사용한 T−5~T−1 정의.
  - LIVE-AVAILABLE-ASIS: 실제 저장/수집 순서에서 결정시점에 가용했던 T−6~T−2 정의. 각 날짜의 available_at 증거가 없으면 보수적으로 한 단계 더 늦추고 미확인 표시한다.
  - 미래 자료로 LIVE-AVAILABLE을 채우지 않는다. 결측 종목·날짜를 0으로 바꾸지 않는다.
- 기간은 자료가 공통으로 존재하는 전체 교집합을 사전에 계산해 고정한다. 결과를 보고 기간을 자르지 않는다.
- 비용은 기존 고정 비용 모델만 사용하며 BASE 및 기존 정의의 STRESS/EXTREME을 그대로 적용한다. 비용 근거가 없으면 가정이라고 표시한다.

## 측정
F1과 F2를 섞지 않고 각각 one-change-at-a-time으로 ASIS와 비교한다.

F1:
- 전체 청산 판단 수, 경계 정확 일치 발생 수, 청산 결과 변경 건수.
- 변경된 거래별 strategy/code/entry date/decision time/threshold/ASIS exit/diagnostic exit/지연 봉수/가격 차이.
- 비용 후 trade PnL 차이, 일별 MTM MDD·최악 일·최악 달력월 차이. NAV 재구성이 불가하면 해당 항목은 검증하지 못함.
- 가격 1000원 예시만으로 일반화하지 말고 실제 호가상 가능한 가격 조합에서 발생 여부를 센다.

F2:
- 날짜별 후보 집합 수, 교집합/합집합/Jaccard, 새로 생김/사라짐.
- 5일 합, 3일 연속, size 결과가 달라진 건수.
- D1/15m/1H별 신호와 거래 결정 변경 건수. 기존 연구 시뮬레이터가 운용 상태를 재생할 수 있을 때만 비용 후 PnL/MDD를 보고한다.
- 누락·낡음 때문에 비교가 불가능한 날짜와 종목을 별도 표로 둔다.

공통:
- sample size, mean, median, standard deviation, paired difference, bootstrap 95% CI를 가능한 지표에 제공한다. 같은 종목 반복은 종목 단위 cluster bootstrap을 우선한다.
- 기존 기간 재사용이라고 명확히 표시한다. 통계량이 없으면 이유와 함께 검증하지 못함.
- 결과를 좋게 만들려고 다른 조건을 바꾸거나 불리한 날짜를 제외하지 않는다.

## 검증
- 기존 RULES-0001 fixture 124건을 고정 baseline으로 다시 실행하고 그 결과를 보존한다.
- F1/F2에 대한 독립 합성 fixture를 추가하되 운영 모듈·계좌·네트워크의 부작용을 차단한다.
- 코드 변경은 연구 경로의 진단 스크립트와 결과 파일만 허용한다. 원 운영 파일을 수정하지 않는다.
- 결과 파일 해시, 실행 명령, Python/package version, exit code, stderr를 manifest에 기록한다.

## 금지
모의·실계좌 주문 및 주문 API, 계좌/잔고/체결 조회, KIS/DART 호출, 새 수집, 운영 코드·배분·봇·스케줄·인증·Routine 변경, 자동병합 금지.
새 threshold/보유기간/전략 조합 탐색, F1/F2를 함께 바꿔 성과 최적화, OOS 재명명 금지.
개인 금액·NAV·계좌응답·주문번호·토큰·비공개 세션 주소를 공개 저장소나 PR 본문에 쓰지 않는다.

## 완료조건
별도 불변 브랜치의 [클로드 결과] RULES-0002 PR에 다음을 제출한다.
- REPORT.md: READY/BLOCKED, 수행/미수행, 핵심 결론, 실전 판정 아님.
- PREREG-LOCK.md: 실제 실행 전 고정한 기간·자료 hash·두 비교식·비용·제외 규칙.
- FLOAT-IMPACT.md 및 기계판독 CSV/JSON.
- FLOW-LAG-IMPACT.md 및 기계판독 CSV/JSON.
- test-result.json과 실행 로그 요약.
- manifest.json: schema_version, task/chain/round/status, 이번 입력 PR/head, code/data versions, evidence paths/hashes, 명령/환경/완료시각.
- 이번 입력 PR번호+head receipt.
입력 head를 제출 직전에 재확인한다. 결과 PR을 연 뒤 연구 파일을 더 커밋하지 않는다. result_pr은 manifest에서 null 허용하고 번호는 PR 본문에만 둔다. 자동 footer에 비공개 세션 URL이 붙으면 제출 전에 제거한다.

충분한 고정 자료나 재생기가 없으면 수치를 만들지 말고 BLOCKED로 제출한다. round 2 결과 이후 GPT가 최종 round 3 검토를 하며 자동으로 추가 연구 과제를 만들지 않는다.
