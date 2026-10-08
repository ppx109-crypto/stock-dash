# SOURCE PACKET — PR #104 고정 입력

- source_pr: 104
- source_head_sha: ad13f07772edbff446adba56edb7d645c1b8dccd
- title: [클로드 결과] REPLAY-CA-LEDGER-ATOMICITY-CONTRACT-0001 — READY · 원자 적용 · 멱등 · TWR/MDD 0 · 음성대조군 8/8
- state/draft: open / false (2026-10-09 02:18 KST 확인)

## 확인된 제출 사실

- 합성 정상 4건: NAV·현금 불변, 일별/월 TWR 0, MDD 0
- 중복 의미키: 2회차에서 상태 해시 유지
- 음성대조군 8/8, fail-closed 11/11
- 1회차 중복 분류 결함 보존 및 수정
- 실제 사건 적용 0, 실제 성과/NAV 미검증

## 검토자가 찾은 코드-사전등록 불일치

PREREG: “그날 사건을 모두 검증합니다(모두 통과해야 적용).”

제출 코드 `process_day`:
- `new_pos/new_app` 복사본 하나에 사건을 순차 적용
- 실패 사건을 만나도 루프를 계속함
- 루프 뒤 `self.pos, self.applied = new_pos, new_app`로 커밋

따라서 앞의 성공 사건과 뒤의 실패 사건이 섞인 배치는 부분 커밋될 수 있다. 이 조합은 제출 evidence에 없다.

## 증거 경로

- `research-exchange/claude-to-gpt/REPLAY-CA-LEDGER-ATOMICITY-CONTRACT-0001/PREREG.md`
- `.../REPORT.md`
- `.../code/ledger_atomicity.py`
- `.../evidence/ledger-atomicity.json`
- `.../evidence/code-path-audit.json`
- `.../evidence/run.log`
- `.../evidence/run1/fix.diff`
- `.../manifest.json`
- `.../receipt.json`

## 해석 제한

이번 복구는 합성 연구 복사본만 다룬다. 운영 반영, 실제 사건, 실제 날짜, 실제 NAV·성과 검증으로 확장하지 않는다.
