# PR49 검토 — R30은 약한 개선 후보, 상한 탐색 종료
{"task_id":"EMA-FLOW-0001","chain_id":"MAX-RETURN-20261008","round":4,"status":"READY","source_pr":49,"source_head_sha":"ba7e05a3ec1aa5db2a09043af3da5a03a8102fc4"}
감지: 2026-10-08 16:57:24 KST. 검토: 2026-10-08 17:03 KST.
입력 open/non-draft/READY, head ba7e05a3ec1aa5db2a09043af3da5a03a8102fc4. INSTRUCTIONS, 루트 README, 교환 README, REPORT/PREREG/manifest/receipt/code/evidence를 고정 SHA로 읽었다.
24개 manifest 파일 SHA256 전부 일치. PREREG 2cc68ef7 16:47:32 → 결과 ba7e05a3 16:56:58 → PR opened 16:57:14 순서. 변경25개는 결과폴더 안이고 제출 뒤 연구 오염 없음. source PR48의 812810b5 이후 변경은 전달 receipt 보정뿐이다.
GPT 직접 일별 NAV 산술: CSV13개(Train127행×10, 전체230행×3)의 끝 금액·CAGR·MDD·최악일/날짜·하루-15% 횟수가 보고와 일치(원 단위 반올림 오차). 새 R30 원시가격 전체 재실행은 이번 검토에서 하지 않았다. 공유 엔진 대조/지표 산술과 독립 엔진 증명을 구분한다.
Train 비용2배 M4: 18,346,201원, 최악일 -15.09%; R30: 18,575,047원, 최악일 -12.64%. 전체 비용1배 M4 31,866,431 → R30 32,674,936원(+808,505원), 전체 MDD는 -28.86 → -29.18%로 소폭 악화. 전체 비용2배 끝금액 R30 30,500,162원은 JSON 주장이고 해당 전체2배 NAV CSV는 미제출이라 직접 NAV 산술 범위가 아니다.
규칙을 만든 뒤 사전등록했지만 규칙 아이디어 자체는 Train 손실일을 본 뒤 나왔다. 미사용 OOS가 아니며 통과로 손실한도/실전 수익을 보장하지 않는다. 최대이익 종목 제외 시 Train 개선 +294,839원이 +34,157원으로 줄었다. R30 보관, 더 cap 탐색하지 않는다.
새 사용자 아이디어의 진입 골격은 이미 nrl.teacher(외국인+/투신+/개인- 5일), aligned, BASE_HOLD에 있다. 기관 합계 조건은 추가 가설이다. investor-data의 개인/외국인/기관/투신은 broker_kis.INVESTORS의 순매수 '수량'이며 gross 매수비율이 아니다.
과거 docs/RL-FLOW-LOG F10/research/f010.py는 수급반전 전량매도가 뒷기간을 악화시켰다고 기록한다. 이는 옛 엔진/비용 가정의 과거 주장이지 최신 검증된 성과가 아니다. 새 가설은 개인 강도 증가 시 1회 부분익절로 전량매도와 다르다. 이름만 바꾼 F10 재실행을 하지 않는다.
최신 사용자 승인: 월-15%는 연구탈락조건 해제, 하루-15% 유지, MDD보고. 고정3회 승인대기 해제 및 새로운 수급조합 연구 승인. 오래된 INSTRUCTIONS가 최신 승인/금지 범위를 대체하지 않는다.
