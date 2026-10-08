# REVIEW — PR #86 REPLAY-RAW-PRICE-CONTRACT-0001

- source_pr: 86
- source_head_sha: `916bc6781eb27000ec8f7b97a2907b28cd89673e`
- source_status: READY
- reviewed_at_kst: 2026-10-09T00:31:04+09:00
- verdict: **READY 결과의 범위는 채택하되, 실제 수집·재생 전 계약 보강 필요**
- paper_validation_ready: false

## 채택한 근거

1. 현재 후보 일봉 D1+BASKET의 148체결(D1 52/71, BASKET 12/13), off-tick 23, on-tick 미확인 125를 재현했다.
2. 공개/로컬 경계를 분리했고 실제 종목·날짜·수량·가격·salt·API 원문을 커밋하지 않았다.
3. 외부 API·네트워크·Actions·Secrets·Train 재생·성과/NAV 계산은 0회였다.
4. 재생 어댑터는 원주가 호가 배수, 원 notional 비용, 수량·현금 항등식, 기업행동 명시 레코드의 기본 골격을 제공한다.
5. 합성 fixture 최초 실패와 입력값 한 건 수정, 재실행 결과를 보존했다. 어댑터 본체는 사전등록판과 동일하다.
6. +19.90%를 검증값으로 승격하지 않았고 148건 전부를 공식 원주가 미확인으로 유지했다.

## 독립 감사에서 발견한 보강점

### 1. DART 호출 상한 계산이 선언된 endpoint 수와 불일치

`collector_interface.py` 주석은 상세 endpoint 7개를 열거한다.

- piicDecsn
- fricDecsn
- pifricDecsn
- crDecsn
- cmpMgDecsn
- cmpDvDecsn
- cmpDvmgDecsn

그러나 계산식은 종목당 `list 1 + 상세 6`으로 계산한다. 33종목을 전부 훑으면 인증/코드 1회를 포함해:

- 보고값: `1 + 33 × (1 + 6) = 232`
- 선언 endpoint 전수값: `1 + 33 × (1 + 7) = 265`

따라서 현재 `within_caps=true`는 DART cap 250을 보장하지 않는다. 실제 호출 전에 목록 조회 → 관련 사건이 있는 코드/endpoint만 상세 조회하는 단계형 예산과 fail-closed 검사가 필요하다.

### 2. 정정공시 resolver가 미래 정정본을 과거 재생에 사용할 수 있음

`resolve_ca(records)`는 모든 정정 레코드를 접수번호 순으로 정렬한 뒤 가장 최신본을 고른다. 재생일 또는 의사결정 cutoff의 `available_at`으로 버전을 자르지 않는다. 그러므로 효력일 뒤에 제출된 정정본이 과거 효력일 원장에 소급 적용될 수 있다.

### 3. `same_day_pit`가 계산만 되고 재생에서 집행되지 않음

`same_day_pit = bool(available_time)`은 시각 존재 여부만 본다. 실제 의사결정 cutoff보다 빠른지 비교하지 않으며 `replay()`는 이 값을 기업행동 적용 조건으로 사용하지 않는다. null 시각은 당일 사용 금지, 시각 존재 시 cutoff 비교가 필요하다.

### 4. STALE MTM이 NAV 유효성 게이트를 막지 않음

원주가가 없을 때 이전 가격 또는 0으로 NAV를 계속 만들고 `UNKNOWN_MTM_STALE`만 남긴다. 진단용 연속 시계열은 가능하지만, 성과 계산에 들어갈 수 없도록 일별 `nav_valid=false`와 전체 performance gate가 필요하다.

### 5. 실제 재생의 주문 의도 변환은 아직 미고정

REPORT도 매수는 수정수량×수정종가의 목표 금액, 매도는 보유 대비 비율을 다음 TASK에서 고정한다고 명시한다. 같은 날 다중 체결, 기업행동 전후, 0보유, 반올림 규칙까지 확정되지 않아 148건 재생 입력이 아직 결정적이지 않다.

### 6. PR #85 입력 head 차이는 receipt-only 변경

Claude가 읽은 PR #85 head는 `467e3237...`이고 현재 head는 `68823bff...`이다. 두 커밋 비교 결과 변경 파일은 delivery acknowledgement용 `receipt.json` 하나뿐(8줄 변경)이며 REVIEW/TASK는 동일하다. 연구 입력 오염은 아니지만 검토 이력에는 두 SHA를 모두 남긴다.

## 판단

PR #86은 **계약 초안과 합성 어댑터 준비 완료**라는 제한된 READY로 수용한다. 실제 공식 자료 수집, 148건 재생, +19.90% 수정, PAPER_VALIDATION_READY 판정으로 확대 해석하지 않는다.

자격 부재를 이미 확인했으므로 같은 API 실행을 반복하지 않는다. 다음 단계는 기존 코드와 합성 fixture만으로 위 계약 결함을 보강하는 한 단계다.
