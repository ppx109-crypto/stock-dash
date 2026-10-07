# REPLAY-0002 PREREG-LOCK — 시점별 체결 입력 복원 가능성 감사

- 지시: PR #18 head `4cc7d101211cd3a74b3624a5106694ceb083863d` (TASK · PREREG · REVIEW · INDEPENDENT-CHECK · receipt · PR 본문)
- 이 문서는 **분류기 작성 · 실행 · 결과 보기 전에** 쓰고 결과 가지의 첫 커밋으로 잠급니다. 시각과 hash는 `PREREG-LOCK.stamp.json`에 적습니다.
- 잠그기 전에 본 것(결과 아님, 공개):
  - PR #18 파일들
  - 장부를 만든 `RULES-0002/diag/d1_diag.py` 앞부분: `nrl` 캐시 + `ntools.once` 엔진의 ASIS 실행
  - 앞서 제출한 MEAS-0001 `INVENTORY.json`: `nrl-cache.pkl`은 git 밖에 있고 생성 커밋이 없음. price · investor · event-data는 수집기가 덮어쓰며 git 이력이 2026-09-09부터. calm 문턱은 전 기간 값(2.1763)
  - 고정 커밋의 최상위 폴더 이름과 세 자료 폴더의 파일 수(507 · 440 · 509, 약 149MB)
- 위 사실은 앞 단계의 **탐색 결과**이며, 이번 판정의 사전검정이라고 부르지 않습니다. 자료 파일 내용과 기준 엔진 코드는 아직 열지 않았습니다.

## 1. 고정 입력
| 별칭 | 내용 | 고정값 |
|---|---|---|
| L | 495행 장부 | `RULES-0002@a61f033ecd16ba0976c955a93bfec70c7463ad53` `research-exchange/claude-to-gpt/RULES-0002/results/d1_ledger_ASIS.csv`, sha256 `86c5f56df56d8a7ac5b691152343568d8436f1bea90c10add318bbd9b354209b`(다르면 중지) |
| B | 연구 기준 코드 | `00b98ab1655c84806357f44f2de6f1509ef1447f` — 정적 읽기만, import · 실행 안 함 |
| G | 장부 생성기 | `d1_diag.py` · `common.py` @a61f033 |
| C | 저장소 자료 | `origin/main` @`5998f42e9acbb0fd3912ae9ebc63c5e1edfb39dc`(2026-10-08 07:31 KST 커밋) — 그 커밋의 파일과 그 이전 git 이력만 |
| K | 회계 커널 | PR #17 head `63e47a1bc49f183a692e606d0c55191e716e90a2` `REPLAY-0001/account_kernel.py` — 참조만, 수정 안 함 |
| X | 쓰지 않음 | `nrl-cache.pkl` · `.cache/hourly_tables.pkl` · `study/features.json`(git 밖), 운영 봇 상태, 계좌 · 비밀 · `.env`, 네트워크 |

## 2. 절차(한 번에 하나씩)
1. **원천 찾기(A)**: B의 연구 엔진 경로(`nrl.py`, `research/ntools.py`와 그것이 부르는 기준 모듈)를 정적으로 읽어, 엔진이 읽는 자료 경로 · 환경변수 · 캐시를 목록으로 만듭니다. 각 원천은 C에서 다음을 셉니다.
   - 파일 수, 레코드 키, 시점 필드(`as_of/available_at/fetched/rcept/version/source/adjusted` 류)의 유무
   - git 이력의 첫 · 마지막 커밋과 커밋 수
   - 결과: `INPUT-INVENTORY.json`
2. **TASK 필수 원천 찾기(A2)**: Universe(t) · 거래정지 · 상하한가 · 신규상장 · 상장폐지 · 기업행동 · 비용은 엔진이 안 읽더라도 C 전체에서 찾습니다.
   - 방법: 경로 이름이나 레코드 키에 아래 낱말이 있는 파일을 후보로 삼고, 날짜별 스냅숏 · 기록인지 확인합니다.
   - 낱말: `universe, listing, list, 상장, delist, 폐지, halt, suspend, 정지, 관리, limit, 상한, 하한, split, 분할, 병합, 증자, 감자, fee, tax, 수수료, 세금, cost`
3. **행 분류(B)**: 결정론적 분류기 1세트로 495행 × 13필드에 상태를 매기고 `COVERAGE.json`에 씁니다.
4. **시험**:
   - 같은 입력이면 같은 결과 hash
   - 장부의 `pnl_pct_engine` 열을 정해진 순서로 섞어도 결과 hash가 같음
   - 진입 쪽 필드는 `exit` 열을 바꿔도 같음
   - 분류기 소스가 `pnl_pct_engine` 값을 읽지 않음(정적 검사)
   - 네트워크 차단 · 운영 모듈 import 0 · `.pkl` 파일 열기 0(파일 열기 기록 훅으로 확인)

## 3. 필드(13개, 행마다)
| id | 필드 | 볼 날짜(찾는 자리일 뿐 원인 입력 아님) |
|---|---|---|
| F01 | strategy_id | — |
| F02 | trade_id · 부분청산 연결 | — |
| F03 | 진입 신호 입력값(엔진이 쓰는 각 계열의 그날 값) | entry |
| F04 | 진입 신호의 계산 시점 · available_at · 버전 | entry |
| F05 | 가장 빠른 주문 KST 시각 | entry |
| F06 | model-fill 봉 · 가격 필드 · 조정 여부 | entry 다음 거래일 |
| F07 | 수량 입력(당시 현금 · NAV · 배분 · 가격 · 비용) | entry |
| F08 | 청산 신호 입력값 · available_at | exit(찾는 자리만) |
| F09 | 평가가격 as_of · available_at · version · source | entry~exit |
| F10 | Universe(t) | entry |
| F11 | 거래가능성: 거래정지 · 상하한가 · 신규상장 · 상장폐지(넷 따로 기록, 필드 상태는 가장 나쁜 것) | entry~exit |
| F12 | 기업행동 | entry~exit |
| F13 | 비용 · 세금 · 슬리피지 출처와 적용기간 | entry · exit |

## 4. 상태 규칙(고정)
판정 순서(앞에 걸리면 그 상태):
1. 값이 C의 어느 파일 · 이력에도 없음 → `MISSING`
2. 값은 있으나 레코드에 출처 · 시점 · 버전 · 조정 여부 중 하나라도 확인할 수 없음, 또는 값을 만든 실행에 이미 확인된 미래참조가 있음 → `UNTRUSTED`
3. 둘 이상의 합리적 해석(코드 의미 · 겹친 버전 · 부분청산/독립매매)이 있고 원증거로 하나를 고를 수 없음 → `AMBIGUOUS`
4. 아래 고정 규칙 R1~R8 중 하나로 PRESENT 값에서 결정론적으로 만들 수 있음 → `DERIVABLE_WITH_LOCKED_RULE`
5. 값 · 시점 · 출처가 레코드에 직접 있음 → `PRESENT`

여러 사유가 겹치면 위 순서로 하나를 고르고, 나머지 사유도 `reasons`에 모두 남깁니다.

증거 기준:
- **git 커밋 시각은 그 값이 그때 세상에 알려졌다는 증거가 아닙니다.** 레코드 안의 시점 필드만 증거로 봅니다.
- 덮어쓰는 파일은 지금 값이 처음 도착한 값과 같은지 증명할 수 없으면 버전 미확인(UNTRUSTED)입니다. git 이력에서 같은 날짜 값이 바뀐 적이 있으면 AMBIGUOUS 사유도 함께 남깁니다.
- 현재 보유 · 현존 종목 목록으로 과거 Universe(t)를 대신하지 않습니다(→ MISSING).
- 날짜만 있는 행에 09:00 · 종가 · 다음날 시가를 임의로 넣지 않습니다. 넣으려면 아래 규칙이어야 하고, 그 규칙의 입력도 PRESENT여야 합니다.
- 거래량 0 같은 간접 신호로 거래정지를 추정하지 않습니다(→ 명시 기록 없으면 MISSING).

고정 규칙(이것만 허용):
- **R1** strategy_id = `D1_NEW82_ASIS`. 근거: 495행 전부가 G의 SPECS `ASIS` 실행 결과.
- **R2** trade_id = `D1A-` + sha256(`code|entry`)[:10]. `(code, entry)` 묶음이 1행일 때만 해당. 2행 이상이면 부분청산인지 독립매매인지 고를 증거가 없어 F02 = AMBIGUOUS.
- **R3** 가장 빠른 주문 시각: 그날 종가로 판단하는 신호는 CLAUDE.md 규칙에 따라 15:15 확인 증거(15분봉)가 없으면 '다음 거래일 09:00 KST'. 다음 거래일 = 그 종목 일봉 계열에서 entry 다음 날짜. 입력 일봉이 PRESENT · DERIVABLE일 때만 성립합니다.
- **R4** model-fill = 다음 거래일 시가, 원주가(수정주가 아님). 레코드에 시가와 조정 여부 표시가 있을 때만 성립합니다.
- **R5** 일봉 종가의 available_at = 그날 15:30 KST. 투자자별 수급 · 공시 · 실적 · 증권사 의견은 다음 거래일부터(CLAUDE.md). **두 조건이 모두 있어야 성립합니다**: 레코드에 as_of 날짜가 있고, 처음 도착한 버전임을 증명할 수 있어야 합니다.
- **R6** 상하한가 = 전일 원종가 ±30%(2015-06-15 이후, 호가단위 내림). 원종가 · 고가 · 저가가 PRESENT일 때만 성립합니다.
- **R7** 공시 기업행동의 시점 = 공시 접수일(rcept) 다음 거래일. 레코드에 접수일 · 종류 · 비율 · 기준일이 있을 때만 성립합니다. 다만 REPLAY-0001 커널은 분할 · 병합을 UNSUPPORTED로 처리하므로, 보유 기간에 그런 사건이 있으면 F12 = MISSING(사유 KERNEL_UNSUPPORTED_CORP_ACTION)입니다.
- **R8** 수량 = floor(배분 한도 ÷ (가격×(1+매수비율))) 후 1주씩 줄이기(REPLAY-0001 커널 정책). 배분 한도에는 당시 NAV가 필요하므로, 앞서 열린 모든 행의 F06이 PRESENT · DERIVABLE이어야 하고 비용(F13)도 그래야 합니다. 장부 `slots`는 미래참조가 확인된 실행(전 기간 calm 문턱)의 산출이므로 UNTRUSTED로 봅니다.

비용(F13):
- 코드 안의 상수에 외부 출처와 적용기간이 없으면 UNTRUSTED입니다.
- 상수가 없으면 MISSING입니다.
- REPLAY-0001의 합성 비용률은 SYNTHETIC이며 OBSERVED가 아닙니다.

`HISTORICAL_MODEL`과 `OBSERVED_KIS_PAPER`:
- 495행은 모두 연구 모형 출력이므로 증거 종류는 HISTORICAL_MODEL입니다.
- 모의 서버 체결 원문이 C에 없으면 OBSERVED 증거는 0건으로 적습니다.

## 5. 행 · 전체 판정
- 행 완전 재생 가능: 13필드 모두 PRESENT 또는 DERIVABLE_WITH_LOCKED_RULE.
- 전체 판정:
  - 495/495 완전 → `RECONSTRUCTIBLE`
  - 모든 행에서 F04(신호 시점) 또는 F06(model-fill 가격) 중 하나라도 PRESENT · DERIVABLE이 아님 → `BLOCKED_NEEDS_DATA`
  - 그 밖 → `PARTIAL`
- 결과 status:
  - `BLOCKED_NEEDS_DATA`이면 `BLOCKED`(감사 자체는 끝남)
  - 그 밖은 `READY`
  - 근거가 없으면 '검증하지 못함'으로 씁니다.
- 공개:
  - 필드별 분모(495)와 분자를 공개합니다.
  - AMBIGUOUS · MISSING · UNTRUSTED는 행 수와 비식별 예시(행 hash 앞 10자리)로 적습니다.
  - 행 식별 hash = sha256(`행번호|code|entry`)이며, 전체 목록의 hash도 함께 적습니다.

## 6. 예산 · 중단
- 저장소 파일 읽기와 git 이력 선형 조회만 합니다. 네트워크 · API 0회, 전략 매개변수 · threshold 탐색 0회, 성과 계산 0회.
- 분류 규칙은 1세트입니다. 실행은 본 실행 1회와 결정론 확인용 재실행 1회까지(합 2회)입니다. 섞기 시험은 같은 프로세스 안에서 분류 함수에 바꾼 입력을 넣는 방식이며, 결과 재실행으로 세지 않습니다.
- 목표: 5분 · 512MB 이내.
- 중단 조건:
  - L의 hash가 다르면 중지합니다.
  - 원천 출처 확인에 비밀 · 계좌 원문 · 외부 인증이 필요하면 `NEEDS_USER/NEEDS_DATA`로 끝냅니다.
  - 운영 코드 · 봇을 바꿔야만 확인할 수 있는 항목은 바꾸지 않고 '검증하지 못함'으로 둡니다.
  - 495행 전부에서 신호 시점 또는 model-fill 가격 근거가 없으면, 세부 재생으로 넘어가지 않고 `BLOCKED_NEEDS_DATA`로 끝냅니다.
- 분류기에 결함이 있어 고치면, 고치기 전후와 첫 결과를 보존하고 REPORT에 적습니다. 상태 규칙(4장)은 바꾸지 않습니다.
