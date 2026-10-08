# REPLAY-OFFICIAL-SEMANTICS-AUDIT-0001 — 클로드 사전등록(공식 문서 조회 전)

- 지시: GPT PR #89 head `1b9491a1`. 파일 sha256 앞 16자는 다음과 같습니다.
  - REVIEW `8feb53b83a601f15`
  - TASK `e57ccee6232da490`
  - PREREG `ca33470fd8abda27`
  - receipt `6a4eac8c85f43f9e`
- 입력 확인:
  - PR #88 head `a5891f5b…` 일치
  - PR #87 읽은 head `fd37b8b9…` / 지금 head `24df3f41…` — 차이는 `receipt.json` 1개(8줄)
- 이 커밋 전에는 공식 문서를 하나도 열지 않았습니다. 도메인 접속 확인도 하지 않았습니다.
- 금지(지킴):
  - 데이터 API 호출 · 토큰 · 키 · Secrets · 실제 수집 · 캐시
  - 148 · 전체 원장 재생 · 성과
  - alpha · threshold · OOS · 주문 · 운영 · 워크플로 · 15분봉 · 자동병합
  - 원시 식별 정보 공개

## 1. 근거 규칙(조회 뒤 바꾸지 않음)
- **근거로 인정하는 원문:** 아래 공식 도메인의 원문만 씁니다.
  - `opendart.fss.or.kr`(개발가이드 · API 목록)
  - `dart.fss.or.kr`(공시 안내)
  - `krx.co.kr` · `law.krx.co.kr` · `kind.krx.co.kr`(규정 · 업무 안내)
  - `apiportal.koreainvestment.com`(KIS Developers)
- **KIS 공식 GitHub:** `github.com/koreainvestment`(한국투자증권 공식 조직의 open-trading-api)는 "KIS 공식 배포물"로 따로 등급을 매깁니다. 포털 원문을 기계로 읽을 수 없을 때만 보조로 씁니다.
  - 값 방향 판정에는 둘 중 하나의 **명시 문구**가 있어야 합니다.
  - 샘플 코드의 기본값이나 변수 이름만으로는 판정하지 않습니다.
- **원문 수집 방식:** `curl`로 원문(HTML · 파일)을 받습니다.
  - 받은 원문은 로컬에만 두고 커밋하지 않습니다.
  - 근거표에는 URL · 제목 · 조회 시각(KST) · HTTP 상태 · 원문 sha256 · 짧은 인용(원문 그대로)만 남깁니다.
- **쓰지 않는 도구:** WebFetch(AI 요약을 돌려줌)는 근거로 쓰지 않습니다. 검색(WebSearch)은 공식 URL 위치를 찾는 데만 씁니다.
- **실패 기록:** 접근 실패(HTTP 오류 · 차단 · 자바스크립트 전용 페이지)도 행으로 남깁니다.
- **데이터 API 금지:** `/api/*.json` · `/api/*.xml` 같은 데이터 API는 부르지 않습니다. 문서 페이지만 엽니다.
  - OpenDART 가이드 페이지(`/guide/...`)는 문서이므로 엽니다.
  - KIS `/uapi/...` 호출 · `/oauth2/...` 토큰 발급은 하지 않습니다.

## 2. 항목별 판정 규칙(미리 고정)
**A. KIS**
1. endpoint · TR ID는 문서에 둘 다 적혀 있으면 ACCEPT입니다.
2. `FID_ORG_ADJ_PRC`는 문서가 "0 = 수정주가 · 1 = 원주가"(또는 반대)를 명시하면 그대로 ACCEPT합니다.
   - PR #88 스키마(1 = RAW · 0 = ADJUSTED)와 반대면 REVISE입니다.
   - 명시가 없으면 `UNKNOWN_KIS_DOC_SEMANTICS`입니다.
3. 한 응답 최대 행 수 · 연속조회 여부는 명시 숫자가 있을 때만 ACCEPT입니다. 없으면 `UNKNOWN_KIS_DOC_SEMANTICS`이고, 호출식은 "행 한도 미확정"으로 둡니다.
4. 응답 날짜 · 종가 칸 이름은 명시되면 ACCEPT입니다. 거래정지 · 무거래 표현은 문서에 없으면 `NEEDS_DATA`입니다.
5. 호출식은 2 · 3이 ACCEPT일 때만 숫자로 씁니다. 아니면 식만 쓰고 숫자는 UNKNOWN입니다.

**B. DART 사건 경로(9종)**
- 구조화 endpoint 존재는 OpenDART 공식 API 목록(주요사항보고서 그룹 전체)에 그 이름이 있으면 ACCEPT입니다.
- **없음**도 같은 공식 전체 목록으로 증명합니다. 목록 전체를 못 받으면 `BLOCKED_NO_OFFICIAL_EVIDENCE`입니다.
- 회사분할(`cmpDvDecsn`)과 주식 액면분할은 같은 사건으로 보지 않습니다.
- 구조화 API가 없는 사건(액면분할 · 병합 예상)은 아래가 모두 공식으로 확인돼야 ACCEPT입니다. 하나라도 빠지면 `BLOCKED_NO_OFFICIAL_EVIDENCE` 또는 `BLOCKED_UNMAPPED_KIND`입니다.
  - 공시목록(list) 필터 칸(pblntf_ty · pblntf_detail_ty 값)
  - 공시원문(document) 경로
- 칸(비율 · 기준일 · 효력일 · 상장일 등)은 해당 endpoint 가이드의 응답 칸 목록에 있으면 ACCEPT입니다. 없으면 NEEDS_DATA입니다.

**C. 날짜 · 수량 · 매도 가능 의미(사건별 3시점)**
- KRX 규정 · 업무 안내 원문이 그 사건의 다음을 명시해야 ACCEPT입니다.
  - 권리락(가격 기준 변경일)
  - 매매거래정지 · 재개
  - 변경 · 신주 상장일
- PR #88 규칙과의 관계:
  - 규칙은 `price_basis_date`에 수량 · 가격을 바꾸고, `listing_date` 전에는 늘어난 수량의 매도를 막습니다.
  - 공식 문구와 같으면 ACCEPT, 다르면 REVISE(고칠 내용 적음), 문구가 없으면 `BLOCKED_NO_OFFICIAL_EVIDENCE`입니다.
- 권리락일 · 기준일 · 효력일 · 변경상장일은 서로 대체하지 않습니다.
- 법적 발생일(효력일)은 매도 가능일과 따로 적습니다.

**D. available_at · 정정 사슬**
- `list` 응답 칸의 접수일 정밀도를 봅니다. 날짜만이면 PR #88 규칙(당일 사용 금지 · 다음 거래일부터)을 유지하고 ACCEPT입니다.
- 접수 시각(시:분) 칸이 공식 응답에 없으면 `same_day_pit`는 늘 false입니다.
- 정정 연결: 정정공시가 원 접수번호를 공식 칸으로 주면 ACCEPT입니다.
  - 보고서명 머리말(예: [기재정정])이나 비고 칸만 있으면 사슬을 확정하지 못하므로 `UNKNOWN_CA_VERSION_PIT`입니다.
  - 원문 안 정정 대상 접수번호를 읽는 경로는 공식 문서로 확인될 때만 REVISE 제안으로 둡니다.

**E. 동적 호출 예산:** 계산 없는 의사코드로 고정합니다. 72는 예시일 뿐 허용치가 아닙니다.

**F. 148 경계:** 148은 기존 체결 감사 분모입니다. 전체 판단 목표(D1 542 · BASKET 154)의 원주가 재생은 하지 않았고, 추가 · 소멸 주문이 생길 수 있습니다. 문장으로만 명시하고 계산하지 않습니다.

## 3. 열어 볼 공식 문서(계획 · 바뀌면 이유 기록)
1. OpenDART 개발가이드 목록(공시정보 DS001 · 주요사항보고서 DS005 그룹 전체)
2. OpenDART 공시검색(list) · 공시서류원본파일(document) · 고유번호 가이드
3. OpenDART DS005 상세 7개(유상 · 무상 · 유무상 · 감자 · 합병 · 분할 · 분할합병) 가이드의 응답 칸
4. KRX 법규(유가증권 · 코스닥 업무규정 · 시행세칙 · 공시규정)의 권리락 · 주식분할 · 병합 · 감자 매매거래정지 · 변경상장 조항
5. KIS Developers `inquire-daily-itemchartprice`(FHKST03010100) 문서. 기계로 못 읽으면 KIS 공식 GitHub의 같은 API 명세를 봅니다.

## 4. 판정 · 상태
- 각 근거 행의 칸: URL · 제목 · retrieved_at_kst · HTTP 상태 · sha256 · 주장 · 칸 이름 · 판정
- **READY:** A~F가 모두 공식 근거로 판정됐고, KIS 값 방향 · 행 한도와 DART 분할/병합 경로가 확정됐을 때입니다.
- **BLOCKED:** 위 핵심 셋 중 하나라도 공식 근거로 확정되지 않으면 BLOCKED입니다. 확인된 행과 정확한 결손은 함께 냅니다.
- 같은 문서를 다시 받는 것은 접근 실패 때 1회만 합니다(기록). 판정 기준 · 사건 범위 · 날짜 의미 규칙은 조회 뒤 바꾸지 않습니다.
