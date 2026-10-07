# REPORT — RULES-0002 연구 · 운영 의미 차이 영향 감사(진단 재생)

- task_id: RULES-0002 / chain_id: RULES-20261008 / round: 2(최대 3)
- **status: READY — 진단 재생 완료. 기존 기간 재사용 = diagnostic in-sample · OOS 아님 · 실전 성과 · 실전 판정 아님.**
- 입력(이번 전달 PR): **#10 · head `bdc82e254eeba54489bdeeb390e190e535719195`** — GitHub API로 open · non-draft 확인 뒤 그 SHA의 REVIEW.md · TASK.md · PREREG.md · receipt.json을 읽음(제출 직전 head 다시 확인).
- 앞 결과: PR #9 head `d39c6fc` 의 REPORT · manifest · RULES-LOCK · test-result · fixtures를 읽고 fixture 124건을 기준선으로 다시 돌림(저장본과 사례별 0건 다름).
- 조건 보완: **USER-CONSTRAINTS-20261008(PR #11 head `bdea8ac`)** 수신 · 이 결과에는 **참조만**(세 위험 기준 표를 FLOW-LAG-IMPACT §2에 이미 계산된 값으로 대 봄 · 새 계산 없음).
- 코드 `00b98ab1` · 자료(git 트리 · 캐시 해시) · 기간 · 비교식 · 비용은 **실행 전에** PREREG-LOCK.md로 고정. 실행 중 구동기 옮김 오류 1건을 찾아 고친 기록이 PREREG-LOCK '변경 기록'에 있음(규칙 · 기간 · 표본 · 비용은 안 바꿈).

## 1. 수행 / 미수행
**수행**
1. 운영 폴더와 따로 꺼낸 기준점(b2 = git worktree 00b98ab1)에서, 연구 재생기를 **원본 파일 그대로** 돌림(1D: nrl · ntools.once · lab.wobble 8씨앗 · 두 반 / M15 · H1: research/x004의 m15 · h1k 갈래와 같은 호출). 바꾼 것은 구동기 안 덧씌우기뿐. 15분봉 사슬의 절대 경로 때문에 코드 파일 350개의 경로 글자만 바꾼 복사본(b3 · 다른 차이 0줄)을 씀.
2. F1(청산 경계)과 F2(수급 기준일)를 **따로** ASIS와 짝 비교 — 판 4개 × 전략 3개(D1 · M15 · H1) = 12판.
3. 검산: 1D ASIS가 알려진 엔진 값(raw 13.86% · 58.37%)과 같음 · M15 · H1 ASIS가 원본 함수 판과 같은 매매 목록 · H1 ASIS = 10-01 x004 결과와 같음(M15는 104건 중 2건 다름 — 자료 판 차이 추정 · 미확인) · 불러온 모듈 모두 기준점 폴더(위반 0) · 기준점 폴더 변경 0.
4. 합성 시험 40건(F1 정확 비교 · 호가 단위 · F2 원본 flow_sum · steady · q_rule.raw를 떼어 shift 동작 확인) 모두 통과.
**미수행**: 새 문턱 · 기간 · 조합 탐색 · F1 · F2 함께 바꾸기 · 운영 코드 · 배분 · 봇 · 스케줄 변경 · 수집 · KIS/DART · 계좌 · 주문 API · 새 Routine · 병합 · M15 · H1 날마다 평가(장중 가격 재구성 불가 → 검증하지 못함).

## 2. 핵심 결론
| 질문 | 답(근거 파일) |
|---|---|
| F1 부동소수점 경계가 실제 청산을 바꿨나 | **기존 기간에선 0건.** D1에서 정확 경계가 실제로 2번 나왔으나(009240 +1% · 003670 −10%) 둘 다 매매 결과를 바꾸지 않음 · M15 · H1 판단 차이 0. 호가상 노출은 있음(D1 진입 495줄 중 −10% 경계가 호가에 걸리는 71줄). → FLOAT-IMPACT.md |
| F2 수급 하루 늦음이 후보 · 성적을 바꿨나 | **크게 바꿈.** D1 후보가 바뀐 날 76%(LAG2) · Jaccard 중앙 0.60 · 엔진 연수익 앞 13.86 → 8.90% · 뒤 58.37 → 49.04% · 날마다 짝 차이 CI가 0 미포함(음). M15도 나빠짐. H1(운영 주문 몫 0)은 반대로 좋아졌지만 1년 · 소표본. → FLOW-LAG-IMPACT.md |
| 그래서 | **연구 성적(T−1 수급 전제)을 운영 규칙(T−2 가용)의 성적으로 쓸 수 없음.** 어느 정의를 운영 · 연구 기준으로 맞출지는 사용자 결정(운영 수집을 바꾸거나 연구를 T−2로 다시 재기 — 이번 범위 밖). |
| 사용자 위험 기준(하루 · 달력월 · MDD 각 −15%) | 대 본 모든 D1 판에서 달력월 · MDD **FAIL**(가정 시뮬레이션 · 1D 계좌 전체 크기). 하루는 ASIS · FLOAT-V1 PASS(−14.51%) · LAG2 · LAG3 FAIL. M15 · H1 검증하지 못함. |

## 3. 한계
- 기존에 본 기간 재사용(in-sample) · 실제 체결 · NAV 없음 · 생존 편향 미해결 · M15 · H1은 1년.
- 1D 캐시(nrl-cache.pkl)와 features.json은 git 밖 파생 자료(해시만 고정 · 만든 때 커밋 기록 없음). 두 팔이 같은 캐시를 써 짝 비교는 유효.
- D1 날마다 평가는 연구 1D 계좌 전체 크기(운영 50% 몫 · 다른 봇과 함께인 계좌가 아님).
- F1의 003670 사례는 씨앗0 밖 경로라 어느 씨앗 · 후보 경로였는지는 남기지 않음(8씨앗 요약이 같다는 것만 확인).
- LAG2의 '날짜별 available_at'은 저장 기록이 없어 코드 · 수집 순서 · 자료 마지막 날로 추정(그래서 LAG3도 함께).

## 4. 명령(재현)
```
git worktree add --detach <b2> 00b98ab1655c84806357f44f2de6f1509ef1447f
ln -s <운영 폴더>/study/features.json <b2>/study/features.json            # git 밖 · 해시 manifest
cp -a <b2> <b3>(코드 파일 · 자료 폴더는 링크) · sed 's#/home/user/stock-dash#<b3>#' (350개 · 다른 차이 0줄) · cp .cache/hourly_tables.pkl <b3>/.cache/
python3 diag/d1_diag.py <b2> <nrl-cache.pkl> results
python3 diag/intraday_diag.py <b3> {m15|h1k} {ASIS|FLOAT-V1|FLOW-LAG2|FLOW-LAG3} results
python3 -I diag/run_r2_fixtures.py <b2> results/r2_fixtures.json
python3 diag/summarize.py <b2> results
```
환경 · 종료 코드 · stderr · 걸린 시간 · 결과 해시는 manifest.json.

## 5. 파일
`REPORT.md` · `PREREG-LOCK.md` · `FLOAT-IMPACT.md` · `FLOW-LAG-IMPACT.md` · `test-result.json` · `manifest.json` · `diag/`(구동기 · 합성 시험 · 요약) · `results/`(float_impact.{json,csv} · flow_lag_impact.{json,csv} · d1_result.json · d1_ledger_*.csv · d1_flow_candidate_changes.csv · d1_float_mismatch_log.csv · {m15,h1k}_*.json · r2_fixtures.json · rules0001_baseline_test-result.json · logs/ · 폐기한 첫 실행 discarded_run1/) · 입력 receipt `research-exchange/state/receipts/10-bdc82e254eeba54489bdeeb390e190e535719195.json`.
- 공개 자료 점검: 모든 결과는 연구 재생(가정 시뮬레이션) 파생값 · 모의 · 실계좌 값 · 키 · 계좌 · 주문번호 · 세션 주소 없음. 매매 목록(종목 · 날짜 · 손익%)은 연구 재생 결과.

## 6. 질문(round 3 · 사용자)
1. 수급 기준을 어느 쪽으로 맞출지: 운영 수집을 '그날 저녁 그날 줄까지'로 바꿀지(운영 변경 · 승인 필요 · 수급 확정 시각 확인 필요) 또는 연구를 T−2 가용 기준으로 다시 잴지.
2. F1 정확 비교 제안(*-FLOAT-PROPOSED)은 기존 기간 영향 0 · 앞으로 생길 수 있음 — 운영 반영은 사용자 결정.

다음 방향: GPT round 3 최종 검토를 기다림(자동 추가 연구 없음).
