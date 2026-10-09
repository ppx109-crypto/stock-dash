# REPLAY-OFFICIAL-DATE-EVIDENCE-RECOVERY-0001 — 클로드 사전등록(원문 대조 전)

- 지시: GPT PR #91 head `c463763d`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `d3ad50f6efd753c6`
  - SOURCE_PACKET `e7a3321807dc89bf`
  - PREREG `7f861d73c2cc5016`
  - REVIEW `fc0b565c8eea5466`
  - receipt `4124efdcbc952d16`
- source: PR #90 head `f2e59846` 일치를 확인했습니다.
- 범위: 주식 액면분할(split) · 주식병합(reverse_split) 두 사건만 봅니다. 나머지 7개 기업행동으로 넓히지 않습니다.
- 금지(지킴):
  - 데이터 API · 토큰 · 키 · Secrets
  - 수집 · 캐시 · 종목 원시자료
  - 재생 · 성과
  - threshold · 배분 · 운영 · 워크플로
  - 새 세션 · Routine · 자동병합
  - 비공식 2차 자료
- 이 커밋 전에는 SOURCE_PACKET의 URL을 하나도 열지 않았습니다.

## 1. 원문 직접 대조(각 URL 최대 1회 · 재시도 없음)
- 대상은 패킷의 URL 5개입니다.
  - S1 주 · S1 보조 · S2(kind.krx.co.kr)
  - S3 · S4(law.krx.co.kr)
- `curl` 한 번씩만 엽니다. 실패하면(403 · 접속 거부 · 빈 본문) 다시 시도하지 않습니다.
- 실패한 항목은 증거 등급을 `GPT_CAPTURED_OFFICIAL_INDEX`(GPT가 검색 색인에서 옮긴 공식 URL · 짧은 발췌)로 낮춥니다.
- 성공하면 원문 sha256과 짧은 원문 인용으로 `OFFICIAL_TEXT_DIRECT` 등급을 줍니다. 원문은 로컬에만 두고 커밋하지 않습니다.
- 새 네트워크 허용을 요청하지 않습니다. PR #90에서 막힌 기본 페이지(KIND 첫 화면 · law.krx 첫 화면)는 다시 열지 않습니다.

## 2. 판정 규칙(대조 결과를 본 뒤 바꾸지 않음)
- **증거 등급**
  - `OFFICIAL_TEXT_DIRECT`(직접 받은 공식 원문)
  - `GPT_CAPTURED_OFFICIAL_INDEX`(패킷 발췌)
  - `INFERENCE`(위 둘에서 끌어낸 추론)
- **판정**(PR #91 PREREG와 같음)
  - ACCEPT: 공식 출처가 필드나 일반 규칙을 **직접** 명시
  - REVISE: 공식 필드는 있으나 일반화에 조건이 더 필요
  - BLOCKED_NO_OFFICIAL_EVIDENCE: 이름이나 시점 의미를 직접 뒷받침하지 못함
- **등급 상한:** `GPT_CAPTURED_OFFICIAL_INDEX`만으로는 최대 REVISE입니다. 색인 발췌는 원문 전체가 아니고 제가 대조하지 못했기 때문입니다.
  - 예외: 패킷이 **서식 이름 · 필드 이름 자체**를 공식 URL과 함께 적은 경우(예: `70128_주식분할 결정`, 필드 '신주의 효력발생일')는 "그런 필드가 있다"는 사실에 한해 ACCEPT 후보로 봅니다. 그 필드의 **뜻**은 따로 판정합니다.
- **사건별 판정 항목**
  1. `report_form_code` · `report_name`: 70128 = 주식분할 결정, 70129 = 주식병합 결정
     - DART 공시목록의 `report_nm` 문자열과 같은지는 이 패킷이 증명하지 않으므로 따로 적습니다.
  2. `legal_effective_date` = 서식 필드 '신주의 효력발생일' 그대로입니다. 가격 기준일 · 매도 가능일로 대체하지 않습니다.
  3. `price_basis_date`
     - S3가 **산식**(직전 매매거래일 종가 × 비율)만 정하는지, **첫 적용 달력일**을 정하는지 나눠 봅니다. 날짜를 직접 정하지 않으면 그 날짜는 INFERENCE입니다.
     - S4의 '분할/병합되는 날'이 거래 재개일과 같다는 공식 문구가 없으면 INFERENCE입니다.
  4. `first_sellable_date`
     - 예시 3건(분할 2 · 병합 1)에서 '매매거래정지 종료일 다음 거래일'과 '신주권상장예정일'이 같은지 대조합니다.
     - 다음 거래일은 **요일만으로** 셉니다. KRX 휴장일 달력 원문은 범위 밖이라, 공휴일 여부는 "확인 못 함"으로 둡니다.
     - 예시가 같아도 일반 규칙의 공식 문구가 없으면 ACCEPT하지 않습니다.
  5. 정정: 정정 예시는 최신 정정본 기준 일정과 정정 사유를 따로 적습니다. PR #90의 `UNKNOWN_CA_VERSION_PIT` · 당일 사용 금지 · fail-closed 유지 여부도 판정합니다.
  6. 시장 범위: S3 · S4가 유가증권시장 규정인지 코스닥에도 적용되는지 패킷이나 원문에 없으면 "코스닥 미확인"으로 둡니다.
- **상태**
  - READY: 두 사건의 보고서명 · 효력발생일에 더해, 가격 기준일과 최초 매도가능일의 **일반 규칙**이 공식 문구로 직접 증명될 때(PR #91 TASK 완료 조건)
  - 아니면 BLOCKED입니다.

## 3. 산출물
- `REPORT.md`: 두 사건 × 세 시점 + 보고서명 — CLAIM / OFFICIAL TEXT / INFERENCE / VERDICT
- `evidence/split-reverse-split-date-contract.json` · `evidence/source-access-log.json` · `evidence/run.log`
- PR #88 계약 좁은 수정안(채울 수 있는 칸 / 계속 UNKNOWN인 칸)
- `manifest.json` · `receipt.json`
