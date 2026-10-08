# PR #116 검토 — REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001

- task_id: REPLAY-CA-PRICE-BASIS-GATE-0001
- chain_id: PAPER-READINESS
- round: 37
- status: READY
- source_pr: 116
- source_head_sha: dc4335554b45ba8f257596acab44a0f6d2e985ff
- reviewed_at_kst: 2026-10-09T03:17:15+09:00

## 판정

**제한적 READY**입니다. 이는 PR #116의 정적 인벤토리·TRACE·GAPS가 사전등록된 완료조건을 충족했다는 뜻일 뿐, 실제 기업행위 입력이나 NAV/성과가 검증됐다는 뜻이 아닙니다.

- 고정 14개 검색어: 3,025행, 미분류 0
- 5개 필드 TRACE: 모두 첫 단절점 존재
- 9개 GAPS: PRESENT_VERIFIED 0, CONFLICTING 4, ABSENT 1
- actual_events=0, external_calls=0, code_execution=0
- performance_verified=false, nav_verified=false, paper_validation_ready=false

## 주장·코드·실측 구분

- 주장: PR #116은 실제 일봉이 수정주가이고 기업행위 게이트가 원주가 장부를 가정하므로 직접 연결 시 이중 조정 위험이 있다고 결론냈습니다.
- 코드 근거: `broker_kis.py:300-312`의 `FID_ORG_ADJ_PRC='0'`, `collect_prices.py:19,124`, `caps.py:100`, PR #114 게이트의 수량·가격 배수 적용부가 제시됐습니다.
- 실측: 실제 사건, 실제 Train 연결, 실제 NAV 재생은 모두 0입니다. 그러므로 이 단계에서 성과·유효성·실제 이중 조정 발생을 검증했다고 말할 수 없습니다.

## 사전등록 한계

03:01~03:07 KST에 검색 수·일부 줄·자료 칸을 본 뒤 보충 검색어와 분류 규칙을 정한 사실이 공개됐습니다. 고정 14개 집계는 원래 TASK와 동일하므로 정적 감사 완료 판정은 유지합니다. 다만 보충 9개 결과는 독립적인 사전등록 검증으로 승격하지 않고 연결 설명용 근거로만 취급합니다.

## 다음 한 단계

실제 데이터 연결 전에 가격기준을 명시적으로 받는 fail-closed 게이트를 합성 복사본에서 검증합니다. `RAW_UNADJUSTED`만 기존 기업행위 배수 적용을 허용하고, `ADJUSTED`·누락·알 수 없는 값은 어떤 장부 mutation도 하기 전에 차단합니다. 이는 Train 가격기준을 선택하거나 운영 코드를 바꾸는 단계가 아닙니다.
