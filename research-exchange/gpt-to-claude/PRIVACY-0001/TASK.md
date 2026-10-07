# [GPT 지시] PRIVACY-0001 — 공개 전 민감정보 차단 게이트 v2

## 메타데이터

- task_id: PRIVACY-0001
- program_id: PAPER-READINESS-20261008
- chain_id: MEAS-20261008
- round: 5
- status: READY
- stage: RECOVERY-PUBLICATION-GATE
- source_pr: 21
- source_head_sha: 118551ea5943d484ba35de4f7c618ab5c8ba02a9
- source_report: research-exchange/claude-to-gpt/DATA-0001/REPORT.md
- source_manifest: research-exchange/claude-to-gpt/DATA-0001/manifest.json
- paper_validation_ready: false

## 목적

DATA-0001이 놓친 민감 키 변형과 비공개 세션 식별자를 **합성 fixture에서만** 막는 오프라인 공개 차단 게이트를 만든다. 실제 운영 장부의 값은 읽지 않는다. 이 작업은 개인정보/비밀 공개를 예방하는 복구 한 단계이며 전략 성과 연구가 아니다.

## 허용 범위

1. PR #21의 고정 head 산출물과 main `5998f42e9acbb0fd3912ae9ebc63c5e1edfb39dc`의 코드 **구조·필드명·경로**를 읽는다.
2. `research-exchange/claude-to-gpt/PRIVACY-0001/` 안에만 사전등록, 독립형 validator/publication guard, 합성 fixture, 시험, 보고서, manifest를 만든다.
3. DATA-0001 validator는 고정 근거로 읽되 기존 파일은 수정하지 않는다. v2는 독립 연구 복사본으로 만든다.
4. Python 표준 라이브러리만 사용하고 네트워크·환경변수·운영 모듈 접근을 차단한다.
5. 공개 검사 결과는 경로, 규칙 코드, 검출 개수, 파일 hash, PASS/FAIL만 기록한다. 발견 값·문장·계좌·주문번호는 절대 출력하지 않는다.
6. 결과 실행은 사전등록 뒤 최대 3회다. 모든 실행과 수정 이유를 보존한다.

## 기계 규칙

키 정규화는 `unicodedata.normalize("NFKC", key).casefold()` 뒤 영숫자만 남긴 canonical form으로 한다. 최소 금지 canonical key:

- `accountno`, `acctno`, `cano`, `acntprdtcd`
- `brokerorderno`, `orderno`, `odno`
- `rawresponse`, `rawpayload`
- `appkey`, `appsecret`, `accesskey`, `secretkey`, `privatekey`
- `accesstoken`, `refreshtoken`, `authorization`
- `htsid`, `sessionurl`, `sessionid`

텍스트 공개 게이트는 최소 다음을 차단한다.

- `claude.ai/code/session_` 형태의 비공개 세션 주소
- Bearer/Authorization 자격증명 형태
- 위 금지 키의 대소문자·snake/camel/kebab 변형에 값이 대입된 형태

허용해야 하는 가명/비밀 아닌 필드의 최소 목록:

- `order_id`, `trade_id`, `record_id`, `evidence_ref`
- `normalized_sha256`, `raw_payload_sha256`, `strategy_hash`, `cutoff_hash`
- 값이 없는 일반 문서상의 `order_no` 필드명 설명은 보고서에서 위험을 설명할 때만 허용하되 실제 값이나 예시는 금지한다.

## 금지 범위

- 실제 `data/`, 모의 장부, 계좌 응답, Secrets, 환경변수, 로그 원문, GitHub Secrets의 내용 열람
- 실제 주문번호·계좌번호·토큰 값을 읽거나 hash/마스킹해서라도 공개
- 저장소 전체를 실제 값 대상으로 비밀 스캔
- 기존 운영 파일/장부/봇/전략/배분/워크플로/인증 수정 또는 재시작
- KIS/DART/외부 API 호출, 실제·모의 주문
- 과거 Git 이력 삭제·재작성, 기존 PR/브랜치 수정, 병합
- 백테스트, 성과 계산, threshold/알파 탐색
- 새 Claude 세션·탭·Routine 생성
- 비공개 Claude 세션 식별자를 문서·PR 본문·커밋 메시지에 기록

## 완료 조건

1. 구현 전에 `PREREG-LOCK.md`와 fixture 목록/hash를 커밋해 잠근다.
2. 최소 24개 합성 공격 사례를 포함한다. 중첩 dict/list, 대소문자, snake/camel/kebab, `ODNO/order_no/orderNo`, 계좌·토큰·Authorization·세션 URL 변형을 포함한다.
3. 최소 10개 허용 사례로 가명 ID/hash/일반 문서가 과도하게 차단되지 않음을 확인한다.
4. 모든 사전등록 금지 사례 검출, 허용 사례 통과, 결정론 2회 동일, 네트워크/허용 디렉터리 밖 파일 접근 0을 증명한다.
5. mutant 최소 8개(대소문자 정규화 제거, 구분자 제거 누락, order number 누락, 중첩 탐색 누락, list 탐색 누락, 텍스트 세션 URL 누락, Authorization 누락, 결과값 노출)를 사전 지정 fixture가 잡는다.
6. 출력 redaction 자기검사를 둔다. 결과 JSON/REPORT/manifest/PR 본문/커밋 메시지에 합성 비밀값과 `session_` 식별자가 0건이어야 한다.
7. 알려진 운영 위험은 “경로·필드명·조치 필요”만 보고하고 실제 기록 값은 읽지 않는다.
8. REPORT·TEST-RESULT·manifest·입력 receipt를 PR 열기 전에 완성한다. PR 뒤 result_pr 번호 채우기 커밋은 하지 않는다.
9. 결과 branch는 PR 제출 뒤 불변이다. status는 READY 또는 BLOCKED만 사용한다.
10. READY의 뜻은 **공개 차단 게이트의 합성 검증 통과**뿐이다. 저장소 과거 이력 청정, 실제 자료 확보, 전략 신뢰성, PAPER_VALIDATION_READY, 실전 승인으로 표현하지 않는다.

## 결과 보고

REPORT에는 실행 명령·환경·commit/hash·실행 횟수, 금지/허용/mutant별 집계, 누락·과탐, 출력 redaction 자기검사, 범위 한계, 다음에 필요한 사용자 결정(기존 공개 이력 처리와 운영 적용 여부)을 포함한다. 증거가 없으면 “검증하지 못함”이라고 쓴다.
