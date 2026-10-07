# 결과 PR 제출·감지 안정화 규칙

## 목적
GitHub webhook가 결과 PR을 즉시 감지하더라도 제출 브랜치의 head가 계속 바뀌면 검토 기준이 이동하고 중복 실행처럼 보인다. 아래 규칙으로 제출과 검토의 경계를 고정한다.

## Claude 제출 규칙
1. REPORT·manifest·receipt를 한 커밋에 완성한 뒤 `[클로드 결과]` 비초안 PR을 연다.
2. PR을 연 뒤 결과 브랜치는 불변으로 둔다. 연구 타이머, 운영 코드, 다른 문서, 추가 실험을 같은 브랜치에 커밋하지 않는다.
3. PR 번호를 미리 알 수 없으므로 receipt의 `result_pr`은 `null`이어도 유효하다. 번호를 채우기 위한 제출 후 커밋을 만들지 않는다.
4. 정정이 꼭 필요하면 현재 PR 본문에 정정 사유를 적고, REPORT·manifest·receipt만 한 번 보정한다. unrelated file이 섞이면 제출 오염으로 본다.
5. 후속 연구는 새 브랜치와 새 PR에서 수행한다.

## GPT 검토 규칙
1. `opened`·`synchronize` webhook를 받으면 실제 PR 상태, draft 여부, 현재 head SHA를 조회한다.
2. `PR 번호 + head SHA`를 검토 단위로 삼고 receipt로 중복을 막는다.
3. 발행 직전 head를 다시 조회한다. 바뀌었으면 현재 patch를 다시 읽고 동일 내용이면 기존 응답 PR의 source SHA와 receipt만 갱신한다.
4. 결과 내용이 달라졌거나 unrelated file이 섞였으면 다음 연구를 실행하지 않고 BLOCKED/NEEDS_USER로 보고한다.
5. 감지 시점과 검토 완료 시점을 구분해 사용자에게 보고한다.

## 현재 상태
PR #5는 개설 직후 receipt 보정과 같은 브랜치의 후속 작업으로 head가 여러 번 바뀌었다. webhook는 개설 약 11초 뒤 정상 감지했으나 검토 기준 SHA가 이동해 최종 회신이 늦어졌다. PR #6에서 현재 head를 다시 고정하고 검토 receipt를 추가했다.
