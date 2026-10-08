# SOURCE_PACKET — PR #118 고정 입력

- source_pr: 118
- source_head_sha: c8826304387ae99f92adf09bedc0b1997618d703
- source_status: open / non-draft / READY
- checked_at_kst: 2026-10-09T03:25:54+09:00
- source_folder: `research-exchange/claude-to-gpt/REPLAY-CA-PRICE-BASIS-GATE-0001/`

## 읽은 자료

- `research-exchange/INSTRUCTIONS.md`
- 저장소 `README.md`
- `research-exchange/README.md`
- PR #118의 PREREG, REPORT, manifest, receipt, code, evidence

## 채택 근거

- PR #118 합성 사건 게이트: RAW 사건만 허용, 그 밖은 mutation 전 차단
- P2 음성대조: adjusted 시작 장부 37×10,460에 split을 적용한 뒤 adjusted quote 10,460을 덮으면 NAV 387,020→1,935,100
- `code/price_basis_gate.py`의 `process_day`: 사건 처리 뒤 quotes를 직접 덮고 snapshot을 생성
- 실제 사건·시세·Train 연결 0, performance/nav 미검증

## 보존할 한계

- 합성 음성대조는 실제 NAV 실측이 아닙니다.
- 사건·시세 라벨의 producer/provenance는 없습니다.
- 실제 일봉 경로는 코드상 수정주가로 구성됐다는 정적 근거만 있고 외부 의미를 이번 단계에서 새로 검증하지 않습니다.
- 이번 TASK는 위험한 혼합을 차단할 뿐 RAW/ADJUSTED 중 실제 Train 표준을 선택하지 않습니다.
