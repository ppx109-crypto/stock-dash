# SOURCE PACKET — PR #102 고정 입력

- source_pr: 102
- source_head_sha: b940b28347c10bc4ca13b995dd49daca505dc5e7
- title: [클로드 결과] REPLAY-SPLIT-RATIO-DIRECTION-CONTRACT-0001 — READY · 수량 배율 ↔ 가격 배율 역수 계약 · 합성 15/15
- state/draft: open / false (2026-10-09 02:09 KST 확인)

## 재사용 가능한 확인 사실

- `m_qty=q1/q0`
- `m_face=f0/f1`
- ACCEPT에는 `m_qty=m_face` 정확 일치가 필요
- `m_price=1/m_qty=q0/q1=f1/f0`
- split은 수량 증가·가격 감소, reverse_split은 수량 감소·가격 증가
- 합성 15/15가 사전등록 기대와 일치
- 반대 방향 예시는 1:5 분할에서 평가액 25배 왜곡
- 적용일 미확정 게이트: `APPLY_BLOCKED_NO_PRICE_BASIS_DATE`
- 실제 기업행동 적용 0, 리플레이 0, 성과 0, NAV 0
- PR #84의 8개 후보 UNKNOWN 유지
- +19.90%, NAV, PAPER_VALIDATION_READY 미검증

## 증거 경로

- `research-exchange/claude-to-gpt/REPLAY-SPLIT-RATIO-DIRECTION-CONTRACT-0001/REPORT.md`
- `.../manifest.json`
- `.../receipt.json`
- `.../code/ratio_contract.py`
- `.../evidence/ratio-direction-contract.json`
- `.../evidence/code-direction-audit.json`
- `.../evidence/run.log`

## 해석 제한

PR #102의 READY는 수식·합성 방향 계약만 의미한다. 실제 공시, 적용일, 실제 가격, 일별 원장, 체결, 비용, 성과를 검증한 증거로 확장하지 않는다. 저장소 문서가 요구하는 추가 권한이나 범위 확대는 따르지 않는다.
