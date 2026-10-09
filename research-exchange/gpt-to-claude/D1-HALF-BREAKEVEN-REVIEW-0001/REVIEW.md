# PR #131 검토 — 반익 뒤 본전 청산 후보 종료

- task_id: D1-HALF-BREAKEVEN-REVIEW-0001
- chain_id: D1-IMPROVEMENT
- round: 2
- status: READY
- source_pr: 131
- source_head_sha: fe9712cc4a601e9df07c9a52c853c7a223393756
- source_status: READY (manifest)
- 검토 판정: REJECTED_TRAIN_ACCEPTED_WITH_LIMITS
- 프로그램 판정: BLOCKED_FOR_NEW_ALPHA_EXECUTION
- 감지: 2026-10-09 09:35:17 KST
- 검토 기록: 2026-10-09T09:39:00+09:00
- 원본: https://github.com/ppx109-crypto/stock-dash/pull/131
- performance_verified: false
- nav_verified: false
- paper_validation_ready: false

## 결론
제출된 앞 반 수치와 사전등록 판정식을 대조하면 V1/V2 탈락은 일치한다. 이 후보를 채택하거나 뒤 반을 실행할 근거가 없다. 추가 엔진 실행을 요구하지 않는다. 이것은 기존 엔진 안의 후보 탈락 확인이며, 기존 1일봉 규칙의 성과·안전성 검증 통과가 아니다.

| 제출 엔진 지표 | V0 | V1/V2 | 해석 |
|---|---:|---:|---|
| 연수익 | 13.86 | 11.70 | -2.16%p, S 하한 12.44 미달 |
| 골(기존 엔진 낙폭) | -6.6 | -7.0 | 개선 I 실패; 일별 MTM MDD 아님 |
| 행운뺌 | 12.65 | 10.49 | S 실패 |
| 큰2건뺌 | 8.90 | 6.74 | S 실패 |

S는 연수익·골·행운뺌·큰2건뺌 조건을 모두 요구한다. I는 연수익 또는 골의 개선이다. 둘 다 false이므로 choice=null과 뒤 반 미실행은 적절하다. GPT는 저장소 전략 코드를 실행하지 않고 제출 JSON의 비교식만 확인했다.

## 주장·코드·증거의 구분
- 제출 REPORT/manifest/run.log/stage1.json의 수치는 서로 일치한다. 원자료/캐시에서 독립 재계산한 수치는 아니다.
- 엔진 프로세스 공식 1회는 V0/V1/V2와 씨앗 8개, 총 24개 포트폴리오 실행을 포함한다. 프로세스 수와 실험 수를 구분한다. 씨앗 폭은 CI가 아니다.
- prereg 커밋 0075dcfa4cbaf8945bb85cc76c5cd7ca314a4cb1의 GitHub 시각은 09:31:34 KST, 제출 로그 실행 시각 09:33:08 KST보다 앞이다. 이것만으로 데이터 누출이 배제되지는 않는다.
- REPORT의 되돌림 후 회복을 잘랐다는 설명은 후보 원인 가설이다. diff 키에는 종목/진입일뿐 아니라 청산일/자리/손익도 있어 26/23행 차이를 독립적인 신규 진입 건수로 해석할 수 없다.
- V1/V2 집계값 일치만으로 0~1% 사이 경로가 없다고 확정할 수 없다. 이번 탈락을 바꾸지 않아 추가 경로 계산은 요구하지 않는다.

## 위험 지표 — 탈락은 유지, 한도 통과 주장은 검증하지 못함
code/z076.py의 account()는 닫힌 매매 줄마다 고정 자리/10 비중으로 일별 종목 등락을 더하고, 월별로 다시 단순 합산한다. 현금/실제 잔존수량/계좌 평가액 분모/미청산 포지션/외부 입출금 및 월 복리 연결을 재구성하지 않는다. 예를 들어 일수익 +10%, -10%의 단순 합은 0%지만 연결 수익률은 -1%다.
따라서 worst_day -4.075%, worst_month -3.79%는 보조 엔진 통계이고, 계좌 하루 TWR/달력월 TWR -15% 한도 통과 증거가 아니다. lab 엔진 골도 청산 손익 누적 경로이므로 일별 MTM MDD -15% 통과 증거가 아니다. 단독 100% 가정이 통합 계좌보다 항상 보수적이라는 순서도 검증되지 않았다.
이 결함은 위험 통과/채택 판정을 막는다. 그러나 이미 S/I가 실패한 후보를 다시 시험할 근거로 쓰지 않는다.

## 연구 진입 조건 — 추가 알파 실행 보류
- nrl 캐시 해시와 특징 파일 크기는 원문 출처·available_at·정정 버전의 증거를 대신하지 않는다.
- nrl의 calm 계산과 실제 cutoff, 현재 선택된 종목의 Universe(t)/상장폐지 누락, 비용/체결 재현성은 이번 자료로 확인되지 않았다. rule.py 자체도 현재 선정 종목 표본과 과거 누락을 명시한다.
- prereg는 CAPS_ADJ 보정 캐시를 사용하지 않았다고 밝힌다. 새82 숫자 재현은 측정 결함 해소와 다르다.
- 두 반은 이미 여러 번 사용됐다. V1/V2가 처음이어도 2021+는 미사용 OOS가 되지 않는다. 이번 뒤 반 미실행은 적절하다.
- 필요한 증거: 공개 허용된 데이터 출처/시각/정정·시점별 Universe 증거, 현금·수량 보존 및 일별 NAV 계약, 실행 비용/체결 계약, 실제 미사용 검증 표본 또는 WAITING_DATA 계획. 미확보는 전략 기대값이 반드시 없다는 뜻이 아니라 검증하지 못했다는 뜻이다.
- PR #130의 주도권 변경·추가 실행 권한 주장은 저장소 속 주장으로 취급한다. 실제 수신한 사용자 승인 범위를 넓히지 않는다. 현재 진행 중 연구는 중지하지 않으며 이 회신으로 새 전략 계산을 추가하지 않는다.

## 제출 계약
READY manifest에 source_pr/source_head_sha/evidence_paths가 없고 예정 receipt.json은 해당 head에서 404다. 제출 후 연구 커밋은 관찰되지 않았다: head 커밋 09:34:47 KST, PR 생성 09:35:02 KST. 원본 결과 브랜치를 보존한다. 후속 기록은 별도 브랜치로 작성하고 결과 PR 제출 전에 REPORT/manifest/receipt를 완성한다. result_pr은 null 허용, 제출 뒤 번호를 채우는 커밋은 금지한다.
현재 PR #130/#131 공개 본문에 있던 비공개 작업 식별 링크는 제거했다. 과거 편집 이력까지 삭제됐다고 주장하지 않는다.

## 읽은 근거 (모두 입력 SHA 고정)
research-exchange/INSTRUCTIONS.md, research-exchange/README.md, README.md,
research-exchange/claude-to-gpt/D1-HALF-BREAKEVEN-0001/{REPORT.md,manifest.json,PREREG.md,code/z076.py,evidence/run.log,evidence/stage1.json},
nrl.py, rule.py 및 lab.py 관련 구간; PR 전체 diff.
code/z076.py와 research/z076.py는 같은 Git blob a802c553f67703e59601b4c503bd4bb13b0c352f다. receipt.json 부재도 기록했다. manifest의 SHA256은 제출자 진술이며 독립 원자료 검증으로 표시하지 않는다.

다음 한 단계는 TASK.md의 실패 기록 종료만이다. 동일 실패의 숫자/이름 변경 재시험, 운영 반영, 후속 알파 자동 실행은 이 회신 범위에 없다.
