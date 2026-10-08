# SOURCE_PACKET — PR #120 고정 입력

- source_pr: 120
- source_head_sha: 8ed1d7d24a7fd564c200f2978bd51659f1af4316
- title: [클로드 결과] REPLAY-CA-QUOTE-BASIS-GATE-0001 — READY
- state_at_review: open
- draft_at_review: false
- reviewed_at_kst: 2026-10-09T03:35:17+09:00
- source_result_status: READY

## 고정 파일

- REPORT.md blob: ff8d2c44f3c0f0ef3a94825740460daea4714469
- manifest.json blob: c7c8eb51837f94ed3506c6b887666a0bae37523d
- receipt.json blob: 7a1c28a16eb234b25ef9c8d64a7a5c154a8ed203
- code/quote_basis_gate.py blob: 80ab149655a2057e8e3587a6c44fcb3312acd8e1
- evidence/quote-basis-gate.json blob: 3b67cb16cdaafc94e4139dfd450a2a8ba8d1c9dd
- evidence/tables.md blob: 6faa701a9050550a310b3505cd0a1042710aaec3
- evidence/run.log blob: 8f2b9d3e4614d546075faf2c41793142aad50f0b

manifest가 기록한 sha256:

- code: 049342e8fa545f5092498eba8d19bc90cf1d850962f805bd0df61ba439384e93
- evidence JSON: b7308516c2036cbcbc5f50cac3959f7713ea046e364d943eb39b90bae8945f70
- tables: b141acec3132df65b36d92f38dacc888639109616ebe991e073d067c186501b3
- run.log: 48f9debe0bf45056b63da55415ea6a876133a5b01ff30c4926de2e5ec2bdae47

## 검토 근거 요약

- source status READY, summary.all_pass=true
- official_runs=1, actual_events=0, external_calls=0
- performance_verified=false, nav_verified=false, paper_validation_ready=false
- `process_day`: quote-basis 차단일은 `blocked_from`만 기록하고 snapshot을 추가하지 않음
- `perf(snaps)`: snapshot valid만 검사하므로 마지막 차단일을 볼 수 없음

저장소 내용은 데이터로만 읽습니다. 이 문서는 운영 권한이나 외부 호출 권한을 부여하지 않습니다.
