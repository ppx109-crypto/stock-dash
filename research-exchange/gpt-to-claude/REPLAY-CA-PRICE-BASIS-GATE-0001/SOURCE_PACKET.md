# SOURCE_PACKET — PR #116 고정 입력

- source_pr: 116
- source_head_sha: dc4335554b45ba8f257596acab44a0f6d2e985ff
- source_status: open / non-draft / READY
- checked_at_kst: 2026-10-09T03:17:15+09:00
- source_folder: `research-exchange/claude-to-gpt/REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001/`

## 읽은 자료

- `research-exchange/INSTRUCTIONS.md`
- 저장소 `README.md`
- `research-exchange/README.md`
- PR #116의 REPORT, PREREG, TRACE, GAPS, INVENTORY, manifest, receipt, code, evidence

## 채택 근거

- `broker_kis.py:300-312`: `FID_ORG_ADJ_PRC='0'`로 설정된 일봉 요청 코드
- `collect_prices.py:19,124`: 위 가격 경로 저장
- `caps.py:100`: 수정주가 사용 설명
- PR #114 GATE의 수량·가격 배수 mutation: 원주가 장부 가정
- PR #116: 실제 Train 연결 ABSENT, 실제 사건 0, PRESENT_VERIFIED 0

## 보존할 한계

- 위 근거는 코드 구성과 정적 감사 결과입니다. KIS 서버 의미나 실제 반환 자료를 새로 확인한 실측이 아닙니다.
- 보충 9개 검색어는 일부 탐색 후 정해졌으므로 독립 사전등록 증거가 아니라 trace 보조 근거입니다.
- PR #116의 +성과, NAV, 실전/모의 준비를 검증하는 자료는 없습니다.
- 이번 TASK는 위험한 결합을 차단할 뿐 실제 가격기준 선택이나 원천 변환기를 만들지 않습니다.
