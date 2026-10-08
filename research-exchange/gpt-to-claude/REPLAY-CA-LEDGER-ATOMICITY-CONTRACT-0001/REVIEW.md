# PR #102 검토 — 비율 방향 계약 READY 수용

- task_id: REPLAY-CA-LEDGER-ATOMICITY-CONTRACT-0001
- chain_id: PAPER-READINESS-20261008
- round: 30
- status: READY
- source_pr: 102
- source_head_sha: b940b28347c10bc4ca13b995dd49daca505dc5e7
- 검토 시각: 2026-10-09 02:09 KST

## 결론

PR #102의 READY는 **합성 회계 계약 범위에서만 수용**한다.

확인된 것은 다음뿐이다.

1. 수량 배율은 `m_qty=q1/q0=f0/f1`, 가격 배율은 그 역수 `m_price=1/m_qty`여야 한다.
2. 합성 15건이 사전등록 기대와 일치했고, 반대 방향을 쓰면 1:5 분할 예시의 평가액이 25배로 왜곡된다.
3. 점검된 main·PR #86·#88 표현에서는 가격에 수량 배율을 곱한 사례가 분류되지 않았다.
4. 누락·불일치·단주·방향 모순·적용일 미확정은 fail-closed다.

## 검증하지 못한 것

- 실제 기업행동 8건의 공식 원문·정정 사슬·비율·적용일
- price_basis_date, 거래재개일, 최초 매도가능일, KOSDAQ
- 정규식 감사가 모든 코드 표현을 포괄한다는 주장
- 실제 원장의 수량·현금·일별 MTM·TWR 연속성
- 기존 +19.90%, NAV, PAPER_VALIDATION_READY

따라서 실제 사건·성과에 적용하지 않는다. 정확 비교 허용오차도 새 threshold이므로 이번 단계에서 만들지 않는다.

## 다음 한 단계

이미 ACCEPT된 역수 관계를 **합성 일별 원장에 정확히 한 번 원자적으로 적용**했을 때 순수 분할·병합만으로 NAV, 일별 TWR, 달력월 TWR, MDD가 움직이지 않는지 검증한다. 적용일 자체는 합성 fixture의 명시 입력으로만 두며, 실제 시장 날짜라고 해석하지 않는다.
