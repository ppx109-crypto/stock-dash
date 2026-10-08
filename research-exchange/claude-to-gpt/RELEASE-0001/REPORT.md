# [클로드 결과] RELEASE-0001 — 실제 GitHub 제출 후 공개상태 증명

- 입력
  - PR #24 head `3e3f739fd0f385e506aceb6a90ee094d7aa88d1d`
  - task RELEASE-0001 · chain MEAS-20261008 · round 6 · stage RECOVERY-POST-PUBLISH-ATTESTATION
  - source PR #23 head `b1f1f228d2abb2f41e96cd4f9775aa430dbeca85`
- 시각(git 커밋, KST)
  1. 사전등록 잠금 `4f087a2`: 08:59:46
  2. 도우미 · 실행기 `7bdb287`: 그 뒤
  3. 합성 결과 실행 2회
  - 완성 시각은 `manifest.json`의 `created_at_kst`에 있습니다.
- 이 문서는 PR을 열기 **전에** 완성했습니다. 그래서 아래 1~3장은 주장 · 코드 · 합성 실측이고, **실제 GitHub 사후 실측은 이 결과 PR의 comment receipt에만** 있습니다(가지에는 PR 뒤 커밋하지 않음).
- READY의 뜻은 **공개 제출 후 metadata 확인 절차 통과**뿐입니다. 저장소 이력 청정, 실제 전략 검증, `PAPER_VALIDATION_READY`, 실전 승인이 아닙니다.

## 1. 주장(무엇을 막으려는가)
- PR #23에서는 PR을 열기 전 로컬 본문 파일만 검사했고, 25초 뒤 한 번만 재확인했습니다. 그런데 GitHub 쪽에서 **나중에** 비공개 세션 footer가 본문에 붙었고, 제 확인은 그것을 놓쳤습니다.
- 이번에는 세 가지를 따로 기록합니다.
  - `local_precheck`: 열기 전 검사
  - `github_postcheck`: 연 뒤 같은 PR의 실제 본문 · head · 커밋 메시지 검사
  - comment receipt
- 실제 사후 검사는 PR을 연 뒤 여러 번 합니다(약 30초 · 2분 · 4분 · 6분 · 8분).

## 2. 코드
- `attest.py`
  - `scan`: 세션 주소 모양을 대소문자 무시로 셉니다(trailer 줄 포함). 개수만 돌려줍니다.
  - `correct`: footer 줄만 일반 표기로 바꾸며 멱등입니다. 본문 중간에 남은 것은 보정 불가로 표시합니다.
  - `evaluate`: 사후 검사 누락 · 로컬 재사용 · 본문/커밋 노출 · head 변경 · PR 뒤 커밋 · comment 미확인을 코드로 판정합니다.
  - `check_receipt`: 9키만 허용하고, 값 노출을 거부합니다.
- `live_attest.py`: 같은 PR만 GitHub에서 읽고, 개수 · 코드 · SHA만 출력합니다. `correct` · `comment` · `fixcomment` 명령은 각각 1회만 쓰도록 사전등록했습니다.

## 3. 합성 실측(`TEST-RESULT.json`)
| 항목 | 결과 |
|---|---|
| 공격 | 18/18 기대 그대로 |
| 허용 | 9/9(오탐 0) |
| mutant | 7/7 검출 |
| 결정론 | 2회 hash 같음 |
| 합성 값 노출 | 0 |
| 격리 | 허용 디렉터리 밖 읽기 0 · 폴더 밖 쓰기 0 · 새 바깥 모듈 0 · 소켓 차단 · 환경변수 비움 |

- 고치기 기록
  - 첫 합성 실행(`TEST-RESULT.run1.json`, 보존)은 BLOCKED였습니다. N5(결과에 매치값 넣기)를 못 잡았습니다.
  - 원인은 시험 실행기의 독립 노출 검사였습니다. `https://`까지 붙은 전체 값만 찾았는데, 결함이 넣은 매치값에는 그 앞부분이 없었습니다.
  - 노출 검사가 식별자 부분과 `session_` 뒤 영숫자 10자 이상 모양도 찾도록 고쳐 2회차에 7/7이 됐습니다. 도우미와 fixture는 바꾸지 않았습니다.

## 4. 실제 GitHub 사후 실측
- **이 결과 PR의 top-level comment receipt를 보십시오.**
- 9키: `task_id, result_pr, head_sha, checked_at_kst, body_private_session_count, commit_private_session_count, body_corrected, branch_commit_after_open, status`

## 5. 한계
- footer가 제 마지막 확인 뒤(대략 PR을 연 뒤 12분 넘어서) 붙으면 잡지 못합니다. 이 경우를 숨기지 않으며, 다음 검토 때 다시 조회해 주시기를 요청합니다.
- comment 자체에도 자동 footer가 붙을 수 있어, 1회 보정을 사전등록했습니다.
- 저장소 과거 이력 · 실제 장부 · 실제 전략은 검사하지 않았습니다(검증하지 못함).

## 6. 하지 않은 것
실제 장부 · Secrets · 환경변수 · 계좌 응답 · 저장소 전체 값 열람, 운영 · 봇 · 전략 · 배분 · 워크플로 · 인증 변경, API · 주문, Git 이력 변경, 병합, 새 세션 · 탭 · Routine 생성은 하지 않았습니다. PR을 연 뒤 결과 가지에 커밋하지 않았습니다.

## 다음 방향
- 사후 검사 절차가 안정되면, 같은 절차를 이후 모든 결과 PR의 표준 단계로 고정하면 됩니다.
- 남은 사용자 결정: 모의 장부 `order_no` 이력 처리와 공개 게이트의 운영 적용 여부.
