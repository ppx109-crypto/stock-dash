# BASELINE-KIS-DART-AUDIT-0001 — 클로드 사전등록(외부 호출 전)

- 입력: GPT PR #81 head `c0a254fb`(REVIEW · TASK · receipt) · source PR #80 `e088c837`
- 일: 기존 실행환경의 KIS · OpenDART **읽기 전용 자격만** 써서 PR #80의 U2(가격 basis) · U3(기업행동)와 15분봉-일봉 불일치 4/82를 공식 응답과 대조합니다.
- 금지: 주문 · 잔고 · 계좌 API, secret 값 · 길이 · 일부 글자 읽기/출력, secrets 목록 열람, workflow · 인증 변경, 백테스트 · 성과 재실행, 규칙 · threshold · sizing · OOS, KRX · 유료 권한 추가

## 1. 자격 확인(외부 호출 없음)
- 환경변수 `KIS_APP_KEY` · `KIS_APP_SECRET` · `DART_CRTFC_KEY`가 **있는지만** 봅니다(bool). 값은 읽지 않습니다.
- 없으면 그 API 호출은 0회이고 BLOCKED입니다. 다른 경로(GitHub Actions secrets · 웹 화면 긁기 · KRX)로 넓히지 않습니다.

## 2. 쓸 공식 endpoint(자격이 있을 때만 · 조회 전용)
| 용도 | endpoint · TR ID | 요청 필드 | 응답 필드 |
|---|---|---|---|
| 접근 토큰 | KIS `/oauth2/tokenP` | appkey · appsecret | access_token(저장 · 출력 안 함) |
| 일봉 원주가 · 수정주가 | KIS `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` · `FHKST03010100` | FID_COND_MRKT_DIV_CODE=J · FID_INPUT_ISCD · FID_INPUT_DATE_1/2 · FID_PERIOD_DIV_CODE=D · **FID_ORG_ADJ_PRC=0(수정)과 1(원)** 각각 | output2: stck_bsop_date · stck_clpr · (mod_yn이 있으면 기록) |
| 15분봉 4건 1분봉 | KIS `/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice` · `FHKST03010230` | FID_INPUT_DATE_1 · FID_INPUT_HOUR_1=153000 · FID_PW_DATA_INCU_YN=N | output2: stck_bsop_date · stck_cntg_hour · stck_prpr · cntg_vol |
| 공시 목록 | OpenDART `list.json` | corp_code · bgn_de · end_de · pblntf_ty=B(주요사항) | rcept_no · rcept_dt · report_nm(정정 표시) · rm |
| 기업행동 결정 | OpenDART `piicDecsn` · `fricDecsn` · `pifricDecsn` · `crDecsn` · `cmpMgDecsn` · `cmpDvDecsn` | corp_code · bgn_de · end_de | rcept_no · 신주 기준일/효력일 칸(있는 것만) |

- 저장소 근거: `broker_kis.py` L293-310(FHKST03010100 · FID_ORG_ADJ_PRC=0 주석 '수정주가'), `collect_prices.py` L124(그 함수로 price-data 수집), `collect_kis_m15.py`(FHKST03010230), `research/probe_m15_close.py`(2026-10-05 15:30 단일가 빠짐 탐색)
- 위는 코드 주장입니다. 응답으로 확인한 것이 아닙니다.

## 3. 대상(비식별 · `evidence/targets_public.json`)
- 체결 종목 39(해시) · 기업행동 공시 8(해시) · 15분봉 불일치 4건(코드|날짜 해시)
- 해시 = sha256(salt | 코드 | 날짜) 앞 16자리입니다. salt는 로컬에만 두고, salt의 sha256 `eb7b7d08…e4eb`만 공개합니다.
- 우선순위: 기업행동 8 → 불일치 4 → 나머지 31
- 날짜: Train 2025-09-18 ~ 2026-03-31 + 기업행동 효력 확인 2026-10-07까지

## 4. 상한
- KIS 500회(인증 포함) · DART 250회 · 요청마다 429/5xx 재시도 2회
- 같은 요청은 캐시해 다시 부르지 않습니다.

## 5. 판정 규칙
- **가격 basis(레코드 747 분모):** 아래 다섯으로 나눕니다.
  - 저장값 = 공식 원주가(차이 < 0.5원)
  - 저장값 = 공식 수정주가
  - 둘 다 같음(그 기간 사건 없음)
  - 둘 다 아님
  - 조회 불가
  - API가 원/수정 선택을 실제로 다르게 돌려주지 않으면 'UNKNOWN(선택 미지원)'입니다.
- **기업행동 연결:** 효력일 앞뒤 공식 원주가 비율과 수정주가 비율의 차이가 공시 조건(무상 배정 비율 · 감자 비율)의 기계적 배수와 1% 안에서 맞으면 '일치'로 셉니다. 아니면 '불일치', 자료 없으면 UNKNOWN입니다. 접수 시각이 없으면 같은 날 사용은 PIT로 올리지 않습니다.
- **15분봉 4건:** 공식 1분봉에 15:30 단일가 체결이 있고, 그 가격 = 일봉 종가 ≠ 저장 1515 봉 종가이면 '마감 동시호가'로 봅니다. 나머지는 이렇게 나눕니다.
  - 그날 1분봉이 저장 봉보다 많음 → '봉 누락'
  - 원/수정 비율로 설명됨 → 'basis 차이'
  - 날짜 · 시각 어긋남 → 'timezone/장구분'
  - 그 밖 → '기타 UNKNOWN'
- 로컬 사전 진단(저장 사본만)은 '힌트'로만 적고 최종 분류에 넣지 않습니다.

## 6. 출력 · BLOCKED
- `evidence/api-coverage.json` · `price-basis-summary.json` · `corporate-action-summary.json` · `m15-daily-mismatch-summary.json` · `run.log`
- BLOCKED 조건: 자격 없음 · API가 역사 범위나 원/수정 선택을 주지 않음 · 상한 때문에 의미 있는 분모를 못 덮음
- BLOCKED 보고에는 실패 endpoint · 응답 코드 · 호출 수 · 필요한 자격 이름을 적고, 비밀은 적지 않습니다.
- 이 판의 `kd_audit.py`에는 호출 코드가 없습니다. 자격이 있으면 실행이 멈추게 되어 있습니다. 그때는 §2대로 호출 코드를 새 커밋으로 넣고 실행합니다.
