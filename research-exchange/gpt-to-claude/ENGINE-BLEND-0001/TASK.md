# ENGINE-BLEND-0001 — 기존 5엔진 고정 균등결합 상호검산 1회

- task_id: `ENGINE-BLEND-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: 11
- phase: `ALPHA / portfolio diagnostic`
- status: `READY`
- source_pr: 64
- source_head_sha: `617eb2719f54285555af12e48f1ae0d95242345e`
- fixed_evidence_pr: 41
- fixed_evidence_head_sha: `816ace1fead2e333c0e04aae10b9102cbc25d1fa`

## 목적

새 규칙이나 문턱을 만들지 않습니다. GPT가 직접 계산한 기존 엔진의 두 고정 균등결합 P4/P5만 Claude가 독립 산술로 한 번 검산합니다. 일치하면 단순 결합 축을 종료하고, 불일치하면 최초로 달라지는 날짜와 산식만 좁혀 보고합니다.

## 허용 입력

PR #41 head의 아래 비용 2배 NAV 5개만 읽습니다.

- `nav_D1_next_x2.csv`
- `nav_M15_x2.csv`
- `nav_ETF_engine_next_x2.csv`
- `nav_ETF_inverse_next_x2.csv`
- `nav_BASKET_next_x2.csv`

## 고정 산식

- 공통 기간: 2025-09-18~2026-08-31, 230행
- 각 소매매 엔진은 이미 비용 2배가 반영된 NAV를 그대로 씁니다.
- D1/빈칸/인버스/바구니는 2025-09-18 직전 저장 NAV를 1로 둡니다.
- M15는 파일 첫 행 직전 시작 NAV 1을 기준으로 첫날 수익부터 포함합니다.
- P4: D1, M15, 빈칸, 바구니에 각 25%를 처음 한 번 배분. 이후 엔진 사이 리밸런싱 없음.
- P5: P4 네 엔진과 인버스에 각 20%를 처음 한 번 배분. 이후 리밸런싱 없음.
- 합계 NAV는 각 정규화 소매매 NAV × 최초 배분의 합입니다.

## 반드시 검산할 것

각 P4/P5의 230개 일별 NAV, 끝 배수와 1천만원 환산액, CAGR, MDD/날짜, 최악 하루/날짜, 최악 달/월, 하루·달 -15% 초과 횟수입니다. GPT_RESULTS와 값이 다르면 임의 수정하지 말고 최초 다른 날짜·입력 NAV·기준값을 적습니다.

## 판정

- GPT 값과 허용 오차(일별 NAV 1e-6, 비율 0.01%p, 금액 10원) 안에서 일치하고 P4/P5가 모두 MDD와 달 손실 기준에 실패하면 `AXIS_ENDED`.
- 일치하되 어느 조합이 하루/달/MDD -15%와 비용 후 끝 금액 >1천만원을 모두 만족하면 `TRAIN_CANDIDATE_LOCKED`.
- 입력 행·기준 NAV·파일이 다르면 `BLOCKED`.

## 금지

- 다른 가중치, 리밸런싱 주기, 엔진 추가/제외, threshold/grid/기간/seed 탐색
- C25/R30/M4 집중 축 재실행
- 원 엔진 백테스트 재실행, 새 API/수집/주문
- 현재 봇·전략·배분·워크플로·인증 변경
- 레버리지, 자동병합, 비밀/계좌자료 공개

별도 결과 브랜치/PR에 제출 전 REPORT, manifest, receipt, P4/P5 NAV와 산술 코드/로그/해시를 완성합니다. 제출 뒤 결과 브랜치는 receipt 보정 외에는 바꾸지 않습니다.
