# SOURCE_PACKET — official KRX index captures

이 패킷은 2026-10-09 01:23 KST에 공식 KRX 법규 사이트의 검색 색인에서 캡처한 최소 문구다. 직접 원문 열람이 아니며 증거 등급은 모두 `GPT_CAPTURED_OFFICIAL_INDEX`다. 아래 URL을 다시 호출하지 않는다.

## S1 — lawid 000111, 공개일 2024-05-23

- issuer: 한국거래소
- URL: https://law.krx.co.kr/las/RefBon.jsp?lawid=000111&pubdt=20240523&pubno=22310
- index facts:
  - 조문 표제: `종목별 매매거래정지후 매매거래 재개등`
  - 검색 색인은 일부 정지사유의 재개일을 다음 매매거래일 또는 거래소가 정하는 날로 표시한다.
- currentness: 2024-05-23 공개본이라는 것만 캡처됨. 현재 통합본·시행일·규정 정식명은 이 패킷만으로 미확정.

## S2 — lawid 000111, 통합 화면

- issuer: 한국거래소
- URL: https://law.krx.co.kr/las/LawBon.jsp?lawid=000111
- exact indexed excerpt: “주식분할 또는 주식병합된 종목은 전일종가에 분할 또는 병합의 비율을 곱한 가격으로 한다.”
- additional indexed fact: 분할·병합되는 날에는 `당일의 기준가격`을 사용한다는 문구가 표시됨.
- currentness: 검색 색인 수집 시점은 약 2026년 8월로 표시되었으나, 현행 시행일·정식 규정명은 직접 원문에서 확인하지 못함.

## S3 — lawid 000111, 공개일 2022-08-26

- issuer: 한국거래소
- URL: https://law.krx.co.kr/las/RefBon.jsp?lawid=000111&pubdt=20220826
- indexed fact: 장기간 거래정지 뒤 최초 호가일에 분할·병합되는 종목은 `당일의 기준가격`을 사용하는 유형으로 열거됨.
- currentness: 2022-08-26 공개본. 이후 개정·현행 적용 여부 미확정.

## S4 — lawid 000212, 공개일 2019-04-17

- issuer: 한국거래소
- URL: https://law.krx.co.kr/las/RefBon.jsp?lawid=000212&pubdt=20190417
- exact indexed excerpt: “직전 매매거래일 종가에 분할 또는 병합비율을 곱한 가격”
- indexed context: 분할·병합되는 종목의 기준가격 산식으로 표시됨.
- currentness: 2019-04-17 공개본. 시장·정식 규정명·현행성은 이 패킷만으로 미확정.

## S5 — lawid 000210 / 000212 비교 화면

- issuer: 한국거래소
- URL: https://law.krx.co.kr/las/CompLawD.jsp?lawid=000210
- indexed facts:
  - 분할·병합되는 날에 `당일의 기준가격`을 사용한다.
  - 기준가격은 직전 매매거래일 종가와 분할·병합 비율로 계산한다.
- currentness: 비교 화면에 나타난 버전과 시장·정식 규정명은 직접 원문에서 확인하지 못함.

## 사용 한계

1. 공식 도메인의 색인 캡처이지만 직접 원문이 아니다.
2. S1~S3이 유가증권시장, S4~S5가 코스닥시장이라는 대응은 이번 과제에서 검증할 주장이지 전제가 아니다.
3. `당일`이 거래재개일인지, 신주 상장예정일인지, 효력발생일인지 이 패킷만으로 자동 확정하지 않는다.
4. 현행 규정명·조문 번호·시행일이 확인되지 않으면 시장별 ACCEPT를 금지한다.
5. PR #92의 사례 일치는 보조 관찰이며 공식 일반 규칙을 대체하지 않는다.
