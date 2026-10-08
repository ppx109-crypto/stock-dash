# REAL-SLEEVE-0001 · 클로드 실행 계획(계산 전 고정)

- 따름: GPT PR #61 head `efcca99fc0496da74f5d0251593ae5e395347de9`의 TASK · REVIEW · PREREG · manifest · receipt.
  - 정확히 8판(B/R × seed 0~3 · 비용 2배 · 250만 원)입니다. 판정 기준은 바꾸지 않습니다.
- 고정 입력: PR #55 head `b4166452`의 코드(`code/orig/`에 그대로 복사, sha256: `fr_m15.py` 0c6582b4… · `m15_exec.py` a49f4965… · `kernel2.py` a1b08028… · `cost_contract.py` c8c006c1… · `common.py` 2f6e61a7…).
  - 그 밖에 엔진 00b98ab1 · b3 · hourly_tables 8dab7750… · D1 picks d02fec2e…를 씁니다.

## 코드 변경(이것만)
1. **자본 한 줄:** `common.py` 4줄 `CASH = 1e7` → `CASH = 2.5e6`.
   - 계좌 시작 현금과 성적표 기준이 모두 이 값을 씁니다.
2. **보고용 기록(판단 · 체결과 무관):** `fr_m15.py`의 `run` 안에서, 날마다 장 마감 NAV를 적는 바로 그 자리에 종목별 평가금액(수량 × 마지막 종가)을 함께 남깁니다.
   - 실행 묶음(맨 아래 20판 부분)은 이 과제의 8판 묶음으로 바꿉니다.
   - `code/rs_m15.py`와 원본의 diff를 `evidence/code.diff`에 남깁니다.
- 신호 · 선정 · 체결 · 비용 · R30 · seed 난수 흐름은 바꾸지 않습니다.

## 합산 · 판정
- B4_ACTUAL · R4_ACTUAL: 같은 날짜에서 4개 소계정의 NAV · 투자금 · 종목별 평가금액을 그대로 더합니다(축소 없음). 날짜행이 다르면 멈춥니다.
- 기준 자본은 1천만 원(250만 × 4)입니다. CAGR · MDD · 최악 하루 · 달은 PR #60 `pe_sum.py`와 같은 식으로 셉니다.
- 일별 최대 단일 종목 비중 = (그 종목 네 소계정 평가금액 합) ÷ 합계 NAV, 날마다 최대값입니다.
- PR #60 근사와 비교합니다(`ens_{B4,R4}_EQUAL.csv`, PR #60 `24b12632`): 끝 금액 차이 · 최대/평균 절대 NAV 차이.
- 판정: 8판 · 보존 불변식 통과, R4 끝 ≥ B4 끝, R4 하루 −15% 넘음 0, R4 달 −15% 넘음 0, R4 최대 단일 종목 비중 < 30%이면 `IMPLEMENTATION_READY`, 아니면 `NO_CANDIDATE`입니다.
