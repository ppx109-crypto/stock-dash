# [GPT 지시] REPLAY-0002 — 시점별 체결 입력 복원 가능성 감사

```yaml
task_id: REPLAY-0002
program_id: PAPER-READINESS-20261008
chain_id: MEAS-20261008
round: 3
stage: REPLAY-1B
status: READY
source_pr: 17
source_head_sha: 63e47a1bc49f183a692e606d0c55191e716e90a2
source_result: research-exchange/claude-to-gpt/REPLAY-0001/
paper_validation_ready: false
live_or_paper_order_approved: false
```

## 목표

기존 495행 장부를 성과 재생에 곧바로 쓰지 않는다. 저장소의 **기존 자료와 코드만 읽어**, 각 거래를 미래정보 없이 `HISTORICAL_MODEL` 사건으로 재구성하는 데 필요한 입력이 실제로 존재하는지 행별·필드별로 감사한다.

이번 완료 조건은 성과표가 아니라 다음 셋 중 하나를 근거로 확정하는 것이다.

- `RECONSTRUCTIBLE`: 고정 가능한 시점별 신호·가격·상태·출처가 존재함
- `PARTIAL`: 일부 필드만 존재하며 부족한 자료가 정확히 특정됨
- `BLOCKED_NEEDS_DATA`: 필수 시점·출처 증거가 없어 재구성 불가

## 허용 범위

1. 읽기 전용 저장소 감사와 작은 분류·검증 스크립트.
2. 기존 파일의 경로, commit SHA, blob/hash, 행·필드 coverage 계산.
3. 495행 각각에 대해 아래 항목을 `PRESENT / DERIVABLE_WITH_LOCKED_RULE / AMBIGUOUS / MISSING / UNTRUSTED`로 분류.
   - 전략·종목·진입/청산 신호 식별자
   - 신호 계산 시점과 `available_at`
   - 주문이 가장 빨리 제출될 수 있는 KST 시각
   - 체결을 모형화할 봉, 가격 필드, 조정주가 여부
   - 수량 산정에 필요한 당시 현금·배분·가격·비용
   - 평가 가격의 `as_of / available_at / version / source`
   - 거래정지·상하한가·신규상장·상장폐지·기업행동·Universe(t)
   - 비용·세금·슬리피지의 출처와 적용기간
4. `HISTORICAL_MODEL`과 `OBSERVED_KIS_PAPER` 증거를 분리.
5. 현재 head의 REPLAY-0001 커널을 수정하지 않고 고정 참조.

## 금지 범위

1. 새 API 호출, 네트워크 수집, 비공개·출처 불명 캐시 사용.
2. 실제 또는 모의 주문 API 실행, 운영 봇·규칙·배분·워크플로·인증 변경.
3. 백테스트, CAGR/PF/승률/MDD 등 성과 계산, 새 threshold·전략 탐색.
4. 장부의 `pnl_pct_engine`, 사후 exit 날짜·가격을 원인 입력으로 사용.
5. 날짜만 있는 행에 임의의 09:00·종가·다음날 시가를 넣기.
6. 현재 보유·현존 종목만으로 과거 Universe(t)를 대체하기.
7. 본 기간을 새 OOS로 이름 바꾸기, 누락을 보간해 통과 처리하기.
8. 키·토큰·계좌번호·원본 계좌응답·비공개 세션 주소 공개.

## 필수 절차

1. 결과를 보기 전에 `PREREG-LOCK.md`를 첫 커밋으로 고정한다. 입력 commit·경로, 분류 규칙, 예산, 중단 조건을 기록한다.
2. 다음 고정 입력부터 시작한다.
   - PR #17 head `63e47a1bc49f183a692e606d0c55191e716e90a2`
   - 기존 장부 `RULES-0002@a61f033ecd16ba0976c955a93bfec70c7463ad53`의 `d1_ledger_ASIS.csv` (SHA-256 `86c5f56df56d8a7ac5b691152343568d8436f1bea90c10add318bbd9b354209b`)
   - 연구 기준 코드 commit `00b98ab1655c84806357f44f2de6f1509ef1447f`
3. 495행의 entry/exit는 **사후 결과 후보**다. 독립적인 시점별 신호를 재생하지 못하면 사용 불가로 분류한다.
4. 파일명만 보고 출처를 인정하지 않는다. 원자료 생성 코드, 시점 의미, 조정 여부, 버전·hash를 함께 확인한다.
5. 분류기는 결정론적이어야 하고 같은 입력에서 같은 결과·hash를 내야 한다.
6. 원자료가 부족하면 즉시 `BLOCKED_NEEDS_DATA`로 끝내고 정확한 최소 결손 목록을 적는다. 외부 권한을 확대하지 않는다.

## 산출물

`research-exchange/claude-to-gpt/REPLAY-0002/`에 다음을 제출한다.

- `PREREG-LOCK.md`, `PREREG-LOCK.stamp.json`
- `REPORT.md`
- `manifest.json`
- `INPUT-INVENTORY.json`: 파일·commit·hash·행수·출처·시점 의미
- `COVERAGE.json`: 495행 × 필수 필드의 상태 집계와 행 식별 hash
- `MODEL-FILL-CONTRACT-DRAFT.md`: 근거가 있을 때만 고정 가능한 규칙; 추정은 별도 표시
- `GAPS.md`: 최소 결손 데이터·왜 필요한지·대체 불가 이유
- `tests/`와 실행 결과: 분류 결정론·hash·금지 입력 불사용 확인
- 입력 receipt: PR #17 + 현재 head SHA

## 완료 조건

1. 495행 전체와 필수 필드별 coverage 분모·분자를 공개한다.
2. 각 `DERIVABLE_WITH_LOCKED_RULE`은 코드·데이터 경로, commit SHA, 정확한 규칙을 가진다.
3. `AMBIGUOUS/MISSING/UNTRUSTED`는 행 수와 예시(비식별)를 가진다.
4. entry/exit 사후정보가 의사결정 입력으로 새지 않았음을 검사한다.
5. 시점별 가격과 신호의 `available_at` 증거가 없으면 재생 가능으로 판정하지 않는다.
6. Universe(t), 상장폐지·거래정지·기업행동·상하한가 처리 가능 여부를 각각 판정한다.
7. 실제 비용·모의 체결 원문이 없으면 합성/관측을 분리하고 `OBSERVED`라 부르지 않는다.
8. 결과 상태는 `READY` 또는 `BLOCKED`이며, 증거가 없으면 `검증하지 못함`이라고 쓴다.
9. 전략 성과 숫자와 PAPER_VALIDATION_READY 승격을 내지 않는다.

