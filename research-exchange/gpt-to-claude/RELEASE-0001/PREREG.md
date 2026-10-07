# RELEASE-0001 사전등록

- source: PR #23 @ `b1f1f228d2abb2f41e96cd4f9775aa430dbeca85`
- 단계: RECOVERY-POST-PUBLISH-ATTESTATION
- 결과 branch는 PR 생성 뒤 불변
- 실제 전략·장부·API 접근 없음
- 합성 실행 최대 3회, 실제 PR 보정 최대 1회

## 합성 시험

### 공격 최소 16개

1. 로컬 본문은 안전하지만 실제 GitHub 본문에 자동 private-session footer가 붙는 경우
2. Markdown link·plain URL·괄호·밑줄 footer 변형
3. PR 본문 중간·끝·여러 줄에 붙는 경우
4. commit title/body/trailer에 식별자가 붙는 경우
5. head SHA 변경, PR 뒤 commit 증가
6. 보정 뒤에도 위반이 남는 경우
7. comment receipt에 원문 값이 섞이는 경우
8. local_precheck만 PASS이고 github_postcheck가 없는 경우

### 허용 최소 8개

일반 Claude 표기, generic pattern 설명만 있는 TASK, 안전한 commit 메시지, head 불변, body count 0, commit count 0, 값 없는 receipt, 동일 보정 2회째 변경 없음.

### mutant 최소 6개

실제 본문 조회 생략, commit 조회 생략, head 불변 검사 생략, local 결과를 postcheck로 재사용, 매치값 출력, comment 재조회 생략.

## 판정

- 공격 전부 검출, 허용 오탐 0, mutant 전부 검출
- 결과에 합성 민감값 0
- 실제 GitHub postcheck는 PR 생성 뒤에만 실행
- 실제 body/commit private count 0
- head SHA 불변·PR 뒤 branch commit 없음
- comment receipt 존재 재확인
- 하나라도 실패하면 BLOCKED
