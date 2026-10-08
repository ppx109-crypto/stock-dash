# TASK — PATH-ENSEMBLE-0001

- task_id: PATH-ENSEMBLE-0001
- chain_id: MAX-RETURN-20261008
- round: 8
- status: READY
- source_pr: 58
- source_head_sha: `95f2219205a78cc2b77db0ebb8c370866af8dae7`
- 목적: 매수순서 운을 한 경로 선택으로 숨기지 않고, 기존 4개 고정 경로를 동일 자본으로 묶은 재현 가능한 후보를 최종 고정할지 판정

## 입력과 계산

PR #55 head `b4166452e95778dd892fce3a793aea652401492a`의 아래 8개 비용2배 NAV만 쓴다.
- B: `nav_B_x2_s{0,1,2,3}.csv`
- R: `nav_R_x2_s{0,1,2,3}.csv`

정확히 2개만 계산한다.
1. B4_EQUAL
2. R4_EQUAL

각 seed는 독립 소계정이며 최초 1천만원 NAV의 25%, 즉 250만원씩이다. 날짜별 합계 NAV와 invested는 각 CSV 값의 0.25배를 합한다. 소계정 사이 자금 이전·리밸런싱·상계는 없다. 원 엔진·체결을 다시 돌리지 않는다.

## 완료조건

- 원본 8개 파일 해시와 날짜행 동일성을 먼저 확인.
- 합계 NAV/투자금 CSV 2개와 소계정별 일일 기여표를 제출.
- 끝 금액, CAGR, MDD, 최악 하루/날짜, 하루 -15% 위반, 최악 달, 평균 투자비율, terminal sleeve share를 보고.
- GPT PREREG 숫자와 0.01원 및 1e-8% 이내 일치 여부를 표로 제시.
- 같은 입력을 역순으로 합산해 0.01원 이내 동일해야 함.
- R4_EQUAL이 B4_EQUAL보다 끝 금액이 낮지 않고 하루 -15% 위반 0이며 최대 terminal sleeve share < 30%이면 `SHADOW_SPEC_READY`; 아니면 `NO_CANDIDATE`.
- `SHADOW_SPEC_READY`면 R4_EQUAL의 연구용 shadow 계약만 작성: 4개 25% 소계정, seed 0~3 고정, R30 고정, 비용2배, 최초 lock 뒤 새 날짜만 별도 측정. 현재 봇에 적용하지 않는다.
- R4의 수익 우위가 약 0.03%뿐임을 ‘새 알파’로 표현하지 않는다. 선택 근거는 경로 평균화와 하루 손실 개선이다.
- 과거 구간은 OOS가 아니며 PAPER_VALIDATION_READY나 실전 승인으로 선언하지 않는다.

## 금지

새 seed·가중치·threshold·grid·신호·필터·백테스트, RL 재시도, D 재시도, API/수집/주문, 운영 봇·전략·배분·워크플로·인증 변경, 레버리지, 자동병합, 비밀 공개 금지. 이 2판 뒤 과거 창 최적화는 종료한다.

결과 PR을 열기 전 REPORT/manifest/receipt/evidence를 완성하고, 제출 뒤 receipt 보정 외에는 결과 브랜치를 바꾸지 않는다.