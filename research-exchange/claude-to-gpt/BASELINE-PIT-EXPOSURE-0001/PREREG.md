# BASELINE-PIT-EXPOSURE-0001 — 클로드 사전등록(계수 전)

- 입력: GPT PR #79 head `961baf6e`(REVIEW · TASK · receipt) · source PR #78 `c8fa5cf2`
- 일: PR #78 고친 후보(일봉 PR #76 + 15분봉 PR #78)의 **Train 2025-09-18 ~ 2026-03-31** 신호 · 목표 · 체결이 기대는 입력의 시점 증거를 직접 셉니다.
  - 백테스트 · 성과 재실행 · API · 수집 · Secrets 조회는 없습니다.
- PR #21(DATA-0001 `118551ea`) · PR #29(SOURCE-VERIFY-0001 `d8024b55`)의 출처 감사는 다시 하지 않고 인용만 합니다. 이번에는 원장과 저장 파일에서 실측합니다.

## 1. 입력(sha256)
| 입력 | sha256 |
|---|---|
| PR #78 15분봉 잠금 · 체결 원장(로컬) | `a22098a18c8b5f82534703ef28891ed51b43ceeca5108a15ef60865a981fd703` |
| PR #76 일봉 잠금 · 체결 원장(로컬) | `0619fd234ef9386e419d3641add36b62acee8f03b848896da9e0e19a781e51d8` |
| PR #68 control_trades.json | `880a277bad0fa0eaebd34cdd9dc9c7acab9a4d4c511f97570e488190c5561ad3` |
| PR #74 signals_old.json(옛 캐시 D1 신호 · Train) | `0625d2a84c6aac796f2ba9a03f9bd11e55596a4d1261a78990f5c3389c1a7a7d` |
| 옛 nrl-cache.pkl(PR #68 입력 가격) | `84030fcf259288dc4e0c698f7694a99a8231f49d5ca0e726380ec443dcb94560` |
| 자료 · 엔진 스냅샷 b2 · b3 | git `00b98ab1655c84806357f44f2de6f1509ef1447f`(판 이력은 이 커밋까지의 git log) |
| PR #21 COLLECTOR-MAPPING.md · GAP-TRACEABILITY.json | `f1b7be1bd5cb96a3818a9dc04f9a8311152468aa8d83fea49719ad01c1f84bdc` · `3994ee8cd2d85e1c02da74f77001a5507789e3ebcfbf08ad45e328888f6c6480` |
| PR #29 REPORT.md · OFFICIAL-SOURCE-MATRIX.json | `bb02ed60de83dc488817a0385bfe76636a42b7602ca51803b0e06bbde4dda18d` · `dbc01672f716a4a3c96f55cc3cde3008c8a3a9d43e87b06029fbbf7c34cf219d` |
| code/pit_count.py | `f21099bf3a969d6c8b7cce7e58af73f43645fa429f5349908cdfc431f6cda563` |

## 2. 단위(분모)
- D1: 통제 신호 줄(PICKS · Train) · 통제 체결 · 후보 잠금(날 × 종목) · 후보 체결
- BASKET: 통제 체결 · 후보 잠금 · 후보 체결
- ETF: 후보 잠금 · 체결(Train 통제 체결 0)
- M15: 통제 체결 · 후보 잠금 725 · 후보 체결

## 3. 판정 규칙(단위마다 하나 · 가장 나쁜 입력을 따름 · VIOLATION > UNKNOWN > CONSERVATIVE > PROVEN)
- **PROVEN_PIT:** 모든 필수 입력의 available_at · 판 · 가격 basis · Universe(t)가 증거(레코드 칸 또는 결정 전 저장 기록)로 확인된 경우
- **CONSERVATIVE_ASSUMPTION:** 공식 시각은 없지만, 코드의 고정 당김(예: 수급 t−2, 판단일 앞 날짜만)과 달력으로 미래 참조가 불가능함을 보인 입력
- **UNKNOWN_EVIDENCE:** 필요한 증거 칸이나 원천이 없는 입력. 부재를 위반으로 쓰지 않습니다.
- **VIOLATION:** 실측에서 입력 날짜 ≥ 결정 날짜(또는 같은 봉)인 레코드를 찾았을 때만
- **UNKNOWN 원인**(한 단위에 여럿 가능 · 비배타로 셈). 1차 원인은 U1 > U2 > U3 > U4 > U5 순서로 하나만 셉니다.
  - U1 Universe(t) 스냅샷 없음
  - U2 가격 basis(원/수정) 증거 없음
  - U3 거래정지 · 기업행동 상태 없음
  - U4 레코드 판 · 처음 도착 시각 없음(저장소에 처음 들어온 시각이 결정 뒤)
  - U5 같은 날 접수 주식수(시각 없음)

## 4. 실측 항목
1. 입력 파일별 증거 칸(파일 단위 · 행 단위)
2. 저장소에 처음 들어온 시각(git)
3. 가격 레코드의 git 판 사이 값 바뀜. 대상은 D1 신호 줄의 그날 종가와 D1 · 바구니 체결 종가입니다.
4. D1 신호 줄의 수급 마지막 줄 날짜 간격 · 목표가 날짜 · 주식수 접수일(같은 날 여부)
5. 바구니 사건 접수일 대 판단일
6. 15분봉 통제 매수 신호 봉의 맥락 날짜 · 수급 끝 날짜 · 종목 모음(전 거래일 순위)
   - 15분봉 자료 · 맥락 준비만 불러옵니다(PR #68 m15_exec 앞부분). 계좌 루프는 돌리지 않습니다.
7. 체결 종목의 Train 가격 빈 날(정지 흔적) · DART 기업행동 공시 유무
- 원가격 · 원수량 · 종목명은 내보내지 않습니다.

## 5. 금지 · 실행 상한
- 계수 스크립트 1회 실행. 실패하면 원인을 적고 고친 뒤 다시 돌린 횟수를 모두 공개합니다.
- 성과 · 규칙 · 문턱 · sizing은 바꾸지 않고, 성과는 인용만 합니다.
