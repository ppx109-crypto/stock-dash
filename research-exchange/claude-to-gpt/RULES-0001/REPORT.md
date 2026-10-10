# REPORT — RULES-0001 기존 자동매매 규칙과 실측 계약 고정

- task_id: RULES-0001 / chain_id: RULES-20261008 / round: 1(최대 3)
- **status: READY — 계약 감사 완료라는 뜻이며 실전 검증 · 실전 승인이 아님**
- 입력(이번 전달 PR): **#8 · head `a5b653b8abcfaf9a09f247b1f70682e6e2fa7d6e`** — GitHub API로 open · non-draft · 파일 4개 확인 뒤 그 SHA의 TASK.md · RULE-CONTRACT-DRAFT.md · REVIEW.md · receipt.json을 읽음(제출 직전 head 다시 확인).
- 코드 기준점: `00b98ab1655c84806357f44f2de6f1509ef1447f`(TASK의 code_baseline) — 운영 작업 폴더와 따로 꺼낸 폴더에서 읽음(운영 폴더 checkout/reset/stash 없음).
- 실행 환경: 기존 Claude 작업 세션 · 리눅스 · Python 3.11(jsonschema 4.26 있음) · 시험은 네트워크(socket) 막고 키 환경변수 지우고 임시 폴더에서.

## 1. 수행 / 미수행
**수행**
1. 1D · 15m · 1H · 엔진/인버스 · 바구니 C · 돈 나누기 · F5의 규칙을 기준 커밋 코드에서 뽑음 — 네 갈래를 하위 에이전트가 읽기 전용으로 추출하고, 핵심 줄(✔)은 본 세션이 코드에서 직접 다시 확인 → `RULES-LOCK.md`(본문) + 부록 3개.
2. GPT 초안(RULE-CONTRACT-DRAFT.md)을 줄마다 코드와 대조 → `RULES-LOCK.md §7`.
3. 자료 사용 가능 시각 · KRX/NXT · 수급 확정 · DART 시각 · Universe(t) 결손 · KIS/DART API 매핑(코드 기준) → `DATA-AVAILABILITY.md` + 부록.
4. 실측 계약 문서 · JSON schema → `MEASUREMENT-CONTRACT.md` · `measurement.schema.json`(비활성 · 목적지 미정).
5. 오프라인 시험 2묶음 → `test-result.json`
   - 계약(순수 함수 `fixtures/contract.py`) 43건: 사용 가능 시각 · 정정판 · 미래봉 · 체결 가정 시각 · DART 날짜만 · 미체결 · 부분체결 · 과체결/과매도 오류 · 같은 봉 익절/손절 · 갭 · 칸 · 수량 · 20일 겹침 · NAV(결제 중복) · TWR(입출금) · 달력월 · MDD · 손실 문(−15% 경계 포함) · 귀속 · schema 4 · 네트워크 차단.
   - as-is(운영 순수 함수를 합성 입력으로) 81건: 바구니 step/todays_events 18 · 공시 갈래 kind_of 8(파일에서 두 정의만 떼어 실행 — 공급자 모듈 import 안 함) · 15분봉 · 1시간봉 청산/stale/EMA 35 · 1일봉 size_of/exit_decision 20.
**미수행(금지 · 범위 밖)**: 성과 백테스트 · 문턱/보유기간 탐색 · 실측 계좌 수집 · 모의/실주문 API 호출 · 운영 코드 · 설정 · 배분 · 봇 · 인증 · 스케줄 변경 · 새 Routine/감시 · 병합 · KIS/DART 호출 · 키 열람 · 공식 문서 대조(저장소에 명세 없음 · 웹 미사용).

## 2. 결과 — 주장 / 소스 확인 / 실행 검증 / 미확인
| 항목 | 종류 | 결과 |
|---|---|---|
| 1H는 실주문 몫 0 · PAPER_TRADING off · 실행 숫자는 90회차(94는 같은 숫자 · 코드 갈래 없음) | 소스 확인 | 운영 전략으로 셈하지 않음 |
| F5 운영 코드 없음 | 소스 확인 | 자동매매 규칙 없음 |
| 초안과 다른 곳: 1D 변동성 문턱(전 기간 40% 자리 · 전날 값) · 기울기 **EMA180**(SMA 아님) · 간격 **< 53**(≤ 아님) · 3칸 나이(EMA 4선 · 0 → 999) · 15:28 한 번만 검사 · 15m stale은 '자리 비키기' 조건 · 바구니 '계좌 중복'은 바구니만 피함 | 소스 확인(✔ 줄 재확인) | RULES-LOCK §7 |
| **경계 부동소수점 결함**: 1D · 15m · 1H 청산에서 정확한 +13% · −10% · +1%(호가상 가능 · 예 1,000 → 1,130 · 900 · 1,010원)가 규칙 글과 다르게 처리됨 | **실행 검증**(as-is 9건 실패로 고정) | *-FLOAT-PROPOSED(제안만) · 연구 코드도 같은지 · 성적 영향은 미측정 |
| 1D 정배열일수 0 → 3칸 불가 | 실행 검증 | 의도 미확인 |
| 바구니: 못 산 자사주 사건도 20거래일 겹침을 막음 · 정확히 −2%는 안 삼 · 정정 · 거래정지 · 신탁 · 유무상 공시도 같은 갈래 | 실행 검증 | BASKET-C-TITLE-PROPOSED |
| **수급이 연구보다 하루 늦게 쓰임**: 1D 15:20 판단은 T−6 ~ T−2(연구 T−5 ~ T−1) · 1H/15m 후보도 하루 늦음 | 소스 확인 + 저장소 자료 마지막 날(price 20261007 · investor 20261006) | 미래 참조는 아님 · 연구 성적이 운영과 다를 까닭 · 영향 크기 미측정 |
| 접수 = 장부 반영(모든 봇) · 체결 조회 없음 · 15:32 값은 체결 증거 아님 | 소스 확인 | 실측 계약에서 접수/체결 분리 |
| 같은 OHLC 봉 익절/손절 동시 | 소스 확인 + 실행 검증 | 운영은 종가로만 판단해 생기지 않음 · 계약은 보수적(손절 · ambiguous) |
| 측정 계약 함수 · schema | 실행 검증(43/43) | 합성 자료만 |
| KIS · DART API 매핑 | 소스 확인 | **공식 문서 미확인**(저장소에 명세 없음) |
| 15:20 현재가가 직전 체결가인지 예상 체결가인지 · 15:32 값 = 공식 종가인지 · 모의 체결가 · 수급 칸 NXT 섞임 · 09-22 6종목 교정 까닭 | — | **미확인** |
| 상장폐지 포함 Universe · 과거 공시 시각 · 컨센서스 | — | **추가 출처 필요**(KIS · DART에 없음) |

## 3. 꼭 적어 둘 한계(지시대로 명시)
- **20거래일 기록은 로그 품질 · 대사 점검이지 알파 합격이 아님.** ALLOC-1 그림자는 60거래일 **AND** 중복 30건이 pilot 최소량일 뿐.
- **DART 날짜만으로 다음 날 진입해도 당일 가격 반응의 시점 문제는 풀리지 않음** — 공시 뒤 반응인지 확인하려면 접수 시각이 필요.
- 이 문서의 어떤 숫자도 새 성과 재현이 아님(성과 백테스트 안 함). 기존 문서 성과는 출처가 보고한 시뮬레이션 값.
- 실제 체결 · 일별 계좌 NAV 증거가 없어 **실전 추천 불가**. 기존 전략을 이름만 보고 폐기하지 않음.
- 하위 에이전트 추출은 ✔ 줄만 본 세션이 재확인 — 부록의 나머지 줄 번호는 추출 그대로(다음 검토에서 무작위 표본 대조 권함).

## 4. 명령(다시 돌리기)
```
# 기준점 꺼내기(운영 폴더와 따로)
git worktree add --detach <폴더> 00b98ab1655c84806357f44f2de6f1509ef1447f
cd research-exchange/claude-to-gpt/RULES-0001/fixtures
python3 -I run_fixtures.py tr-contract.json          # 계약 43건
python3 -I run_asis.py <폴더> tr-asis.json            # as-is 81건(네트워크 차단 · 임시 폴더)
python3 -I merge_results.py tr-contract.json tr-asis.json ../test-result.json
```

## 5. 파일
`REPORT.md` · `RULES-LOCK.md`(+ `RULES-LOCK-1D.md` · `RULES-LOCK-M15-1H.md` · `RULES-LOCK-ENGINE-BASKET.md`) · `DATA-AVAILABILITY.md`(+ `DATA-AVAILABILITY-DETAIL.md`) · `MEASUREMENT-CONTRACT.md` · `measurement.schema.json` · `fixtures/{contract,run_fixtures,run_asis,merge_results}.py` · `test-result.json` · `manifest.json` · 입력 receipt `research-exchange/state/receipts/8-a5b653b8abcfaf9a09f247b1f70682e6e2fa7d6e.json`.

## 6. 질문 · 다음 한 단계 후보(GPT · 사용자 결정)
1. 수급 하루 늦음: 운영 수집을 '그날 저녁 그날 줄까지'로 바꿀지(운영 변경 · 사용자 승인) 또는 연구를 '이틀 전까지'로 맞춰 다시 잴지(성과 재검증 단계).
2. 경계 부동소수점: 연구 코드에도 같은 식이 있는지 확인하고 영향 크기를 잴지.
3. 실측(MEAS) 비공개 목적지 결정 — 정해지기 전엔 수집 안 함.

다음 방향: GPT 검토 뒤 '실측 · 유니버스 · 성과 재검증' 가운데 한 단계만 다시 정함(이번 결과로 ALLOC/ALPHA/MEAS 실수집을 시작하지 않음).
