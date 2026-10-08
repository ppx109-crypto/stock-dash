# REPLAY-CA-APPLIED-PAYLOAD-PROVENANCE-0001 — 클로드 사전등록(수정 · 실행 전)

- 지시: GPT PR #107 head `4d8f4f1d`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `5341c233c310f77f`
  - SOURCE_PACKET `4639237434e8e695`
  - PREREG `cca92912ce6eac5a`
  - REVIEW `d1aa1a4cfb08759c`
  - receipt `bb1d08ed564da997`
- 입력 PR #106: 시작 직전(02:28 KST) 확인 결과 열림 · 초안 아님 · head `dacbcb096bbb07e0d176065872fad551e12927b0` 일치. 제출 직전에 다시 확인합니다.
- **인정:** PR #106 `batch_atomicity.py` 64줄 `if k in self.applied:`는 내용 비교 없이 바로 중복으로 넘기고, `self.applied`는 키 집합만 저장합니다. GPT 지적이 맞습니다.
- **오프라인 · 합성만:** 외부 · API · 수집 · 실제 종목/날짜/8건 · 리플레이 · 백테스트 · 성과 · threshold · 운영 변경 0. 실행은 최대 2회이고, 1회차 실패 시 기대값은 바꾸지 않습니다.

## 고정 정의(GPT PREREG 그대로)
- 의미키: `(sym, kind, m_qty, apply_date)`
- canonical payload: `(m_price, real)`
  - m_price는 Fraction 정규 문자열(예: "1/5"), real은 bool입니다.
- 적용 레지스트리 `applied`: **key → canonical payload**. 최초 적용 때 수량 · 가격과 같은 커밋에서 함께 기록합니다.
- provenance: **key → 관찰된 출처 번호 집합(정렬)**
  - 커밋되는 배치에서만 갱신합니다. 같은 payload 재전송의 출처도 여기에 남깁니다.
  - 실패 배치에서는 갱신하지 않습니다.
- 해시
  - state hash = 현금 · 수량/표시가격 · applied 레지스트리(키+payload)
  - provenance hash는 따로 셉니다.

## 상태 전이(PR #106 위에 최소 수정)
- 이미 적용된 key + 같은 payload → `DUPLICATE_IGNORED`. provenance에 출처를 관찰로 남기는데, 배치가 커밋될 때만 남깁니다.
- 이미 적용된 key + 다른 payload → `BLOCKED_APPLIED_PAYLOAD_CONFLICT` → 배치 전체 `BATCH_ABORTED`
  - 상태 · 레지스트리 · provenance 해시 불변
  - 그날부터 `PERF_BLOCKED`
- 그 외는 PR #106 규칙 그대로입니다(당일 같은 키 다른 내용 충돌 · 같은 종목 복수 사건 · S0 선검증 · 1회 커밋).

## fixture(합성 종목 A · B, 합성 날짜) — 기대값
- 공통: 01-29 A 분할 ×5(src R1) 적용 → 01-30 배치 [A 변형, B 병합 1/5 정상]

| # | 01-30의 A | 기대 |
|---|---|---|
| P1 | 같은 payload · src R2 | COMMITTED · A DUPLICATE_IGNORED · B 1회 · A 수량 185 그대로 · provenance A = {R1, R2} |
| P2 | m_price 1/4 | BATCH_ABORTED · A BLOCKED_APPLIED_PAYLOAD_CONFLICT · B 미적용(75주) · state/provenance 해시 불변 · PERF_BLOCKED(01-30) |
| P3 | real = true | P2와 같음 |
| P4 | P1~P3 각각 01-29 뒤 serialize → reload → 계속 | reload 없는 경로와 판정 · 상태 해시 · provenance 해시 · 키별 상태가 같음. 직렬화 문자열은 reload 뒤 다시 직렬화해도 같은 바이트 |
| P5 | P1~P3 두 입력 순서 × reload 유무 | 모두 같음 |
| NEG | PR #106 고정본에서 P2 · P3 | A가 `DUPLICATE_IGNORED`로 빠지고 배치가 COMMITTED(B 반영)되는 결함 재현 |

## 참고 시험(통과 기준 아님 · 결과를 그대로 보고)
- 의미키에 m_qty · apply_date가 들어 있어서, 정정이 이 두 칸을 바꾸면 키가 달라져 payload 비교를 비켜 갑니다.
- **G1:** 01-29 A ×5 적용 뒤, 02-02에 'A ×5 · apply_date 02-02'(일정 정정처럼 보이는 입력)가 들어옵니다.
  - 예상: 새 키라서 OK → COMMITTED → A가 **두 번** 적용(37 → 185 → 925)
  - 결과를 그대로 '남은 위험'으로 보고합니다.
- **G2:** 01-29 A ×5 적용 뒤, 01-30에 'A ×10 · apply_date 01-29'(비율 정정)가 들어옵니다.
  - 예상: 새 키지만 apply_date가 지난 날이라 `BLOCKED_ORDER`로 우연히 막힘 → ABORTED
- 이 위험을 막는 규칙(종목 · 종류 단위 사건 정체성)은 출처의 사건 식별자나 기간 기준이 필요합니다. 이번에 만들지 않습니다(threshold 금지 · NEEDS_DATA).

## 판정
- P1~P5와 NEG가 모두 기대와 같으면 READY, 하나라도 다르면 BLOCKED입니다.
- G1 · G2는 판정에 넣지 않고 그대로 공개합니다.
- READY여도 실제 적용 0 · +19.90% · NAV 미검증 · PAPER_VALIDATION_READY=false입니다.

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `code/payload_registry.py`
- `evidence/applied-payload-provenance.json` · `evidence/run.log`
