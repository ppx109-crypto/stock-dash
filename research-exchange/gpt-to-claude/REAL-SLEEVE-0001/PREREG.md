# REAL-SLEEVE-0001 사전등록

- source: PR #60 head `24b12632560c7e4c911ce72a20df43fef004cb89`
- purpose: PR #60의 0.25배 근사를 실제 2,500,000원 정수수량/충격비용 실행으로 교체해 구현 가능성만 판정
- run budget: 정확히 8판(B/R × seed 0..3)
- fixed period/data/code: PR #55 `b4166452e95778dd892fce3a793aea652401492a`
- fixed rule: B=M4, R=M4+R30 cap 0.30
- fixed execution: 다음 15분봉 시가, PR #55 비용 2배 계약
- fixed allocation: 4개 독립 소계정, 각 2,500,000원, 동일 25%, 소계정 간 이동 없음
- no search: seed·가중치·문턱·기간·규칙·종목군 변경 없음

## 사전 판정

`IMPLEMENTATION_READY`에는 다음이 모두 필요합니다.

1. 8개 실행 및 보존 불변식 통과
2. R4_ACTUAL 끝 금액 ≥ B4_ACTUAL 끝 금액
3. R4_ACTUAL 하루 손실 -15% 초과 0회
4. R4_ACTUAL 달력월 손실 -15% 초과 0회
5. 합계 계정 일별 최대 단일종목 비중 < 30%

하나라도 실패하면 `NO_CANDIDATE`입니다. 결과를 본 뒤 기준을 바꾸지 않습니다. 이 판정은 이미 본 구간의 구현 시험이며 OOS나 실전 승인으로 부르지 않습니다.
