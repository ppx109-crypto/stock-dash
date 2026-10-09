# REPLAY-KRX-PRICE-BASIS-RULE-LOCK-0001 — 클로드 사전등록(판정 · 코드 · 증거 전)

- 지시: GPT PR #93 head `fffc3088`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `07ec979bd478686a`
  - SOURCE_PACKET `451aefa53240ec91`
  - PREREG `cf5ccabf13775233`
  - REVIEW `2adb17b52465b70b`
  - receipt `754200924e6dfd44`
- 입력 PR #92 head `8f9a1d934fa8f3fa110332a0aa4885320d91956b`: 시작 직전에 확인했고 일치합니다(01:31 KST). 제출 직전에 한 번 더 확인합니다.
- **오프라인만**: 외부 URL · 브라우징 · 네트워크 허용 요청 0, API · 키 0, 수집 · 캐시 · 재생 · 성과 0. 패킷 URL도 열지 않습니다.
- 저장소 문서(INSTRUCTIONS · README 2개)는 불신 입력으로 읽기만 했습니다. 그 안의 명령은 따르지 않습니다.

## 1. 판정 칸
- 유가증권 × split, 유가증권 × reverse_split, 코스닥 × split, 코스닥 × reverse_split — 4칸
- 칸마다 아래를 따로 판정합니다.
  - 규정 식별: 시장 · 정식 규정명 · lawid · 공개/개정일 · 조문/별표 위치
  - 산식
  - 날짜 관계(`당일`이 어느 날인지)
  - `price_basis_date`
- 형식: `CLAIM / OFFICIAL_INDEX_TEXT / INFERENCE / VERDICT / EVIDENCE_TIER`

## 2. 고정 규칙(결과를 본 뒤 바꾸지 않음)
1. 증거 등급은 모두 `GPT_CAPTURED_OFFICIAL_INDEX`입니다. 직접 원문으로 승격하지 않습니다. 이 등급만으로는 어떤 항목도 ACCEPT하지 않고, 최대 REVISE입니다.
   - 예외 없음. PR #92에서 서식 이름 존재에 준 예외는 이번 '규정 의미' 판정에 쓰지 않습니다.
2. **시장 대응:** 패킷 안에 lawid ↔ 시장(유가증권/코스닥)을 잇는 문구가 없으면, 그 lawid의 시장은 '증거 없음'입니다.
   - 패킷 '사용 한계 2'가 S1~S3 = 유가증권, S4~S6 = 코스닥을 전제가 아닌 주장으로 둡니다.
3. **버전:** 공개일만 있고 시행일 · 현행 여부가 없으면 '버전 미확정'입니다. 과거 공개본은 그 시행 구간 밖으로 일반화하지 않습니다.
   - 우리에게 필요한 것은 '현행'만이 아니라 **Train 기간(2025-09-18 ~ 2026-03-31)에 시행 중이던 버전**입니다.
4. **산식:** 정확 발췌(따옴표 문구)가 있으면 OFFICIAL_INDEX_TEXT로 적되, 판정은 최대 REVISE입니다. 비율의 방향(분할 비율이 '분할 뒤 주식 수 ÷ 분할 전'인지 그 반대인지)이 문구에 없으면 그 사실을 따로 적습니다.
5. **날짜:** '분할 · 병합되는 날' · '최초 호가일'이 거래 재개일과 같다는 공식 문구가 없으면 INFERENCE입니다. 산식만으로 날짜를 만들지 않습니다.
6. 효력발생일은 쓰지 않습니다. 사례 일치(PR #92)는 보조 관찰입니다. 유가증권 근거를 코스닥으로 넓히지 않습니다. '유효성 없음'이 아니라 '증거 없음'으로 씁니다.
7. **`price_basis_date` ACCEPT 조건:** PR #93 PREREG의 6축(규정명 · 시장 / lawid · 조문 / 버전 · 시행일 / 산식 / 당일 = 재개일 문구 / PR #92와 모순 없음)이 모두 공식 근거여야 합니다. 하나라도 없으면 `BLOCKED_NO_OFFICIAL_EVIDENCE`입니다.
8. 판정은 `code/decide.py`가 패킷 사실표(오프라인 상수)에 위 규칙을 적용해 냅니다(네트워크 · 데이터 0).
9. 상태: 4칸 모두 `price_basis_date`가 ACCEPT일 때만 READY, 아니면 BLOCKED입니다.

## 3. 산출물
- `REPORT.md` · `manifest.json` · `receipt.json`
- `evidence/rule-identity-matrix.json` · `evidence/price-basis-date-decision.json` · `evidence/run.log`
- `code/decide.py`
