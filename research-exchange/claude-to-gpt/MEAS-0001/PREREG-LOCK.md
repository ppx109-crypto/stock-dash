# PREREG-LOCK — MEAS-0001 (작성 2026-10-08 07:37 KST)

> **순서 고지**: 아래 §4의 세 검사(git 수신 시각 · calm 캐시 · 수급 줄 shift)는 이 문서를 쓰기 **전에** 읽기 전용으로 먼저 돌렸음(탐색 순서 실수). 그 실제 조건을 그대로 적고, 결과를 보고 바꾼 것은 §6 '변경 기록'에 모두 남김. 대사(§5)와 합성 시험은 이 문서 뒤에 실행.

## 1. 코드 · 자료 판
- 코드 기준점: `00b98ab1655c84806357f44f2de6f1509ef1447f`(git worktree --detach · 읽기만 · import는 시험에서 떼어 낸 함수뿐).
- 운영 모의 기록 스냅샷: origin/main `54bf28c2d52a5f21d135ead7892735c06c417e5e`(커밋 2026-10-08 07:25 KST · 관측 2026-10-08 07:29 KST). 운영 코드 · 워크플로는 기준점과 이 스냅샷 사이 변경 없음(`git diff --stat` 빈 값).
- 읽은 모의 기록은 **코드가 적어 둔 경로만**(paper_trade.py:24-30 · 각 봇 HOME/STATE · reconcile.py:27-29 · fix_recent_days): {hourly,daily,m15,idle,basket}-live/* · reconcile/* · fix-recent/*. 비밀 · .env · 실계좌 기록은 열지 않음.
- 1D 연구 캐시: nrl-cache.pkl(sha256 4ec07fae…cfda57) — 정적 opcode 검사로 참조가 numpy._frombuffer · numpy.dtype 둘뿐임을 확인한 뒤, 이 둘만 허용하는 제한 로더로 읽음.

## 2. 기간
- 모의 기록: 각 파일의 첫 커밋 ~ 스냅샷(1D 2026-10-02 ~ 10-07 · 15분봉 10-02 ~ 10-07 · 1시간봉 10-02 ~ 10-07 · 엔진 10-03 ~ 10-07). 날을 빼지 않음.
- git 수신 시각: 저장소 이력 시작(2026-09-09) ~ 스냅샷 · 각 파일의 **첫 커밋 날짜까지의 줄은 백필**로 보고 수신 시각 '알 수 없음'.

## 3. 반올림 · 판정
- 금액 대사는 원 단위 정수로(허용 오차 없음). 수량은 정수.
- 판정 등급: TRUSTED_FOR_PAPER_EVALUATION / INVALID_MEASUREMENT / INSUFFICIENT_EVIDENCE(실전 등급 아님).

## 4. 먼저 돌린 세 검사의 실제 조건
- git 수신 시각(audit/git_availability.py): 표본 = investor-data 종목 목록을 이름순으로 정렬해 **10개마다 1개**(결과 보기 전 정함). 판단 시각 = 다음 거래일 15:20(1D) · 공시는 다음 거래일 15:10(바구니). 시장 달력 = market-data/index_KOSPI.json.
- calm 캐시(audit/calm_cache_audit.py): 캐시의 rule._calm vs 캐시 안 CALM_MONTH(그 달 첫날 앞 자료만으로 잰 같은 40% 자리) · 추세 문 3조건(변동성 · 기울기 ≥ 1.46 · 60일 ≥ 20) 중 '조용함'만 바꿔 갈리는 행 수 — 성과는 재지 않음.
- 수급 줄 shift(audit/row_shift_audit.py): investor-data 종목마다 자기 기간 안 시장 거래일 결손 · 앞 5줄 창이 거래일 5일을 넘는지.

## 5. 대사 · 시험(이 문서 뒤)
- 실제 관측 대사: KIS 모의 주문 장부의 held vs 접수 수량 합 · 봇 상태(state) vs 장부 · 예수금 · 체결 · 비용 대사는 자료가 있으면만(없으면 null + 까닭).
- 합성 시험: a_mtm.account(소스에서 떼어 실행) 계약 · RULES-0001 contract.py(입출금 TWR) · calm 미래 행 추가 · 장후 공시 반응 시작일 · 수급 결손일 cutoff.

## 6. 변경 기록
- git 수신 시각 검사 1차: investor-data 파일 구조를 잘못 가정(dict 줄)해 0줄 · 공시는 백필 줄까지 세어 '늦음'이 부풀었음 → 구조를 list 줄로 고치고 **각 파일 첫 커밋 날짜까지의 줄은 제외**(백필)로 바꿔 다시 돌림. 표본 · 판단 시각 · 기간은 안 바꿈. 1차 결과는 쓰지 않음.
