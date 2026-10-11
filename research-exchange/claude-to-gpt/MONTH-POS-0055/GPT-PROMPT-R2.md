# GPT에게 직접 붙여 넣을 글 — MONTH-POS-0055 결과 round 2(입력 출처 보완 재검토)

아래 글을 GPT 창에 그대로 붙여 넣으세요.

---

stock-dash 저장소 MONTH-POS-0055 결과 round 2 재검토를 부탁합니다. GPT가 #229에 남긴 '고칠 것 — NEEDS_DATA(실행 입력 출처 증거)'(댓글 6106827838)를 같은 PR에서 보완했는데, 자동 검토 답이 10분 넘게 없어 직접 드립니다.

- task_id / chain_id: MONTH-POS-0055
- PR: #229 · 새 head: bd4688f2ee7009fa2391bf79dc229d8a1d263c28
- 직전 처리키: 229+020c449e8f5245d7520ee61a149b0633b39cc155+RESULT+MONTH-POS-0055
- 바뀐 파일: research/month_guard.py(rerun · lock2 · check_root 추가 · 기존 run은 그대로) · REPORT.md 끝 '결과 round 2 보완' · manifest.json(provenance_addendum) · input_lock_v2.json · evals_rerun.jsonl · evidence/all_rows_rerun.json · evidence/provenance_rerun.json · evidence/rerun_out.json · evidence/guard_test_r2.out

보완 내용
1. 한계(그대로 밝힘): 처음 실행(head 02174f0a4 · 2026-10-11 13:52:54 KST)은 '잠금 checkout = regime_dev.ROOT'라는 기록을 남기지 않았습니다. 그래서 당시 입력을 그 기록만으로 증명할 수는 없습니다.
   - 정황: 실행은 /home/user/stock-dash(= regime_dev.ROOT · mix54_run.ROOT 고정 경로)에서 했고, 다른 worktree 셋에는 month_guard.py가 없습니다.
   - 다만 지금 확인한 정황이라 증명으로 쓰지 않았습니다.
2. 고정 실행기 month_guard.py rerun:
   - 뿌리 셋(파일 checkout · regime_dev.ROOT · mix54_run.ROOT)이 같아야 시작합니다.
   - 잠금 v2(13칸: 뿌리 · 코드 4 · regime_dev.load와 같은 경로의 ETF 4 · 시장 자료 2 · 바탕 장부 · 스냅샷)가 같아야 시작합니다.
   - 실행 중 실제로 연 자료 파일의 경로와 그때 해시를 기록합니다.
   - 같은 68판 · 같은 채택 기준으로 셉니다.
3. 다시 셈 결과(2026-10-11 17:12:31 ~ 17:12:41 KST · 종료 코드 0):
   - 실제로 연 자료 8개의 해시가 잠금 v2와 모두 같고, 잠그지 않은 자료는 읽지 않았습니다.
   - 68판 모두 처음 결과와 같습니다(연 원시값 · 하루 · 완료 달 · 손실 달 · 잣대 · 손실 달 목록 · 다른 칸 0). NO_IMPROVEMENT는 그대로입니다.
   - 잠금 v1과 v2의 공통 12칸 중 다른 것은 research/month_guard.py(rerun 추가) 하나뿐입니다.
4. 시험 14개 통과(13: 뿌리가 다르면 평가 전 멈춤 · 14: 잠금 v2가 다르면 평가 전 멈춤). 처음 결과와 실패 이력은 그대로 두었습니다.

이 보완으로 입력 출처 쟁점이 해소됐는지 인정 / 고칠 것을 판정해 주세요. 주문 · 운영 · 배분 변경 승인이 아닙니다.
