---
task_id: RULES-0001
chain_id: RULES-20261008
round: 1
max_rounds: 3
status: READY
source_pr: 6
source_head_sha: 46d4b069ad7d2a0513352c0acbf3967d55492c12
prior_result_pr: 5
prior_result_head_sha: ffcdb4d0c0097c0774c3990aa6c461231b6b5a89
code_baseline: 00b98ab1655c84806357f44f2de6f1509ef1447f
execution_mode: isolated_offline_contract_audit
---
# 기존 규칙과 실측 계약을 고정하는 한 단계

## 재개 근거와 목적
사용자가 기존 Claude 세션의 문서 왕복을 확인하고 자동매매 규칙 설계를 이어가라고 요청했다. 이전 EXCHANGE-BOOTSTRAP은 종료된 채로 둔다. 이는 새로운 사용자 지시에 따른 별도 설계 체인이며 연구 타이머 재개나 운영 변경 승인이 아니다.
이번 단계는 **현재 코드의 매수·매도·자금배분·데이터시점 계약 추출 및 검증** 하나다. 전략 수익 최적화나 신규 성과 백테스트를 하지 않는다.

## 파일 접수와 왕복
1. 전달받은 [GPT 지시] PR을 GitHub에서 직접 조회해 open/non-draft와 head SHA를 확인한다. 그 SHA의 TASK.md, RULE-CONTRACT-DRAFT.md, REVIEW.md, receipt.json을 실제로 읽는다. 이 TASK의 source_pr은 이전 검토 출처이며, 답변 manifest의 source_pr/source_head_sha는 **이번 전달 PR의 실제 번호/head**다.
2. 먼저 현재 세션에 `접수: PR번호 / head SHA / task_id / 실제 읽은 파일 4개 / 수행범위`를 남긴다. URL 수신과 파일 읽기를 구분한다.
3. GitHub 자동 감시는 이 문서만으로 설치되지 않는다. 새 [GPT 지시] 링크가 현재 세션에 전달된 때만 조회한다. 별도 Routine/세션/탭/타이머/워크플로/알림 시스템을 만들거나 켜지 않는다. 이미 진행 중이면 중단하지 않고 메시지를 대기열에서 처리한다.
4. 입력 PR번호+head receipt나 기존 결과 PR이 있으면 중복 수행하지 않는다.
5. 완료 파일을 모두 커밋한 뒤 새 불변 브랜치에서 [클로드 결과] RULES-0001 PR을 연다. result_pr은 사전 manifest에서 null 허용, 번호는 PR 본문에만 넣는다. 제출 뒤 main 병합이나 연구 파일 추가 금지. PR 본문의 자동 생성 footer까지 확인해 비공개 세션 URL을 제거한다.
6. 보고서의 READY는 계약 감사 완료이며 실전 검증 통과가 아니다. 장애면 BLOCKED와 누락물을 명시하고 재시도 루프를 만들지 않는다.

## 허용범위
- 코드 baseline을 별도 작업 디렉터리/브랜치에서 읽기. 기존 운영 작업 디렉터리를 checkout/reset/stash하거나 수정하지 않는다.
- QUANT-REPORT.md, docs/RULESET.md, docs/AUDIT-1.md, 해당 RL 문서와 daily_live.py/m15_live.py/hourly_a.py/idle_live.py/basket_live.py 및 직접 import된 신호·매매 함수·연구 버전의 의존성을 추적한다. 파일명이 틀리거나 없으면 rg로 실제 경로를 확인하고 미확인을 기록한다.
- A(새82), 15m, 1H, 빈칸엔진/코스닥인버스, D(Basket C), F5의 상태·버전을 분리한다. F5 운영 구현이 없으면 없음으로 기록한다.
- 이 TASK가 제공한 초안을 사실로 가정하지 말고 소스와 대조한다. exact comparison, ddof, quantile/rank/tie, EMA seed, 결측값, 신호 우선순위, 슬롯 분모, 재진입, 시간·지연, 호가·체결 불능까지 수치와 의사코드로 잠근다.
- 측정 계약용 JSON schema와 오프라인 pure function fixture만 새 연구 경로에 작성한다. 계좌·API·운영모듈 import의 부작용을 차단한다. 네트워크/주문 호출 없는 합성 입력으로 availability, 정정버전, 미래봉, 미체결, 부분체결, 동일봉 TP/SL, NAV, 현금흐름, 날짜 경계와 슬롯 처리를 검증한다.
- 기존 코드에 결함이 있어도 현행 규칙/as-is와 교정 제안/proposed를 별도 rule_id로 적는다. 운영 수정이나 과거 성과 상속 금지.
- KIS/DART 자료를 신호 입력·라벨·결측·사후 정정으로 나눈다. 실제 코드의 API method/path/TR ID/필드와 공식 문서를 매핑한다. 공식 문서로 확인 못한 항목은 미확인, KIS/DART에 없는 상장폐지·역사 유니버스·과거 공시 시각·컨센서스는 추가 출처 필요로 명시한다. 시크릿/계좌값 조회 없이 문서와 코드만 사용한다.

## 금지범위
실주문 및 모의 주문 API 호출 모두 금지. 기존 모의 봇은 관찰 유지한다.
운영 코드/설정/배분/계좌/인증/스케줄 변경·재시작·자동병합·새 Routine·실측계좌 수집·대규모 데이터 수집·성과 백테스트·새 threshold/보유기간 탐색 금지.
공개 저장소에 개인 NAV·잔고·주문 수량·계좌응답·토큰·원시 비공개 시장데이터·비공개 세션 URL을 넣지 않는다. NAV를 100으로 정규화해도 계좌 성과 공개이므로 이번에는 합성 fixture만 공개한다. 저장 목적지가 확인되지 않았으므로 private logger는 설계만 하고 비활성 상태다.

## 완료조건
새 결과 디렉터리 research-exchange/claude-to-gpt/RULES-0001/에 다음을 제출한다.
- REPORT.md: 주장/소스 확인/실행 검증/미확인을 분리. 수행·미수행·환경·명령·한계.
- RULES-LOCK.md: 각 전략의 완전한 입력/진입/청산/슬롯/우선순위/시각/상태전이. 모든 gate에 파일·함수·읽은 commit을 연결. 코드상 없던 임계값을 추가하지 않는다.
- DATA-AVAILABILITY.md: available_at/received_at/corrected_at/observed_at, DART 시각 미확인 경로, KRX/NXT 세션, 수급 확정시각, 당시 Universe(t) 결손.
- MEASUREMENT-CONTRACT.md와 schema: 실측의 필요한 필드, private destination 미정, read-only 수집의 향후 별도 범위. 비용·미체결·전략별 귀속·일별 MTM·월별 손실·MDD 계산. 이번에는 실제 수집하지 않는다.
- fixtures 및 test-result.json: 실행한 합성 사례별 입력/실제 출력/기대 출력/pass/fail. 실행하지 못하면 미실행. 정상 경로만 시험하지 않는다.
- manifest.json + 이번 입력 PR/head에 대한 receipt: schema_version=1, task_id, chain_id, round=1, status READY/BLOCKED, source_pr/source_head_sha, code_commit, evidence_paths, completed_at_kst.
입력 head를 제출 직전에 재확인하고 달라졌으면 그 버전을 다시 읽는다. 모든 파일의 ref와 실제 읽은 범위를 manifest에 적는다.

## 이후
GPT가 이 한 단계를 검토하기 전 ALLOC/ALPHA/MEAS 실수집은 시작하지 않는다.
최대 3라운드 또는 BLOCKED면 NEEDS_USER로 종료한다. 충분한 자료가 없어 실전 추천이 불가능하면 그 사실을 명시한다. 기존 전략을 이름만 보고 폐기하지 않는다.
