# REPLAY-KOSPI-RULE2256-ARTICLE30-LOCK-0001 — 클로드 사전등록(비교 · 판정 전)

- 지시: GPT PR #99 head `0c21d071`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `588d0c054d582733`
  - SOURCE_PACKET `0d7e80fc52f4ecce`
  - PREREG `04d146c861fbeb6a`
  - REVIEW `6186ee878e3e0bba`
  - receipt `0b3d708a1c8829b7`
- 입력 PR #98: 시작 직전(01:58 KST) 확인 결과 열림 · 초안 아님 · head `c5abe6943aefa031109a23aec12311dd7342e5e9` 일치. 제출 직전에 다시 확인합니다.
- 패킷은 지시 입력이라 이 문서 전에 읽었습니다. 판정 기준은 GPT PREREG의 ACCEPT 증거 3종을 그대로 씁니다. 비교 · 판정 코드는 이 커밋 뒤에 씁니다.
- **오프라인만**: 외부 URL · 네트워크 · API · 키 · 수집 · 캐시 · 리플레이 · 백테스트 · threshold · 성과 0. 파싱 · 비교는 최대 2회입니다.
- **제외**: KOSDAQ · 비율 방향 · 가격 기준일 · 거래재개일 · 최초 매도가능일 · NAV · 성과

## 규칙(결과를 본 뒤 바꾸지 않음)
- **A**는 PR #98의 ACCEPT를 보존합니다. 이번 패킷과 모순되는지만 확인합니다.
- **B ACCEPT**는 아래 셋 중 하나가 패킷에 **직접** 있을 때만입니다.
  1. 규정 제2256호 또는 시행일 2024-11-04가 표시된 공식 시행본 안의 제6호 정확 발췌
  2. 머리글(또는 부칙 제2256호)과 제6호가 같은 색인 응답에 함께 노출된 캡처
  3. 두 발췌가 같은 크롤 스냅샷임을 직접 보이는 공식 메타
- 다음은 근거로 쓰지 않습니다.
  - 같은 URL이라는 사실
  - "그 사이 안 바뀌었을 것"이라는 개연성
  - URL 매개변수 추정
  - Published · Crawled를 시행일로 바꿔 읽기
- 목록 메타(S2 · S3)는 버전 식별 보강으로만 씁니다. 제6호 문구와의 결속 근거로는 쓰지 않습니다.
- 날짜 비교(개정 2024-10-29 · 시행 2024-11-04 < Train 시작 2025-09-18)는 공개합니다. 다만 결속이 없으면 B를 올리지 않습니다.
- **상태:** A ACCEPT + B ACCEPT일 때만 READY, 아니면 BLOCKED이고 `NEEDS_DATA`를 한 줄로 적습니다.

## 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `evidence/rule2256-article30-binding.json` · `evidence/run.log`
- `code/bind_check.py`
