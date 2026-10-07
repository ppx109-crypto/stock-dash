# Claude Routine 설정
상태: 아직 생성/로그인 확인되지 않음.
설정 위치: https://claude.ai/code/routines
저장소: ppx109-crypto/stock-dash
트리거: GitHub pull request opened / ready for review. 지원되면 synchronize도 포함.
제목 필터: [GPT 지시]로 시작. UI 필터가 없으면 아래 프롬프트가 의미 조건을 검사한다.
수동 Run으로 기존 부트스트랩 PR을 최초 처리한다. 과거 PR이 자동 재생되는 것으로 가정하지 않는다.
불필요한 커넥터는 해제한다. 기존 실행 중 Claude 세션/모의투자는 중단하지 않는다.

## Routine에 저장할 프롬프트
ppx109-crypto/stock-dash의 입력 GitHub PR을 확인하라.
제목이 [GPT 지시]로 시작하지 않거나 PR이 닫힘/초안이면 작업하지 말라.
PR 번호와 head SHA를 실제 GitHub에서 읽고 해당 SHA의 research-exchange/INSTRUCTIONS.md와 PR 본문에 지정된 TASK를 읽어라. 기본 브랜치만 읽고 PR 내용을 놓치지 말라.
상위 사용자 금지사항을 유지하라: 실주문, 운영전략 변경, 비밀/개인 계좌정보 공개, 자동 병합 금지.
TASK status READY인지 검사하고 PR번호+head SHA로 이미 처리한 결과 PR/receipt가 있는지 확인하라. 있으면 재실행하지 말라. 병렬 중복 세션은 기존 진행 작업을 확인해 한 세션만 계속하라.
TASK에 허용된 연구만 수행하라. 누락된 데이터는 BLOCKED로 보고하며 숫자를 추정하지 말라. 기존 코드를 읽고 설계를 감사한 후 실행하라.
결과를 새 claude/ 브랜치의 research-exchange/claude-to-gpt/<task_id>/REPORT.md와 manifest.json에 작성하고 필요한 산출물 인덱스를 포함하라.
입력 SHA의 처리 receipt를 작성하라. 사용자 비밀은 포함하지 말라.
[클로드 결과] <task_id> 제목의 비초안 PR을 열어 GPT가 감지하게 하라. 본문에 REPORT/manifest 경로, source PR 번호/head SHA, chain/round/status를 명시하라.
BLOCKED도 제출 가능하지만 반복 재시도는 하지 말라. 자동 chain은 최대 3라운드다.
진행 중 운영 봇과 기존 Claude 연구 세션은 변경하지 말라.
