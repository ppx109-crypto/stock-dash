# REPLAY-SPLIT-RATIO-DIRECTION-CONTRACT-0001 — 클로드 사전등록(계산 · 코드 검색 · 판정 전)

- 지시: GPT PR #101 head `d0313d20`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `b44de5d3a3dc22c1`
  - SOURCE_PACKET `39d9e0652c3ba772`
  - PREREG `46b12c95837a8aca`
  - REVIEW `510c7750b5145150`
  - receipt `4ee9ed636a06f969`
- 입력 PR #100: 시작 직전(02:04 KST) 확인 결과 열림 · 초안 아님 · head `c16010b1ede2185814b1639cbb46cb2536a26e8f` 일치. 제출 직전에 다시 확인합니다.
- **오프라인만**: 외부 URL · 네트워크 · API · 키 · 수집 · 캐시 0. 실제 종목 · 원시 공시 · 계좌자료 열람 0. 리플레이 · 백테스트 · 성과 · NAV 0
- **제외**: 적용일 · 거래재개일 · 최초 매도가능일 · KOSDAQ · 제2256호 결속 · 단주 처리 규칙 추정

## 고정 계약(GPT PREREG 수식 그대로)
- 입력 q0 · q1(전/후 발행주식총수), f0 · f1(전/후 1주당 가액)은 정수 또는 유리수로 받습니다. Python `fractions.Fraction`으로 **정확히** 비교하고, 허용 오차는 두지 않습니다.
- 수식
  - `m_qty = q1/q0`
  - `m_face = f0/f1`
  - 검증 조건: `m_qty == m_face`
  - `m_price = 1/m_qty = q0/q1 = f1/f0`
- **UNKNOWN(fail-closed) 사유를 미리 고정합니다:**
  - 누락
  - 0
  - 음수
  - 비유한(NaN · inf)
  - 부동소수 입력(단위 · 반올림 불명)
  - `m_qty ≠ m_face`
  - `m_qty == 1`
  - 사건명과 방향 모순(split인데 m_qty < 1, reverse_split인데 m_qty > 1)
- **Truth table**
  - split: `m_qty > 1` 이고 `0 < m_price < 1`
  - reverse_split: `0 < m_qty < 1` 이고 `m_price > 1`
  - 모순이면 값을 뒤집어 맞추지 않습니다.
- **보유 전환**
  - `qty_after = qty_before × m_qty`, `price_after = price_before × m_price`
  - 단주 · 비용 · 현금보상 전에는 `qty × price`가 보존됨을 Fraction 등식으로 증명합니다.
  - `qty_after`가 정수가 아니면 `UNKNOWN_CASH_IN_LIEU`로 두고, 회계 · NAV에 적용하지 않습니다.
- **적용일 미확정:** price_basis_date가 BLOCKED이므로 계약이 READY여도 **어느 사건에도 적용하지 않습니다**.

## 합성 검산(실제 종목 아님)
- 분할 2건 · 병합 2건 · 실패 사례를 둡니다.
- 실패 사례에는 '병합 뒤 발행주식총수가 단주 처리로 1주 어긋난 경우'를 포함합니다. 정확 비교 규칙이 이런 경우를 UNKNOWN으로 막는다는 것(그리고 그 대가)을 보이기 위해서입니다.
- 각 사례의 기대값은 코드에 먼저 적고, 실제값과 pass를 공개합니다.

## 기존 코드 · 문서 방향 감사(읽기 전용)
- 이 저장소 작업 트리(origin/main)와 제 이전 결과 PR 브랜치 연구 복사본(PR #86 · #88 · #92 · #94)에서 비율을 가격에 곱하거나 수량에 곱하는 표현을 찾습니다.
- 검색어: `ratio` · `분할` · `병합` · `prtt` · `split` 계열
- 경로 · 줄 · 문구와 방향 판정(수량 배율로 씀 / 가격에 곱함 / 무관)만 보고합니다. 코드는 고치지 않습니다.
- 운영 코드에서 가격 × 주식수 배율이 발견되면 그 사실과 경로만 적고, 수정 범위가 이번 TASK 밖이면 BLOCKED 사유로 적습니다.

## 상태
- 위 계약 · truth table · 합성 검산 · 가치 보존 · fail-closed가 모순 없이 재현되고, 기존 코드에 반대 방향이 없거나 범위가 분명하면 READY입니다.
- 아니면 BLOCKED이고 NEEDS_DATA를 한 줄로 적습니다.
- READY는 회계 계약 준비일 뿐입니다. 8개 기업행동 후보 UNKNOWN · +19.90% · NAV · PAPER_VALIDATION_READY는 그대로 둡니다.

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `evidence/ratio-direction-contract.json` · `evidence/code-direction-audit.json` · `evidence/run.log`
- `code/ratio_contract.py`
