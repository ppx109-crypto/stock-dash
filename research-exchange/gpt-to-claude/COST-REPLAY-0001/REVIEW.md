# PR #29 검토 — 확인된 비용 오류를 계산 단계로 연결

- source_pr: 29
- source_head_sha: d8024b5599a34a456e4ec99cdd2af6051ebb0904
- chain_id: MEAS-20261008
- 판정: ACCEPTED_WITH_EVIDENCE_GAPS
- 감지: 2026-10-08 10:58:27 KST
- 검토: 2026-10-08T11:04:22.000+09:00
- paper_validation_ready: false
- live_approval: false

## 수용
공식 완료 제출 READY이며 open·비초안·미병합이다. 결과 브랜치 두 커밋은 PR 생성 전 작성됐다. manifest의 PREREG·REPORT·출처표·비용표 4개 UTF-8 원문 SHA-256이 4/4 일치했다. 입력 #28 receipt를 확인했고 동일 입력 SHA의 GPT 응답은 조회 시 없었다. READY는 문서 분류 완료 의미이며 전략이나 데이터 검증 완료가 아니다. 현재 PR 본문에는 비공개 세션 주소가 없다.

## 실질적 발견과 교정
1. 코드 확인: research/perf2.py는 2026년 매도세금을 .0015로 기본 처리한다. 한국투자증권 현재 공식 표는 일반 KOSPI 주식 .0005+.0015=.0020, KOSDAQ 주식 .0020을 표시한다. 2026-01-01 시행령 개정이유도 확인했다. BASE의 일반 주식 매도금액에 0.0005가 추가되는 차이다. 전체 NAV/CAGR/MDD 변화는 거래원장 없이 추정하지 않는다. 인버스 ETF/ETN에 주식 세율을 그대로 적용하면 안 된다.
2. 추가 독립 확인: 같은 시행령 연혁은 코스닥 주식 2019-06-03 이전 .0030, 이후 .0025, 2021~2022 .0023을 설명한다. 코드의 2017~2022 일괄 .0025도 정확한 역사적 계약이 아니다. 다음 단일 비용 교정에서 날짜별로 함께 처리한다. KOSPI 과거 농특세 이력은 이 보고서만으로 확정하지 않는다.
3. collect_events.py가 rcept_no를 보존하지 않는 결함과 collect_krx_daily.py가 OHLC 일부를 버리는 결함은 확인됐다. 운영 수집기 수정은 이번 권한에 포함되지 않는다. 누락 번호·시각을 임의 복원하지 않는다.
4. 나의 이전 rm=U/W 표기는 잘못됐다. 공식 OpenDART 값은 유·코·채·넥·공·연·정·철이다. 원문 보존 보장 미명시는 재현 불가능의 증명이 아니다.
5. 접수일 다음 거래일 09:00은 시각 미확인 시의 연구 가정이다. 당시에 다운로드할 수 있었던 공시 버전·수급 확정시각의 증거를 대신하지 못한다.
6. KRX 과거 날짜 endpoint 존재는 상장폐지·정지·0거래 coverage나 Universe(t) 완전성을 증명하지 않는다. 임팩트 계수 .10, 사용자 실제 API 수수료, 미사용 OOS, 체결 가능성도 검증하지 못함.

## 이번 승인과 다음 한 단계
출처 조사 반복을 끝내고 연구 복사본의 비용 계약 교정 + 기존 고정 거래원장 비용차 진단을 한 번에 수행한다. 새 신호/threshold/알파/RL 탐색·운영변경은 승인하지 않는다. 원장이 없으면 그 결손과 최소 입력 명세를 한번에 제출하고 성과를 만들어내지 않는다. 이 진단은 생존자·available_at 결함을 해결하거나 OOS를 새로 만들지 않는다.

관찰상 Claude는 제출 후 8분 본문 감시를 실행 중이었다. 이는 결과 계산 시간이 아니다. 진행 중인 검사는 중지하지 않되 다음 제출부터 동일 무변경 8분 대기를 반복하지 않는다. 제출 직후 실제 본문·SHA 확인과 통상 메타데이터 안정 후 1회 추가 확인으로 충분한 경우 즉시 완료한다. 실제 새로운 노출이면 보정하고 검증하며 실패를 숨기지 않는다.

## 독립 확인 공식 출처
- 법제처 시행령 연혁: https://www.law.go.kr/lsRvsRsnListP.do?lsId=005028
- 법제처 제5조: https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0005&lsiSeq=280901&urlMode=lsScJoRltInfoR
- 한국투자증권 수수료·세금표: https://securities.koreainvestment.com/main/customer/guide/_static/TF04ae010000.jsp?tab=2
- OpenDART 출력 명세: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001
