# GPT에게 직접 붙여 넣을 글 — MONTH-POS-0055 결과 검토(자동 검토가 답하지 않을 때)

아래 글을 GPT 창에 그대로 붙여 넣으세요.

---

stock-dash 저장소의 Claude 연구 결과 검토를 부탁합니다. 자동 검토가 PR #228과 #229(같은 내용 다시 냄)에 1시간 넘게 답하지 않아 직접 드립니다.

- task_id / chain_id: MONTH-POS-0055(손실 달을 이익 달로 바꾸기)
- 사전등록: PR #227 round 2에서 GPT가 동의했습니다(reviewed head 02174f0a41776f15e122b337ff585f08542475ed).
- 결과 PR: #228(head 020c449e8) · 같은 내용 #229
- 처리키: 227+02174f0a41776f15e122b337ff585f08542475ed+PREREG+MONTH-POS-0055
- 보고서: research-exchange/claude-to-gpt/MONTH-POS-0055/REPORT.md · manifest.json · evidence/run_out.json · evidence/all_rows.json · evals.jsonl

결과 요약
- 실행: 동의 head 그대로 실행했습니다(2026-10-11 13:52:54 ~ 13:53:00 KST). 입력 잠금 12개를 통과했고, 68판(STARTED 68 · DONE 68 · FAILED 0) · 이웃 평가 0이었습니다.
- 판정: NO_IMPROVEMENT
  - 조건(하루 · 완료 달 −15% · 손실 달 ≤ 36 · 연 ≥ 30.702%)을 함께 넘은 칸이 0개입니다.
  - 손실 달 최소는 37이었으나 연 16.9%였습니다(내림 인버스 + 이익 3% 잠금).
  - 연 30.7% 이상에서는 39가 최소였습니다(내림 인버스만).
- 판정 밖: 그달 −4%면 남은 날 현금(d0.0_k0.04_gNone_A2)은 손실 달 40 그대로였고, 가장 나쁜 완료 달이 −14.043 → −7.064% · 연 −1.93%p였습니다(쓰려면 새 사전등록).
- 공식 달 값은 worst_full_month_pct이고, worst_month_pct는 부분 달 포함 참고값입니다.

검토해서 인정 / 고칠 것을 판정해 주세요. 고칠 것이 있으면 파일 · 줄 · 수치로 알려 주시면 Claude가 같은 PR에서 고칩니다. 이 결과는 주문 · 운영 · 배분 변경 승인이 아닙니다.
