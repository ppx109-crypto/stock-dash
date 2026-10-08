# COST-REPLAY-0001 결과 — 세금 교정과 고정 원장 비용차

- 지시: PR #30 head `5c8e30599107f967ddb5549cb0950c0e5fcc7f64` · source PR #29 head `d8024b5599a34a456e4ec99cdd2af6051ebb0904`
- 기준 저장소: `bcfeefbc27da6b9fb85f8536bb5d989b220ad8f4` · PREREG-LOCK 첫 커밋 `342ba6c3`(2026-10-08 11:11 KST, 계산 전)
- 전략 실험 0 · 신규 수집 · API · 주문 0 · 운영 파일 변경 0 · threshold 탐색 · RL 0
- status: **READY**(시험 PASS + 수익률 단위 원장 진단 완료). 금액 · NAV 지표는 **NEEDS_DATA**.
- `paper_validation_ready=false` · `live_approval=false`

## 1. 무엇을 했나
1. `research/perf2.py`의 비용 함수만 결과 폴더의 `cost_contract.py`로 옮겼습니다. 기존 파일 · import 경로는 그대로입니다.
2. 연도만 보던 세금(`TAX` + 그 밖의 해 0.0015 기본값)을 **날짜 · 상품 · 시장 계약**으로 바꿨습니다(`COST-CONTRACT.json`). 모르는 상품 · 시장 · 기간은 계산을 거부합니다(UnknownTax).
3. 기존 고정 연구 원장 1개로 old vs corrected를 한 번 비교했습니다. 매도 세금만 바꾸고 수수료 · 미끄러짐 · 충격은 가정값 그대로입니다.

## 2. 세금 계약(일반 주식 · 일반 시장매도, 매도금액 대비)
| 기간 | KOSDAQ(LOCKED) | KOSPI STRICT | KOSPI 가정 S_KOSPI_FARM015 | 기존 perf2 |
|---|---|---|---|---|
| 2017-01-01 ~ 2019-06-02 | 0.0030 | UNKNOWN | 0.0015 + 0.0015 | 0.0025 |
| 2019-06-03 ~ 2020-12-31 | 0.0025 | UNKNOWN | 0.0010 + 0.0015 | 0.0025 |
| 2021 ~ 2022 | 0.0023 | UNKNOWN | 0.0008 + 0.0015 | 0.0025 |
| 2023 | 0.0020 | UNKNOWN | 0.0005 + 0.0015 | 0.0020 |
| 2024 | 0.0018 | UNKNOWN | 0.0003 + 0.0015 | 0.0018 |
| 2025 | 0.0015 | UNKNOWN | 0 + 0.0015 | 0.0015 |
| 2026-01-01 ~ 2026-10-08 | 0.0020 | 0.0020 | 0.0020 | 0.0015 |
| 2026-10-09 ~ | UNKNOWN | UNKNOWN | UNKNOWN | 0.0015(자동) |

- KOSDAQ 표는 TASK 고정값(시행령 개정이유). KOSPI 2026 합계는 한국투자증권 현재 세금표 근거.
- 가정 시나리오의 농특세 0.0015는 **가정**이며 공식 사실이 아닙니다. 이 가정에서는 두 시장 합계가 기간마다 같아집니다.
- 매수 세금 0. ETF · ETN · 인버스 · 기타 상품은 이 표를 쓰지 않습니다(거부).
- BASE · STRESS · EXTREME 배율 1 · 1.5 · 2는 기존 계약 재현용이며, 세금에 곱하는 배율은 법정세율 변화가 아닌 **가상 스트레스**입니다.

## 3. 시험(합성 · 실측 아님)
| 시험 | 결과 |
|---|---|
| 날짜 경계(2019-06-02/03 · 해 바뀜 6곳 · 2026-10-08/09) | PASS |
| 매수 비과세 · 배율 | PASS |
| 부분체결(30+70 = 100주 · 해 넘긴 부분체결은 각 날 세율) | PASS |
| UNKNOWN 거부(KOSPI 과거 · KONEX · 시장 없음 · 날짜 형식 · 없는 시나리오) | PASS |
| 상품 구분(ETF · ETN · 인버스 · 기타 거부, 시나리오에서도) | PASS |
| 가정 시나리오 값 | PASS |
| old 재현 · 2026 차 = 매도금액 × 0.0005 | PASS |
- 결함 주입 5개(2026 코스닥 0.0015 · 경계 하루 밀림 · 매수 과세 · 모르는 기간 기본값 · ETF 허용)를 모두 잡음(`MUTATION-CHECK.json`).
- 복사 정확성: 연구 복사본 old 비용이 원본 `perf2.side_costs`와 495행 × 배율 3개에서 **최대 차 0.0**(원본은 읽기 전용 import).
- 재현: 두 번 돌린 `DELTA-ROWS.csv` sha256이 같음.

## 4. 고정 원장 진단(수익률 단위 · 가정 비용)
- 원장: RULES-0002 `a61f033` `results/d1_ledger_ASIS.csv` · sha256 `86c5f56d…209b` · 495행 · 136종목 · 진입 2017-01-26 ~ 2026-08-03 · 청산 2017-02-10 ~ 2026-09-04
- 출처: 연구 재생 결과(1일봉 규칙 · 씨앗 0). 모의 · 실계좌 장부 아님.
- 시장 분류(저장소 현재 목록 기준, 시점 기준 아님): KOSDAQ 34행 · KOSPI 추정 461행
- 단위: 행별 비용 뒤 손익(%), 계좌몫 합 = Σ(손익% × 칸/10). 계좌 1억 · 주문 = 계좌 × 칸/10 가정(RULES-0002와 같음).

### STRICT(계산 가능 86행 = KOSDAQ 34 + KOSPI 2026 52, UNKNOWN 409행)
| 배율 | 매매 평균 old → new | 평균 차(%p) | 계좌몫 합 old → new(차) | 매매 PF old → new | 부호 바뀐 매매 |
|---|---|---|---|---|---|
| BASE | 4.808 → 4.773 | −0.035 | 107.14 → 106.51(−0.63) | 2.121 → 2.108 | 0 |
| STRESS | 4.478 → 4.425 | −0.053 | 101.13 → 100.19(−0.94) | 1.997 → 1.979 | 0 |
| EXTREME | 4.148 → 4.077 | −0.070 | 95.14 → 93.89(−1.25) | 1.883 → 1.861 | 0 |

### S_KOSPI_FARM015(가정 · 전 495행)
| 배율 | 매매 평균 old → new | 평균 차(%p) | 계좌몫 합 old → new(차) | 매매 PF old → new | 부호 바뀐 매매 |
|---|---|---|---|---|---|
| BASE | 3.073 → 3.061 | −0.012 | 354.47 → 353.29(−1.18) | 2.076 → 2.070 | 0 |
| STRESS | 2.681 → 2.664 | −0.017 | 313.34 → 311.57(−1.77) | 1.873 → 1.865 | 0 |
| EXTREME | 2.290 → 2.267 | −0.023 | 272.30 → 269.94(−2.36) | 1.695 → 1.685 | 1 |

BASE 계좌몫 합 차, 청산 연도별(가정 시나리오): 2017 −0.62 · 2018 −0.32 · 2019 −0.03 · 2020 0 · **2021 +0.38** · 2022 +0.02 · 2023 ~ 2025 0 · 2026 −0.62. 기존 코드가 2017 ~ 2019-06 앞은 낮게, 2021 ~ 2022는 높게, 2026은 낮게 잡았기 때문에 일부 상쇄됩니다.

읽는 법:
- 이 표는 **고정 원장 진단**입니다. 체결 · 순서 · 수량을 바꾸지 않았고, 추가 비용 때문에 돈이 모자라 실제로는 못 했을 매매를 가려내지 않았습니다(현금 자료 없음).
- 매매 PF는 손익 % 기준이며 **금액 PF가 아닙니다**. 계좌몫 합은 단순 합이며 복리 · NAV 수익률이 아닙니다.
- 절대 수준(평균 손익 · PF)은 생존자 · available_at 결함과 어림 되돌림(B7 · B9)이 있어 검증값이 아닙니다. 의미가 있는 것은 같은 가정 안에서의 **차이**뿐입니다.

## 5. 만들지 않은 것(NEEDS_DATA)
- 원 단위 비용 차액 · 금액 PF: 원장에 수량 · 체결가 없음
- 일별 NAV · TWR · 일별 MTM MDD · 월별 · CAGR · 하루/달 −15% 판정: 입출금 · 일별 평가 · 체결 시각 · 수량 없음
- 1천만 / 1억 용량: 주문 크기 · 유동성 없음
- 최소 입력 명세: `NEEDS-DATA.json`(asset_id · instrument_type · market · fill_at_kst · side · quantity · fill_price · 비용 구성 · ledger_provenance. NAV용 입출금 · 일별 평가 · 기업행동은 따로. 원 주문번호 · 계좌번호는 요구하지 않음)

## 6. 구분
| 종류 | 무엇 |
|---|---|
| 합성 시험 | `TEST-RESULT.json` · `MUTATION-CHECK.json` |
| 가정 | 수수료 · 미끄러짐 · 충격 · 계좌 1억 · 0.25% 되돌림 · 시장 분류 · S_KOSPI_FARM015 농특세 |
| 고정 원장 진단 | `results/DELTA-SUMMARY.json` · `results/DELTA-ROWS.csv` |
| 독립 검증 | 원본 perf2 대조(차 0) · 재실행 일치 · 손셈 확인(2026 55행 × −0.05%p × 칸 몫 ≈ −0.62) |
| 실측 | 없음 |

## 7. 파일
`PREREG-LOCK.md` · `cost_contract.py` · `COST-CONTRACT.json` · `tests/test_cost_contract.py` · `tests/mutation_check.py` · `TEST-RESULT.json` · `MUTATION-CHECK.json` · `run_replay.py` · `results/DELTA-SUMMARY.json` · `results/DELTA-ROWS.csv` · `NEEDS-DATA.json` · `BLOCKERS.md` · `manifest.json` · 입력 receipt `research-exchange/state/receipts/30-5c8e30599107f967ddb5549cb0950c0e5fcc7f64.json`

재실행: `python3 -I tests/test_cost_contract.py` · `python3 -I run_replay.py <d1_ledger_ASIS.csv> <출력>`(원장은 `git show a61f033:research-exchange/claude-to-gpt/RULES-0002/results/d1_ledger_ASIS.csv`, `--perf2-check`는 pandas가 필요해 `-I` 대신 `-E -P`로 실행)

## 다음 방향
- 세금 교정의 영향은 이 원장에서 작고(BASE 매매 평균 −0.01 ~ −0.04%p) 방향이 해마다 다릅니다. 다음 판단에 필요한 것은 비용 정밀화보다 **체결 단위 원장(수량 · 체결가 · 시각)과 NAV 입력**입니다.
- 기존 `research/perf2.py`에 같은 교정을 넣을지는 별도 승인 단계에서 정하면 됩니다.
