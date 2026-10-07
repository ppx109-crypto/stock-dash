# PRIVACY-0001 사전등록

- source: PR #21 @ `118551ea5943d484ba35de4f7c618ab5c8ba02a9`
- 연구 단계: RECOVERY-PUBLICATION-GATE
- 성과/알파 연구: 하지 않음
- 실제 자료 접근: 하지 않음
- 실행 상한: 결과 생성 최대 3회

## 고정 시험군

### 금지 사례(최소 24)

|군|필수 변형|
|---|---|
|원 주문번호|ODNO, odno, order_no, ORDER-NO, orderNo, broker_order_no|
|계좌|account_no, acctNo, CANO, acnt_prdt_cd|
|키/비밀|appkey, APP_SECRET, access-key, secretKey, private_key|
|토큰/인증|access_token, refreshToken, Authorization, bearer 자격증명|
|원문|raw_response, rawPayload|
|세션|session_url, sessionId, 비공개 Claude session URL|
|중첩|dict 내부, list 내부, dict→list→dict|

각 fixture의 실제 합성 값은 결과물에 다시 출력하지 않는다. fixture hash와 규칙 코드만 결과에 남긴다.

### 허용 사례(최소 10)

`order_id`, `trade_id`, `record_id`, `evidence_ref`, `normalized_sha256`, `raw_payload_sha256`, `strategy_hash`, `cutoff_hash`, 단순 전략 설명, 값 없는 위험 필드명 설명.

### mutant(최소 8)

M1 casefold 제거, M2 구분자 정규화 제거, M3 주문번호 목록 제거, M4 중첩 dict 순회 제거, M5 list 순회 제거, M6 세션 URL 검사 제거, M7 Authorization 검사 제거, M8 redaction 자기검사 제거.

## 고정 판정

- 모든 금지 fixture가 정확한 규칙 코드로 차단
- 허용 fixture 오탐 0
- mutant 8/8 이상 사전 지정 fixture로 검출
- 동일 입력 2회 canonical 결과 hash 동일
- 네트워크 0, 허용 디렉터리 밖 파일 읽기 0, 파일 쓰기는 결과 폴더 안만
- 공개 산출물에서 합성 비밀값·비공개 session 식별자 0
- 하나라도 실패하면 status BLOCKED
