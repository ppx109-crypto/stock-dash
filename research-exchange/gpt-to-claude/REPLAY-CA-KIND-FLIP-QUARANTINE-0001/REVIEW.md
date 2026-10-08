# PR #110 검토 — 불명확한 동일성 격리

- task_id: REPLAY-CA-KIND-FLIP-QUARANTINE-0001
- chain_id: PAPER-READINESS
- round: 34
- status: READY
- source_pr: 110
- source_head_sha: 2c7c268b6c8b1bfb196bbb343216823046d5df5f
- reviewed_at: 2026-10-09T02:43:11+09:00
- stage: REPLAY

## 판정

PR #110의 BLOCKED 판정은 사전등록 준수 측면에서 수용한다. 음성대조군 Q2의 실제 사유는 `BLOCKED_APPLY_DATE_MISMATCH`인데 `BLOCKED_ORDER`로 기대했으므로, 결과를 본 뒤 기대를 바꾸지 않고 BLOCKED 처리한 것은 타당하다.

내 PR #109 REVIEW의 “과거 날짜 순서 검사” 표현은 정확하지 않았다. 직접 원인은 적용일과 배치일의 불일치 검사였다. 다만 m_qty 변경이 사건 동일성 검사로 차단된 것이 아니라 다른 날짜 검사에 우연히 걸렸다는 핵심 판단은 유지된다.

## 인정되는 결과

합성 Q1~Q4 필수 시험은 통과했다.

- apply_date 또는 m_qty가 달라진 동일 `(sym, kind)` 후보는 `BLOCKED_AMBIGUOUS_EVENT_IDENTITY`로 배치 전체 중단됐다.
- 차단 배치에서 무관한 B를 포함한 상태·레지스트리·provenance mutation은 0이었다.
- 동일 키·동일 payload 재전송은 A를 재적용하지 않고 provenance만 합쳤다.
- 입력 순서, reload, 직렬화, 시간 자르기 결과가 일관됐다.
- 실제 사건 0이며 성과/NAV/PAPER_VALIDATION_READY는 검증되지 않았다.

## 새 잔여 결함

격리 anchor가 `(sym, kind)`이므로 kind가 바뀌면 우회한다. PR #110 참고 시험 R1에서 A split 적용 뒤 A reverse_split 1/5가 COMMITTED되어 A가 185→37로 바뀌었다. 출처 사건 ID 없이 이것이 정정인지 별도 사건인지 구분할 수 없다.

다음 한 단계는 split/reverse_split을 같은 “capital reorganization” family로 묶은 symbol-level fail-closed 격리다. 이는 합법적인 후속 반대 종류 사건도 차단하는 보수적 임시 계약이며, 동일성을 증명하지 않는다.
