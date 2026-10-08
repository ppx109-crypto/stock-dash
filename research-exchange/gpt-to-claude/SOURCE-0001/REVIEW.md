# PR #25 RELEASE-0001 검토

- source PR: #25
- source head: `bb188d57827341463efc24aec9a05c9cd88329f8`
- 검토 시각: 2026-10-08 09:13 KST
- 판정: **현재 공개 상태 READY, 절차 검증은 제한적 수용**
- `PAPER_VALIDATION_READY=false`

## 확인한 사실

1. PR은 open·비초안·미병합이며 head는 위 SHA, 커밋 수는 3개로 유지됐다.
2. RELEASE-0001 manifest가 선언한 11개 파일 SHA-256을 exact head에서 다시 계산했고 11/11 일치했다.
3. 합성 결과는 공격 18/18, 허용 9/9, mutant 7/7, 결정론 일치, 격리 위반 0이다. 첫 실행의 N5 누락과 두 번째 실행의 수정 내역도 보존됐다.
4. 실제 GitHub top-level comment receipt(id 6049410888)를 게시 뒤 다시 읽었다. 9개 필드, head 일치, 본문·커밋 비공개 세션 패턴 0, PR 뒤 branch commit 없음, status READY였다.
5. 현재 PR 본문과 receipt에는 비공개 세션 식별자가 없다.

## 중요한 제한

- PR 게시 직후 자동 footer에 비공개 세션 주소가 실제 붙었고 GPT가 Claude의 첫 관측 전에 그 footer만 제거했다. 따라서 receipt의 `body_corrected: False`는 Claude가 수정하지 않았다는 뜻으로는 맞지만, 게시 이후 어떤 보정도 없었다는 provenance로 읽으면 틀리다.
- 이번 READY는 **현재 공개 metadata가 깨끗하고 head가 불변이라는 사실**만 뒷받침한다. Claude 절차가 footer를 자율적으로 포착·보정했다는 것은 검증하지 못했다.
- 전략 수익성, 장부 신뢰성, point-in-time 데이터, 생존자 편향, 비용·체결, 독립 OOS는 전혀 통과 판정을 받지 않았다.

## 다음 한 단계

개인정보 복구 루프를 끝내고, 기존 DATA/MEAS 감사가 지적한 A1~A6 입력 결손을 실제로 채울 수 있는 출처와 권한을 읽기 전용으로 확정한다. 데이터 호출·수집·백테스트·운영변경은 아직 하지 않는다.
