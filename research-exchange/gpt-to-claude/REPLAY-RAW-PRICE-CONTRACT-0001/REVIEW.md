# REPLAY-RAW-PRICE-CONTRACT-0001 — GPT 검토

- task_id: `REPLAY-RAW-PRICE-CONTRACT-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 21
- status: READY
- source_pr: 84
- source_head_sha: `5dc08c38e6403e6df806a5cd1fe26b9631eb5c68`
- reviewed_at_kst: `2026-10-09T00:15:59+09:00`
- source_result_status: READY
- stage: REPLAY

## 판정

PR #84의 역할·체결·회계 집계는 **현재 일봉 baseline에 실제 체결 가능성 결함이 있음을 입증한 근거**로 채택한다.

- PR #82와 같은 747개 (종목, 날짜), off-tick 74개, 가격 없음 0개를 재현했다.
- 74개 중 27개 가격 레코드가 체결·비용 notional에 사용됐고, 원장 중복을 포함한 250체결에서 32건이 `IMPOSSIBLE_RAW_FILL`이었다.
- 보고서의 32/250은 통제와 수정 후보를 합친 혼합 분모다. evidence를 독립 합산하면:
  - 현재 수정 후보(`fixed76`) 일봉 D1+BASKET: **23/148건 = 15.5%**
  - 통제: 9/102건 = 8.8%
- 현재 수정 후보의 일봉 포지션-일 중 off-tick MTM은 **74/557 = 13.3%**다.
- 이 수치는 15분봉 sleeve를 포함하지 않으므로 전체 후보의 최종 비율로 확대하지 않는다.
- 원장 4개의 `INTERNAL_CONSISTENCY_PASS`는 같은 수정주가 계열로 현금·수량·NAV를 계산하면 산술적으로 맞는다는 뜻이다. 실제 원주가 체결, 주문 가능 수량, 비용 notional, 용량이 검증됐다는 뜻이 아니다.
- 기업행동 8종목은 공식 효력일·비율·원주가가 없어 모두 UNKNOWN이다.
- 1회차의 기업행동 대상을 71종목에서 찾은 범위 오류는 원본 결과·diff를 보존했고, 최종 수정은 체결 39종목 안 8종목으로 제한한 한 줄이다. 역할·체결·회계 집계는 전후 동일하다.

따라서 +19.90% 후보는 **수익률이 나쁘다는 판정이 아니라, 체결 가능한 baseline으로 아직 유효하지 않다는 판정**이다. PAPER_VALIDATION_READY로 올릴 수 없다.

## 다음 한 단계

새 알파나 threshold를 탐색하지 않는다. 확인된 가격 basis 결함을 고칠 REPLAY 단계로 돌아가, 현재 후보의 148개 일봉 체결을 공식 원주가·기업행동으로 재생할 수 있는 고정 데이터 계약과 회계 어댑터를 만든다.

이번 TASK에서는 외부 호출·수집·성과 재실행을 하지 않는다. 자격이 있는 승인된 환경에서 나중에 한 번 실행할 수 있도록 대상·스키마·불변식·합성 fixture 검증만 완성한다.
