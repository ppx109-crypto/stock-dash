# PR #118 검토 — REPLAY-CA-PRICE-BASIS-GATE-0001

- task_id: REPLAY-CA-QUOTE-BASIS-GATE-0001
- chain_id: PAPER-READINESS
- round: 38
- status: READY
- source_pr: 118
- source_head_sha: c8826304387ae99f92adf09bedc0b1997618d703
- reviewed_at_kst: 2026-10-09T03:25:54+09:00

## 판정

**합성 사건 가격기준 게이트 범위에서 READY**입니다.

- `RAW_UNADJUSTED` 사건만 기존 기업행위 경로에 들어갑니다.
- `ADJUSTED`·누락·빈 값·다른 문자열은 사건 mutation 전에 배치 전체가 차단됐습니다.
- 차단 7건에서 감시 상태 대입 0, 바뀐 칸 0, 해시 불변을 보고했습니다.
- PR #114 고정 fixture 11개는 다른 칸 0이었습니다.
- 공식 실행 1회, actual_events=0, external_calls=0입니다.

이 판정은 실제 가격기준 라벨·기업행위 입력·NAV·성과를 검증하지 않습니다. `performance_verified=false`, `nav_verified=false`, `paper_validation_ready=false`를 유지합니다.

## 주장·코드·실측 구분

- 주장: 사건 단위 가격기준 라벨이 기업행위 적용 전 fail-closed 경계를 제공합니다.
- 코드: `apply_batch` 첫 부분이 사건 라벨을 검사하고, 합성 fixture에서 mutation 선행이 없었습니다.
- 실측: 실제 사건·실제 시세·실제 포지션은 0입니다. P2의 5배 NAV 변화는 고정 합성 음성대조입니다.

## 확인된 잔여 결함

사건 게이트만으로는 장부와 시세 공급의 기준 불일치를 막지 못합니다.

- `process_day`는 `apply_batch` 뒤 `quotes`를 장부 가격에 무조건 덮어씁니다.
- 사건이 `RAW_UNADJUSTED`로 잘못 라벨링되면 게이트를 통과합니다.
- 그 뒤 수정주가가 덮이면 P2 음성대조처럼 NAV가 387,020에서 1,935,100으로 5배 왜곡될 수 있습니다.
- 차단된 사건 뒤에도 현재 합성 `process_day`는 quote 루프와 snapshot 생성을 계속합니다.

따라서 다음 단계는 사건 게이트를 확장하는 것이 아니라, 하루 처리의 가장 앞에서 **시세 배치 가격기준**을 검사해 사건·시세·스냅숏을 함께 차단하는 독립 경계입니다.

## 사전등록 메모

사전등록 뒤 공식 실행 전에 공통 A1 fixture에 RAW 라벨 한 줄을 추가한 사실은 공개됐습니다. 이는 사전등록 계약을 코드에 맞춘 수정이고 공식 실행은 그 뒤 1회였습니다. 이번 합성 READY를 뒤집지는 않지만, 실제 라벨 provenance 근거로는 사용하지 않습니다.
