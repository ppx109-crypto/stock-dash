---
task_id: RULES-0003
chain_id: RULES-20261008
round: 3
max_rounds: 3
status: NEEDS_USER
source_pr: 12
source_head_sha: a61f033ecd16ba0976c955a93bfec70c7463ad53
execution_mode: review_acknowledgement_only
---
# 최종검토 접수 및 사용자 결정 대기
## 목적
REVIEW.md와 INDEPENDENT-CHECK.json의 감사 범위/미확인을 수신하고 자동 연구 체인을 종료한다. 이 문서는 다음 계산을 지시하지 않는다.
## 허용범위
- 이 GPT PR의 open/non-draft/head를 GitHub에서 확인하고 그 SHA의 REVIEW.md/TASK.md/receipt.json/INDEPENDENT-CHECK.json을 읽는다.
- 현재 작업 중인 동일 기존 세션에서 PR/head/읽은 파일/NEEDS_USER/추가 실행 없음만 접수 확인한다.
- 진행 중 사용자가 따로 승인한 작업은 중단하지 않는다. 이 체인 과제는 추가 실행하지 않는다.
## 금지범위
기존 결과 #12 브랜치 변경, 결과 PR 새 제출, 새 연구/계산/수집/API/계좌조회/주문/운영·배분·워크플로·인증 변경, 병합, 새 세션·탭·Routine, 새 threshold 탐색 및 OOS 재명명 금지.
모의 파생 자료 공개 허용은 PR #11의 비식별 allowlist 범위. 키/토큰/원본계좌응답/실계좌자료/비공개 세션 주소 공개 금지.
## 완료조건
기존 세션에서 실제 파일 읽기와 NEEDS_USER를 확인한다. 다음 실행 TASK를 만들거나 자동 완료 PR을 생성하지 않는다.
## 사용자 결정 대기
후속 한 단계 후보: 기존 모의 기록/캐시 provenance에 대한 가격·수급·현금·MTM 측정 계약 감사. 승인 전 시작하지 않는다. 운영 수집을 바꾸거나 높은 성과의 cutoff를 고르는 제안은 승인되지 않았다.
