# GPT ↔ Claude 연구 교환
공동 작업 경로. 기존 ai-handoff와 현재 진행 중 연구/모의투자는 보존한다.

## 제출과 감지
- GPT → Claude: gpt-to-claude/에 작업지시를 작성하고 제목이 [GPT 지시]로 시작하는 PR을 연다.
- Claude → GPT: claude-to-gpt/에 완료 보고서와 manifest를 작성하고 제목이 [클로드 결과]로 시작하는 비초안 PR을 연다.
- 단순 main 파일 업로드는 GPT 이벤트 감지 대상이 아니다. PR 제출이 필수다.
- 감지 → 해당 PR head SHA에 고정하여 읽기 → 근거 검토 → 검토문 및 다음 지시 PR 작성.
- 자동 병합, 실계좌 주문, 운영전략/배분 변경은 하지 않는다.
- Claude Routine의 GitHub 트리거는 별도 연결해야 한다. 문서가 있다는 이유로 자동화 완료로 간주하지 않는다.

## 경로
- INSTRUCTIONS.md: 공통 계약
- CLAUDE-ROUTINE.md: 클로드 자동화 설정 및 프롬프트
- gpt-to-claude/: 검토 후 발행하는 작업지시
- claude-to-gpt/: 클로드 결과
- work/: 연구 산출물 인덱스
- state/: 자동화 설정 및 중복처리 상태
