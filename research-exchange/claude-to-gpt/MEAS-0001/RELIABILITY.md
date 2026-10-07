# RELIABILITY — 전략별 모의 신뢰성(MEAS-0001 · 실전 등급 아님)

판정 칸: 데이터(시점 · 출처) / 규칙 · 코드(운영 = 연구 일치) / 계좌 · 체결(모의 원장) / OOS. 하나라도 UNVERIFIED면 종합 PASS 금지.

| 전략 | 데이터 | 규칙 · 코드 | 계좌 · 체결 | OOS | 종합 |
|---|---|---|---|---|---|
| 1D '새 82' | **FAIL** — 수급 가용일 날마다 다름(T−1/T−2) · 종가 88% 나중에 바뀜 · 연구 calm 전 기간(미래) | **FAIL** — 운영 calm(그날까지) ≠ 연구 calm(전 기간) · 수급 기준일 차이(RULES-0002: 후보 76% 바뀜) · 107/107 일치는 같은 자료 위 판단 함수만 | **UNVERIFIED** — 10-02 ~ 10-07 판단 3일 · 매매 0건(폭 < 50) · 체결 · 현금 기록 없음 | UNVERIFIED(기존 기간뿐) | **INSUFFICIENT_EVIDENCE**(연구 MTM 수치는 INVALID_MEASUREMENT — 현금 음수 28%의 날) |
| 15m 22회차 | FAIL — 같은 수급 · 종가 시점 문제(전날 저녁 plan) | UNVERIFIED — 연구 재생 = 원본 함수(RULES-0002) · 운영 실행 시각(봉 뒤 약 3분) 차이 미측정 | UNVERIFIED — 10-02 ~ 10-07 상태 66번 · 매매 0건 | UNVERIFIED(1년 · 이미 본 기간) | **INSUFFICIENT_EVIDENCE** |
| H1 90회차 | FAIL(같은 이유) | — | **해당 없음** — 주문 몫 0 · PAPER_TRADING off(스냅샷 코드 · 워크플로가 기준점과 같음) · 상태 25번 · 매매 0 | — | **평가 대상 아님(주문 안 함)** |
| 빈칸 엔진 · 인버스 | 부분 — ETF는 NXT 없음 · 15:10 현재가 + 어제까지 종가 | UNVERIFIED — 연구(i013)의 몫 날마다 맞춤 ≠ 운영(산 수량 유지 · AUDIT-1 F4) | **UNVERIFIED** — KIS 모의 주문 2건(10-06 거절 · 10-07 접수 · 수량 약 0.81배로 줄음) · 장부 held = 접수 합(일치) · **체결 · 현금 · 비용 기록 없음** | UNVERIFIED | **INSUFFICIENT_EVIDENCE** |
| 바구니 C | FAIL — 공시 날짜만 · 첫 수신이 다음 날 15:10 뒤인 사건 11 / 31 | FAIL — 제목 부분 일치 갈래(RULES-0001) | **없음** — 운영에서 한 번도 안 돎(코드 도입 10-07 21:24) | UNVERIFIED | **INSUFFICIENT_EVIDENCE** |

## 종합 판정
- **모의 평가: INSUFFICIENT_EVIDENCE** — 체결 · 예수금 · 비용 · NAV 원장이 없고 매매 표본이 사실상 0(모의 주문 2건).
- **연구 측정(1D MTM · RULES-0002 수치): INVALID_MEASUREMENT** — 현금 제약 없는 평가(최대 노출 122%) + calm 전 기간 문턱(미래 행) + 고정 수급 지연 가정(실제는 날마다 다름).
- TRUSTED_FOR_PAPER_EVALUATION인 전략 없음. 이것은 아이디어가 틀렸다는 판정이 아니라 **측정이 아직 믿을 만하지 않다**는 판정.
