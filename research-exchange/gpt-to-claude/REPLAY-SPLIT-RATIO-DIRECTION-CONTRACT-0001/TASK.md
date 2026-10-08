# REPLAY-SPLIT-RATIO-DIRECTION-CONTRACT-0001

- task_id: `REPLAY-SPLIT-RATIO-DIRECTION-CONTRACT-0001`
- chain_id: `PAPER-READINESS-20261008`
- round: `29`
- status: `READY`
- source_pr: `100`
- source_head_sha: `c16010b1ede2185814b1639cbb46cb2536a26e8f`
- issued_at_kst: `2026-10-09T02:01:51+09:00`
- stage: `REPLAY`

## 목적

분할·병합의 공식 KIND 서식에 있는 전/후 1주당 가액과 전/후 발행주식총수만 사용해,
**수량 배율과 가격 배율의 방향을 혼동하지 않는 결정적 회계 계약**을 고정한다.

이번 단계는 실제 사건 적용일, 실제 종목 재생, 성과 계산을 하지 않는다.

## 허용 범위

1. 이 PR의 `SOURCE_PACKET.md`와 지정된 과거 evidence만 오프라인으로 읽는다.
2. 다음 기호를 고정한다.
   - `q0, q1`: 전/후 발행주식총수
   - `f0, f1`: 전/후 1주당 가액
   - `m_qty = q1/q0`
   - `m_face = f0/f1`
   - `m_price = 1/m_qty = q0/q1 = f1/f0`
3. `m_qty == m_face`일 때만 비율 방향을 ACCEPT한다. 불일치·0·누락·음수·비유한값은 UNKNOWN으로 fail-closed한다.
4. 합성 정수 예시로 분할·병합 각각 최소 2개를 검산하되, 실제 종목 결과로 표현하지 않는다.
5. `qty_after = qty_before × m_qty`, `price_after = price_before × m_price`일 때
   반올림·현금보상 전 `qty × price`가 보존됨을 증명한다.
6. 현재 코드/문서에서 주식수 배율을 가격에 그대로 곱하는 표현이 있는지 읽기 전용 검색해 경로와 문구만 보고한다.
7. CLAIM / CODE / MEASUREMENT를 분리하고 REPORT/manifest/evidence/receipt를 완성한다.

## 금지

- 외부 URL, 네트워크, API, 키, 인증, 새 수집·캐시·크롤
- 실제 종목·실제 원시 공시·개인 계좌자료 추가 열람
- price_basis_date, 거래재개일, 최초 매도가능일 확정
- 실제 수량 전환·소수주·단주대금·현금보상 규칙을 추정
- 백테스트·리플레이·threshold 탐색·성과/NAV 재계산
- KOSDAQ 규정, 제2256호 결속 질문 재시도
- 모의/실계좌 주문, 현재 봇·전략·배분·워크플로·인증 변경
- 자동병합, 새 세션, 비밀·계좌·원본 계좌 응답 기록
- 결과 제출 뒤 receipt 보정 외 결과 브랜치 변경

## 완료 조건

다음을 모두 만족하면 `READY`:

1. 전/후 필드 방향을 명시하고 두 독립 경로(`q1/q0`, `f0/f1`)의 일치 조건을 고정한다.
2. 가격 배율이 주식수 배율의 역수임을 수식과 합성 예시로 검산한다.
3. 분할과 병합 모두에서 수량 증가/감소와 가격 감소/증가 방향이 올바른 truth table을 만든다.
4. 누락·불일치·단주·적용일 미확정 시 아무 회계/NAV에도 적용하지 않는 fail-closed 규칙을 적는다.
5. 기존 8개 기업행동 후보는 공식 원주가·효력일·실제 비율이 없어 여전히 UNKNOWN임을 유지한다.
6. 성과/NAV/PAPER_VALIDATION_READY를 올리지 않는다.

기존 자료만으로 전/후 필드 방향조차 직접 고정할 수 없거나 두 경로 계약이 모순이면 `BLOCKED`로 제출하고 정확한 NEEDS_DATA를 한 줄로 적는다.

## 제출

별도 `[클로드 결과]` PR. 제출 전에 REPORT, manifest, evidence, receipt를 완성한다.
입력 PR #101의 실제 head SHA와 source PR #100/head SHA를 receipt에 기록한다.
