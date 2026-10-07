# PR #19 검토 — REPLAY-0002

- 입력 PR: `#19`
- 입력 head SHA: `1d295ee32e16e05bbed6fe41f60b8efe44106bf6`
- 감지 시각: `2026-10-08T08:25:55+09:00`
- 판정: `ACCEPTED_BLOCKED_WITH_PRIVACY_DEFECT`

## 결론

REPLAY-0002의 `BLOCKED_NEEDS_DATA` 판정을 채택한다. 이것은 전략의 기대값이 음수라는 판정이 아니라, 과거 495건을 미래정보 없이 다시 계산할 증거가 없다는 판정이다.

- 완전 재생 가능: `0/495`
- 신호 시점·available_at 성립: `0/495`
- model-fill 시가 성립: `0/495`
- Universe(t), 상장폐지·거래정지·신규상장: 전 행 MISSING
- 실제 비용 근거: `0/495`
- 관측 KIS 모의체결: 0건
- `PAPER_VALIDATION_READY=false`

## 독립 확인

1. PR #19는 open·non-draft·unmerged이며 입력 receipt의 PR #18/head SHA가 일치한다.
2. manifest가 선언한 11개 산출물을 현재 head에서 읽어 SHA-256을 독립 계산했고 **11/11 일치**했다. 1,274,213자 `COVERAGE.json`도 Git blob 전체를 읽어 확인했다.
3. field coverage 합계와 REPORT가 일치한다. F06은 MISSING 240 + UNTRUSTED 255 = 495, F12는 MISSING 19 + UNTRUSTED 476 = 495다.
4. TEST-RESULT는 결정론 2회, pnl 섞기, exit 교체의 진입측 비영향, 정적 pnl 미사용, 격리 검사를 통과했다고 기록한다.
5. 이번 환경에서는 기준 저장소의 전체 원자료를 실행환경으로 내려받지 않았으므로 55초 분류 실행 자체는 독립 재실행하지 않았다. 제출 코드·전체 coverage·hash는 확인했지만 실행 수치는 `submitted measurement`로 구분한다.

## 방법론적 제한

- git 경로의 최초 등장 시각은 rename/move 이전 이력을 자동 추적하지 않는다. 보고서도 MEAS-0001의 9월 9일과 이번 9월 22일 차이를 미해결로 밝혔다. 어느 쪽이어도 2017~2026 신호시점보다 늦다는 핵심 판정은 변하지 않는다.
- 격리 검사에서 운영 모듈 경로 판정이 `/home/user/stock-dash`에 고정돼 있다. 제출 실행 위치와 맞을 수 있으나 재사용 가능한 일반 격리 증거는 아니다.
- 기존 장부의 exit는 청산 재생 근거가 아니고, 29개 다중행 묶음은 부분청산 여부가 여전히 불명확하다.
- calm 2.1763은 전 기간 미래참조라 폐기 대상이지만, 대체 문턱을 이번 결과에서 선택하지 않았다.

## 개인정보 결함

PR 본문의 비공개 세션 주소는 검토 중 제거했다. 그러나 결과 head commit message에도 같은 비공개 세션 식별자가 이미 포함돼 있다. 불변 결과 브랜치를 강제 재작성하면 head SHA와 receipt가 바뀌므로 이번에 이력을 재작성하지 않았다. 이는 미해결 개인정보 결함이며 다음 제출부터 commit/PR metadata에 `Claude-Session` trailer를 넣지 않는다.

## 다음 단계

과거 495행을 보간하거나 성과를 계산하지 않는다. 다음 한 단계는 앞으로 수집될 자료가 `available_at`, 최초판·정정판, Universe(t), 체결·비용 증거를 잃지 않도록 **append-only 시점별 데이터 계약과 오프라인 검증기**를 만드는 것이다. API 호출·실제 수집·운영 변경은 아직 하지 않는다.

