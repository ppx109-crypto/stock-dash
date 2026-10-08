# [GPT 지시] SOURCE-VERIFY-0001 — 공식 원문 기반 출처·비용·Universe(t) 검증

- task_id: SOURCE-VERIFY-0001
- program_id: PAPER-READINESS-20261008
- chain_id: MEAS-20261008
- round: 8
- stage: OFFICIAL-SOURCE-VERIFICATION
- status: READY
- source_pr: 27
- source_head_sha: e048b35f925f2bd20d21bbed3ed6d6eb35051830
- paper_validation_ready: false
- live_approval: false

## 목적

SOURCE-0001에서 검색 요약이나 저장소 주석으로만 남은 핵심 주장을 공식 원문으로 검증한다. 이번 단계에서 해결할 것은 **자료를 받을 수 있는지와 비용 계약을 정확히 정의하는 것**이지, API를 호출하거나 데이터를 수집하는 것이 아니다.

## 검증 대상

1. KRX 일별매매정보
   - 공식 제공 시작일과 필드
   - 과거 날짜 조회 가능 범위
   - 과거 날짜 결과가 이후 상장폐지 종목을 포함한다고 공식적으로 보장하는지
   - 거래정지일 종목과 0거래 종목 포함 여부
   - 시가·고가·저가 존재 여부
   - 키 유효기간·호출 한도·활용신청
   - 저장·분석·공개 저장소 재배포 조건
2. KRX/KIND Universe(t)
   - 상장·상장폐지·관리·거래정지·이전상장·합병/분할의 효력일과 announced_at을 공식 자료만으로 재구성 가능한지
   - 일별매매정보만으로 충분한지, 별도 상태/공시 자료가 필요한지
3. OpenDART
   - `list.json`의 `rcept_no`, `rcept_dt`, `report_nm`, `rm` 의미
   - 접수 시각과 정정 원본 연결키 존재 여부
   - 과거 원 공시·정정 전 문서의 현재 조회 가능성을 공식 문서가 보장하는지
   - 날짜만 있을 때 사용할 보수적 `available_at`
4. 비용
   - 2023~2026 KOSPI·KOSDAQ의 증권거래세/농특세를 시행기간별로 표 작성
   - 한국투자증권 국내주식 수수료를 계좌 유형·KRX/NXT·주문 채널별로 분리
   - 사용자 실제 계좌 유형은 모름으로 유지하고 BASE/STRESS/EXTREME에 어떤 값을 쓸지 아직 선택하지 않음
5. 체결제약
   - KRX 가격제한폭·호가단위의 공식 표와 적용 시작일
   - 과거 호가 이력이 없을 때 시장충격을 어떻게 “검증하지 못함”으로 남길지
6. 달력·지수
   - KRX 공식 거래일/휴장일 출처
   - KOSPI/KOSDAQ 지수 일별 공식 시작일과 available_at

## 우선 공식 URL

- KRX 서비스 목록: https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd
- KRX 이용방법: https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO003.jsp
- KRX 이용약관: https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO002.jsp
- KRX 규정: https://regulation.krx.co.kr/
- OpenDART 공시검색 가이드: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001
- 한국투자증권 수수료안내: https://securities.koreainvestment.com/main/customer/guide/_static/TF04ae010000.jsp?tab=2
- 국가법령정보센터 증권거래세법 시행령: https://www.law.go.kr/

접근되지 않으면 검색 요약을 E2로 올리지 말고 `NOT_VERIFIED`로 유지한다. 공식 문서의 표현을 짧게 의역하고 URL·문서명·확인시각(KST)·적용일을 기록한다.

## 반드시 구분할 것

- 공식 문서가 명시한 사실
- 저장소 코드가 기대하는 사실
- 그 둘을 결합한 추론
- 직접 증명하지 못한 주장

“일별매매정보 제공”을 “Universe(t) 완전 복원”으로 자동 확대하지 않는다. 상장폐지 종목·정지 종목 포함 여부는 공식 근거가 없으면 `NOT_VERIFIED`다.

## 허용 범위

- 지정 공식 문서와 exact source head의 SOURCE-0001 산출물 읽기
- 공개 문서의 표를 기계판독 자료로 전사
- 기존 코드의 필드 기대치와 공식 필드의 불일치 비교
- 공개 정보에 한정된 읽기 전용 조사

## 금지 범위

- KRX·KIS·DART 데이터 API 호출, 인증키 신청/입력, 신규 데이터 수집
- 로그인, 약관 동의, 활용신청, 권한 변경
- 운영 봇·collector·전략·배분·워크플로·스케줄·인증 변경
- 실계좌/모의 주문, 계좌 원문·키·토큰·원 주문번호 열람
- 백테스트, threshold 탐색, 알파 채택, OOS 사용
- 유료 데이터 구매, Git 이력 변경, 병합, 새 세션·탭·Routine 생성

## 산출물

- `research-exchange/claude-to-gpt/SOURCE-VERIFY-0001/REPORT.md`
- `OFFICIAL-SOURCE-MATRIX.json`
- `COST-TABLE.json`
- `manifest.json`
- 입력 PR번호+headSHA receipt

결과 PR 제목은 `[클로드 결과] SOURCE-VERIFY-0001`로 시작한다. 결과 PR을 열기 전에 산출물을 완성하며, 연 뒤 결과 branch에 커밋하지 않는다.

## 완료 조건

1. 위 6개 검증 대상마다 `PROVEN / PARTIAL / NOT_VERIFIED` 판정이 있다.
2. 모든 PROVEN에 공식 URL·문서명·확인시각·적용일 또는 데이터 시작일이 있다.
3. KRX 일별매매정보가 상장폐지·정지 종목을 포함하는지는 별도 필드로 판정한다.
4. 2023~2026 세금표는 세율 구성과 시행기간을 분리하고 법령 근거를 기록한다.
5. 수수료는 계좌 유형을 모르는 상태에서 단일 숫자로 고정하지 않는다.
6. DART 날짜·시각·정정 연결·과거 원문 조회 가능성을 각각 분리한다.
7. 확인되지 않은 재배포 권한은 공개 허용으로 쓰지 않는다.
8. manifest hash가 일치하고 비밀·계좌 원문·비공개 세션 식별자가 없다.
9. `paper_validation_ready=false`, `live_approval=false`를 유지한다.
