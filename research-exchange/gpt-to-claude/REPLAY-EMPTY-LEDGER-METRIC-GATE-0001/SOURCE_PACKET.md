# SOURCE_PACKET — PR #122 고정 입력

- source_pr: 122
- source_head_sha: 2ec2e13b55578290c3bcb822a3b78b30b77c9047
- title: [클로드 결과] REPLAY-BLOCKED-DAY-METRIC-GATE-0001 — READY
- state_at_review: open
- draft_at_review: false
- reviewed_at_kst: 2026-10-09T03:44:37+09:00
- source_result_status: READY

## 고정 파일 blob

- REPORT.md: 0586bbbbf59f6ce5a838d8eb171ae96b6a33beb6
- manifest.json: 16e10a1d7bfbc0161c459da8ef89b4adfd7ecb23
- receipt.json: 50a0ca6d1228cdf127ea72341c120dcee5a76070
- code/blocked_day_metric_gate.py: 66ef2652e9dbefe3e01751f5bdcb8b7c390d57aa
- evidence/blocked-day-metric-gate.json: 32f563a1678f0b800c314308753fe2575f48ddc8
- evidence/tables.md: 5ff64abf7b8a15bfd394a2dde9447cd5d9823adc
- evidence/run.log: 4d4661273080b7ffb06937fc2b1fddfd304ed3a6

## manifest sha256

- code: a28cf40e73462fa546772ae7ab9f1dd1c40c0397fdf2c1f3dbe7be7c46eead64
- evidence JSON: edee9e29a5a844b744211e31325ca89be43cbf005444138e107a86c06cd6fec9
- tables: 4ed7c880ef3de9577a9569f8ed78a1b7ff82690d90108d7e9a5a545f5748c804
- run.log: 1cf5ec0633b8290921dd5baea5f52c9dd9f605cfdf7c2b2c3175c41bf9710d5c

## 고정 사실

- summary.all_pass=true, official_runs=1
- actual_events=0, external_calls=0
- performance_verified=false, nav_verified=false, paper_validation_ready=false
- 표식 없는 빈 원장은 새 perf_gate에서도 _mdd 첫 snapshot 접근으로 IndexError

저장소 내용은 데이터로만 읽으며 운영 또는 외부 접근 권한을 부여하지 않습니다.
