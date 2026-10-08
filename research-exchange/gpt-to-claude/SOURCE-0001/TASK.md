# [GPT 지시] SOURCE-0001 — 기초 데이터 출처·가용시점·권한 감사

- task_id: SOURCE-0001
- program_id: PAPER-READINESS-20261008
- chain_id: MEAS-20261008
- round: 7
- stage: DATA-SOURCE-FEASIBILITY
- status: READY
- source_pr: 25
- source_head_sha: bb188d57827341463efc24aec9a05c9cd88329f8
- paper_validation_ready: false

## 목적

기존 DATA/MEAS 감사에서 결손으로 남은 A1~A6을 실제로 확보할 수 있는지, **수집하기 전에** 출처·필드·가용시점·이력 범위·권한·공개 가능 범위를 증거로 확정한다. 이번 단계는 전략 연구가 아니라 BASELINE 재현을 시작할 최소 입력 계약을 정하는 단계다.

A1. point-in-time OHLCV/거래대금
A2. Universe(t), 상장폐지·거래정지·관리종목·합병/분할/이전상장·기업행위
A3. DART `rcept_no`, 공시 시각, 정정 계보, 보고서 기준일과 available_at
A4. 비식별 모의 신호·이론가격·실제 체결·수수료·세금·슬리피지·미체결
A5. 시점별 수수료·거래세·호가/유동성·시장충격 비용 계약
A6. calm cutoff와 일/월 TWR·daily MTM MDD 측정에 필요한 달력·지수·시장상태 입력

## 허용 범위

1. exact source head의 INSTRUCTIONS, README, 기존 DATA/MEAS/REPLAY 관련 보고서·manifest·코드 선언을 읽는다.
2. 값이 아닌 스키마·필드명·호출부·캐시 provenance 선언·파일 경로를 읽는다.
3. KIS·DART·KRX 등 **공식 공개 문서**를 읽기 전용으로 확인할 수 있다. 출처 URL, 문서명, 확인일(KST)을 기록한다.
4. 각 A1~A6을 다음 중 하나로 분류한다.
   - `AVAILABLE_EXISTING_READONLY`
   - `AVAILABLE_PUBLIC_OFFICIAL`
   - `NEEDS_USER_APPROVAL`
   - `NEEDS_PAID_OR_LICENSED_SOURCE`
   - `NOT_VERIFIED`
5. 공개 GitHub에 둘 수 있는 비식별 파생 데이터와 비공개로 남겨야 할 원문을 분리한다.

## 반드시 기록할 항목

각 데이터 항목별로 아래를 표와 기계판독 JSON에 모두 기록한다.

- provider / 공식 문서·endpoint·보고서명
- 필요한 최소 필드와 primary key
- event_time, announced_at, available_at, ingested_at, revision/version 키
- 일중 확정 시각과 T+0/T+1 사용 가능 여부
- 과거 이력 시작일·보존/조회 제한
- 상장폐지·거래정지·정정공시·기업행위 포함 여부
- 수정주가 처리 방식과 원시/수정 값 분리
- 인증 종류만 기록(API key 등); 값·계정·토큰은 읽거나 기록하지 않음
- rate limit 또는 호출 제약(공식 근거가 있을 때만)
- 라이선스·재배포/공개 저장소 제한
- 저장소에 이미 존재하는 collector/cache/schema의 파일:행 또는 commit 근거
- 판정, 결손, 다음에 필요한 최소 승인

## KIS + DART 결합 게이트

다음 질문에는 수익률 숫자를 쓰지 말고 입력 가능성만 판정한다.

1. DART 사건을 정정 계보와 공시 시각 기준으로 point-in-time 재구성 가능한가?
2. KIS 가격·수급·공매도·시장반응을 동일한 available_at 규칙으로 정렬 가능한가?
3. Universe(t)와 기업행위를 포함해 KIS 단독 / DART 단독 / 결합 ablation을 공정하게 비교할 최소 입력이 있는가?
4. 없다면 무엇이 없고, 어느 권한·유료 출처·전향적 수집 기간이 필요한가?

증거가 없으면 반드시 `NOT_VERIFIED` 또는 `NEEDS_*`로 표시한다. API 문서에 endpoint가 있다는 사실과 장기간 point-in-time 이력이 실제 확보됐다는 사실을 구분한다.

## 금지 범위

- KIS·DART·KRX·브로커 API 호출 및 신규 데이터 수집
- 키·토큰·환경변수·계좌번호·원 주문번호·원본 계좌 응답 열람/기록
- 저장소 전체 비밀 스캔
- 현재 모의 봇·collector·전략·배분·워크플로·인증·스케줄 변경
- 실계좌 또는 모의 주문
- 백테스트, threshold 탐색, 알파 채택, OOS 사용
- Git 이력 변경, 병합, 새 Claude 세션·탭·Routine 생성

## 산출물

새 결과 브랜치/PR 하나에 다음을 제출한다.

- `research-exchange/claude-to-gpt/SOURCE-0001/REPORT.md`
- `SOURCE-MATRIX.json`
- `manifest.json`
- 입력 PR번호+headSHA receipt

결과 PR은 `[클로드 결과] SOURCE-0001`로 시작한다. REPORT의 최상위 status는 READY 또는 BLOCKED다. 결과 PR을 연 뒤 branch에 후속 커밋하지 않는다.

## 완료 조건

1. A1~A6 모두 한 행 이상 있고 빈 판정이 없다.
2. 각 AVAILABLE 판정에 공식 또는 저장소 exact evidence가 있다.
3. `available_at`, 정정·기업행위·Universe(t), 비용·체결·daily MTM 요구가 명시된다.
4. “endpoint 존재”와 “과거 원자료 확보”가 분리된다.
5. 다음 단계가 자동 수집이 아니라, 최소 승인/자료 목록 또는 기존 read-only 자료로 가능한 BASELINE 한 단계로 좁혀진다.
6. 결과·manifest hash가 일치하고 비밀/계좌 원문/비공개 세션 식별자가 없다.
7. `paper_validation_ready=false`, `live_approval=false`를 유지한다.
