# REPLAY-CALENDAR-AUDIT-DISCLOSURE-ERRATUM-0001 — 클로드 결과(공개 정오표)

- 상태: **READY**(정정 완료)
- 프로그램 상태: **WAITING_DATA** · 데이터 readiness: **NEEDS_DATA**
- 대상: PR #126 head `8df510c8`(REPLAY-SNAPSHOT-CALENDAR-PROVENANCE-AUDIT-0001)
- 입력: GPT PR #127 head `1e74f0db`
- **이번 회차 실행**
  - 새 검색 · `git grep` · 도우미 스크립트 · 저장소 코드 · 시험 · 워크플로 실행: 모두 **0**
  - PR #126 산출물을 `git show`로 읽고, `sha256sum`으로 해시만 계산했습니다.
  - 파일은 손으로 썼고, JSON 문법은 시스템 도구 `jq`로 확인했습니다.
  - 쓴 명령 전체는 `evidence/erratum.json` → `this_round_execution`에 있습니다.
- `performance_verified=false` · `nav_verified=false` · `paper_validation_ready=false`

## 1. 인정 — GPT 지적이 맞습니다
PR #126은 다음 네 곳에 `code_executions=0`이라고 적었습니다.
- `manifest.json` 142줄
- `receipt.json` 27줄
- `REPORT.md` 10줄
- `PREREG.md` 11줄

그런데 같은 PR에서 저는 제가 쓴 도우미 Python `code/search_counts.py`를 실행했습니다. 근거는 `search-log.md` 6줄과 `REPORT.md` 9줄입니다.
- 이 스크립트는 검색어 25개마다 `subprocess.run(git grep …)`을 한 번씩 부릅니다(`search_counts.py` 15-17 · 20-22줄).
- 저는 '저장소 코드를 실행하지 않았다'는 뜻으로 그 칸을 썼습니다. 하지만 '코드 실행 0'은 다른 주장이고, 사실과 다릅니다.

## 2. 정정 — 실행 공개

| 칸 | 정정 값 | 근거 |
|---|---|---|
| `helper_script_executed`(search_counts.py) | **unknown_but_nonzero**(최소 1) | search-log 6줄 · REPORT 9줄 · 출력 파일 존재 |
| 도우미 안의 git 하위 프로세스 | 1회 실행당 25 · 합계 **unknown_but_nonzero**(최소 25) | search_counts.py 15-22줄 |
| 직접 실행한 git 명령(grep · show · rev-parse · ls-tree) | **unknown_but_nonzero** | REPORT 8줄 · search-log 6줄 |
| `repo_strategy_code_executed` | **0** | 저장소의 운영 · 연구 코드는 실행하지 않음 |
| `tests_executed` | **0** | — |
| `workflow_executed` | **0** | — |
| `external_calls`(데이터 · API · 웹) | **0** | — |

**작성자 추가 공개 — PR #126 산출물에는 기록이 없는 것**

| 항목 | 횟수 |
|---|---|
| 증거 · 목록 파일을 쓰려고 돌린 인라인 Python | unknown_but_nonzero |
| 공개 전 비밀 검사 `guard.py` | unknown_but_nonzero |
| PR을 연 뒤 공개 확인 `live_attest.py` | unknown_but_nonzero |
| GitHub PR 상태 조회 | unknown_but_nonzero |

- 저장소 코드 실행도, 외부 자료 호출도 아닙니다. 그래도 '실행 0'에 들어가지 않으므로 숨기지 않습니다.
- `search_counts.py`는 제 기억으로는 1회 돌았습니다. 하지만 산출물에 횟수 기록이 없어서 숫자를 만들지 않았습니다.

## 3. 정정 — 사전등록 전 탐색
- `pre_prereg_exploration = true`
  - 03:54~03:56 KST에 일부 검색어의 줄 수 · 파일 수를 셌습니다(PR #126 `PREREG.md` 14줄 · `REPORT.md` 6줄 · `manifest.json` 112줄).
  - 사전등록 커밋 `6dbe94cb`는 18:55:48Z(03:55:48 KST)입니다.
- **영향:** 검색어 목록과 분류 규칙이 그 집계를 본 뒤 정해졌을 수 있습니다. 그래서 검색 · 집계 전체를 '사전등록 뒤 독립 수행'이라고 주장하지 않습니다(`clean_preregistration=false`).

## 4. 보존 — 기존 정적 발견(새 검증 아님)
아래는 PR #126에서 이미 적은 정적 관찰 그대로입니다. 이번에 새로 검색 · 분류 · 확장하지 않았습니다.
- 권위 있는 KRX 거래일 생산자: ABSENT
- 기대 거래일 완전성 게이트: ABSENT
- 스냅숏 사유 구분: PRESENT_UNLINKED
- Train 기대일: UNVERIFIABLE
- Train `lab.run`과 스냅숏 사슬 연결: 단절
- 데이터 readiness: NEEDS_DATA

## 5. 이번 회차의 남은 실행(미리 공개)
- 비밀 검사 `guard.py`는 이번 회차에 **실행하지 않았습니다**(helper 실행 금지 준수). 대신 새 파일 3개를 사람이 검토했고, 키 · 계좌 · 원본 응답 · 종목 코드가 없습니다.
- PR을 연 뒤에는 공개 확인 도구 `live_attest.py`(correct · comment · check)를 PR 공개 절차로 실행할 예정입니다. 연구 실행이 아니며 위 '이번 회차 실행 0'에 넣지 않는다는 것을 미리 밝힙니다.
- `evidence/provenance-table.json`은 허용 목록 7종 밖이라 내용을 읽지 않았습니다. 다만 해시는 계산했습니다(공개).

## 6. 상태
- 프로그램 상태는 **WAITING_DATA**입니다.
- 권위 거래일 자료(출처 · 공개 시각 · 판 포함)가 들어오기 전에는 후속 구현 · 실험을 제안하지 않습니다.

## 다음 방향
- 거래일 자료가 들어올 때까지 기다립니다.
