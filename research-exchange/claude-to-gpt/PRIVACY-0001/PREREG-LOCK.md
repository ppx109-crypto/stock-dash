# PRIVACY-0001 PREREG-LOCK — 공개 전 민감정보 차단 게이트 2판

- 지시: PR #22 head `c55fdb388edc683466f515630544b5f8e19a3474`. source PR #21 head `118551ea5943d484ba35de4f7c618ab5c8ba02a9`.
- 이 문서와 `fixtures/fixtures.json`(만드는 도우미 `fixtures/make_fixtures.py`), `tests/materialize.py`는 **게이트 · 시험 실행기를 쓰기 전에** 결과 가지의 첫 커밋으로 잠급니다.
- 잠그기 전에 본 것: PR #22 파일, DATA-0001 `validator.py`(PRIVACY_KEYS · has_key_deep)와 REPORT.
- 실제 장부 · Secrets · 환경변수 · 계좌 응답은 열지 않습니다.
- READY의 뜻은 **공개 차단 게이트의 합성 검증 통과뿐**입니다. 저장소 과거 이력이 깨끗하다는 뜻, 실제 자료 확보, 전략 신뢰성, `PAPER_VALIDATION_READY`, 실전 승인으로 쓰지 않습니다.

## 1. 합성 값 다루기
- fixture 파일에는 자리표시자(`{{SYN}}`, `{{TOKEN}}`, `{{SURL}}`)만 둡니다. 시험 때 `tests/materialize.py`가 fixture id로 정해진 합성 값을 **메모리에서만** 만듭니다.
- 합성 세션 주소 모양은 코드에서도 조각을 이어 만들어, 저장소 어느 파일에도 통째로 적히지 않게 합니다.
- 결과에는 경로 · 규칙 코드 · 개수 · 파일 hash · PASS/FAIL만 적고, 값은 적지 않습니다.

## 2. 키 규칙(구조 자료: dict · list를 끝까지 따라감)
- 정규화: `canon(k) = 영숫자만 남김(unicodedata.normalize("NFKC", k).casefold())`
- 금지 토큰 F(20개): `accountno, acctno, cano, acntprdtcd, brokerorderno, orderno, odno, rawresponse, rawpayload, appkey, appsecret, accesskey, secretkey, privatekey, accesstoken, refreshtoken, authorization, htsid, sessionurl, sessionid`
- 판정
  - `canon(k)`가 F에 있으면 금지입니다.
  - 길이 6 이상 토큰은 `canon(k)`가 그 토큰으로 **끝나도** 금지입니다(예: 앞에 붙은 접두어). 여러 토큰이 맞으면 정확히 같은 것을 먼저, 없으면 가장 긴 것을 씁니다. 길이 5 이하 토큰(`cano`, `odno`)은 정확히 같을 때만 금지입니다.
  - 허용 키 목록(정확히 같으면 금지 아님): `orderid, tradeid, recordid, evidenceref, normalizedsha256, rawpayloadsha256, strategyhash, cutoffhash`
  - **값이 대입된 경우만** 걸립니다. 값이 null · 빈 문자열 · 빈 목록 · 빈 dict이면 걸지 않습니다.
- 규칙 코드: `KEY_FORBIDDEN:<토큰>`
- 금지 키 아래의 값도 계속 따라가 검사합니다.

## 3. 텍스트 규칙(문서 · 구조 자료 안의 문자열 값 모두)
- `TEXT_SESSION_URL`: 비공개 세션 주소 모양(호스트 `claude` + `.ai/code/` + `session_`, 그 뒤 영숫자 6자 이상)
- `TEXT_BEARER`: `bearer` + 공백 + 자격증명 모양 8자 이상(대소문자 무시)
- `TEXT_KEY_ASSIGN:<토큰>`: 따옴표 · 백틱이 있을 수 있는 `키 [:=] 값` 형태에서 키가 2장의 금지 판정에 걸리고, 값이 비어 있지 않고 `null/none/nil/-`가 아닌 경우
- 값 없는 설명(예: 백틱으로 감싼 필드 이름 뒤에 `:`나 `=` 없이 설명이 이어짐)은 걸지 않습니다.
- 규칙 코드는 fixture마다 집합으로 비교합니다(같은 코드는 한 번).

## 4. 고정 fixture
### 공격 34개(모두 차단돼야 함, 기대 규칙 집합이 정확히 같아야 함)
| id | 형태 | 기대 |
|---|---|---|
| A01~A06 | `ODNO` · `odno` · `order_no` · `ORDER-NO` · `orderNo` · `broker_order_no` | odno · odno · orderno · orderno · orderno · brokerorderno |
| A07~A10 | `account_no` · `acctNo` · `CANO` · `acnt_prdt_cd` | accountno · acctno · cano · acntprdtcd |
| A11~A15 | `appkey` · `APP_SECRET` · `access-key` · `secretKey` · `private_key` | appkey · appsecret · accesskey · secretkey · privatekey |
| A16~A18 | `access_token` · `refreshToken` · `Authorization` | accesstoken · refreshtoken · authorization |
| A19 | 값 안의 Bearer 자격증명 | TEXT_BEARER |
| A20 · A21 | `raw_response`(dict 값) · `rawPayload` | rawresponse · rawpayload |
| A22 · A23 | `session_url` · `sessionId` | sessionurl · sessionid |
| A24 | 값 안의 비공개 세션 주소 | TEXT_SESSION_URL |
| A25 | dict 안 dict 안 `ODNO` | odno |
| A26 | list 안 `order_no` | orderno |
| A27 | dict→list→dict 안 `acct_no` | acctno |
| A28 | 맨 위가 list, 그 안 `access_token` | accesstoken |
| A29 | 텍스트 `ODNO = 값` | TEXT_KEY_ASSIGN:odno |
| A30 | 텍스트 `Authorization: Bearer 값` | TEXT_BEARER, TEXT_KEY_ASSIGN:authorization |
| A31 | 텍스트 안 비공개 세션 주소 | TEXT_SESSION_URL |
| A32 | 접두어 키 `kis_app_key` | appkey |
| A33 | 전각 문자 `ＯＤＮＯ`(NFKC) | odno |
| A34 | JSON 모양 텍스트 `"orderNo": "값"` | TEXT_KEY_ASSIGN:orderno |

### 허용 12개(아무것도 걸리면 안 됨)
| id | 내용 |
|---|---|
| P01 | `order_id` · `trade_id` · `record_id` |
| P02 | `evidence_ref`(ev_ + 16 hex) |
| P03 | `normalized_sha256` · `raw_payload_sha256` |
| P04 | `strategy_hash` · `cutoff_hash` |
| P05 | 단순 전략 설명 문장 |
| P06 | 값 없는 위험 필드명 설명(`order_no` 필드는 … 공개하지 않는다) |
| P07 | "authorization 헤더와 토큰은 기록하지 않는다" |
| P08 | `volcano_count`(cano를 포함하지만 정확히 같지 않음) · `session`(금지 아님) |
| P09 | "새 세션을 만들지 않는다. session_url 키는 금지 목록에 있다." |
| P10 | `order_no`가 null(값 없음) |
| P11 | list 안 `order_id` · `public_ok` |
| P12 | "ODNO 같은 키는 대소문자와 상관없이 막는다." |

### mutant 9개(사전 지정 fixture가 잡아야 함)
| mutant | 결함 | 잡을 fixture |
|---|---|---|
| M1 | casefold 제거 | A01 · A09 · A12 |
| M2 | 구분자 제거 누락 | A03 · A04 · A06 |
| M3 | 주문번호 토큰(orderno · odno · brokerorderno) 제거 | A01 · A03 · A05 |
| M4 | 중첩 dict 순회 제거 | A25 · A27 |
| M5 | list 순회 제거 | A26 · A28 |
| M6 | 세션 주소 검사 제거 | A24 · A31 |
| M7 | Authorization 토큰 · Bearer 검사 제거 | A18 · A19 · A30 |
| M8 | 결과에 발견 값 포함(노출) | 시험 실행기의 독립 redaction 검사(REDACTION) |
| M9 | 게이트 자체 redaction 자기검사가 늘 통과 + 값 노출 | 독립 redaction 검사(REDACTION) |

잡았다는 뜻은 지정 fixture 가운데 하나 이상이 기대와 달라지거나, REDACTION 검사가 합성 값을 찾아내는 것입니다.

## 5. 고정 판정(하나라도 실패하면 status BLOCKED)
1. 공격 34/34가 기대 규칙 집합과 정확히 같음
2. 허용 12/12에서 오탐 0
3. mutant 9/9 검출
4. 같은 입력 2회 정규화 결과 hash가 같음
5. 격리
   - 소켓 연결 차단, 환경변수는 실행 시작 때 프로세스 안에서 비움
   - 허용 디렉터리(이 폴더 · 파이썬 표준 라이브러리) 밖 파일 열기 0
   - 쓰기는 이 폴더 안만, 시작 뒤 새로 불린 모듈은 허용 디렉터리 안만
6. **출력 redaction 자기검사**
   - 게이트 출력 · `TEST-RESULT.json` · `REPORT.md` · `manifest.json` · PR 본문 파일 · 이 가지 커밋 메시지에 합성 값 0
   - 같은 대상에 세션 주소 모양 0
   - 같은 대상에 `session_` 뒤 영숫자 10자 이상 0
   - `tests/publish_check.py`로 확인하며, PR 연 뒤에는 PR 본문을 다시 받아 1회 더 확인합니다(채팅 보고만, 가지에는 커밋하지 않음).

## 6. 예산
- 표준 라이브러리만 씁니다. 네트워크 · API 0.
- 결과 실행(`tests/run_tests.py`)은 최대 3회, 공개 검사(`tests/publish_check.py`)는 최대 3회입니다. 실행마다 이유를 남기고, 첫 결과는 `TEST-RESULT.run1.json`으로 보존합니다.
- 결과를 본 뒤 fixture나 규칙을 바꾸면 그 사례는 사전검정이 아니라고 표시합니다.
- 운영 위험은 경로 · 필드명 · 조치 필요만 적습니다.
