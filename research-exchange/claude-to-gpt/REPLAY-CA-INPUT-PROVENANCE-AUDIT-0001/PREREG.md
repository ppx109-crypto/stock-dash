# REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001 — 클로드 사전등록(정적 감사 · 공식 실행 전)

- 지시: GPT PR #115 head `9e5187be`. 파일 sha256 앞 16자는 다음과 같습니다.
  - TASK `8e01ab2c2930b940`
  - SOURCE_PACKET `6a887f27eb4bd518`
  - PREREG `93148e68674f46d0`
  - REVIEW `c6d64282e4217368`
  - receipt `0cac8dc470bcbe72`
- 원천: PR #114 head `6261e5a100607b36fa033b8a2ce710482cf8ccfa`(열림 · 초안 아님 · 03:01 · 03:07 KST 두 번 확인).
  - GPT PREREG의 blob 5개(code `58417375` · evidence `02f65d3c` · report `cd34b51f` · manifest `cb6b6237` · receipt `c0e6a6ca`)와 모두 일치합니다.
- **읽기만:** 저장소의 스크립트 · 시험 · 워크플로 · 노트북은 실행하지 않습니다.
  - 명령은 `git ls-tree` · `git grep` · `git show`(읽기) · 해시 계산뿐입니다.
  - 분류 · 집계는 제 감사 스크립트(`code/audit_inventory.py`, scratch에서 작성)가 git 객체를 읽어서 합니다.
- 금지 0: 외부 API · Secrets · 새 수집 · 실제 사건 적용 · replay · NAV/성과 · adapter/운영 코드 수정 · threshold/alpha · 주문 · 자동병합.
- **실제 값은 옮기지 않습니다.** INVENTORY에는 줄 본문 대신 줄의 sha256을 넣습니다. 자료 파일은 칸 이름 · 줄 수 · 파일 수만 셉니다.

## 공개 — 사전등록 전 탐색(03:01~03:07 KST)
- 사전등록 전에 다음을 먼저 봤습니다.
  - 14개 검색어의 줄 수 · 파일 수
  - 기업행위 관련 일부 줄(`docs/QUANT-REPORT.md` · `caps.py` · `fix_recent_days.py` · `broker_kis.py` · `collect_dart_extra.py` · `collect_events.py` · `probe_catalog.py`)
  - `dart-events/` 칸 이름 · 줄 수
- 아래 분류 규칙과 보충 검색어는 이 탐색을 본 뒤 정했습니다.
- 판정에 쓰는 고정 검색어 14개는 GPT TASK 그대로이며, 탐색으로 바꾸지 않았습니다.

## 범위(고정)
- **S1 원천 트리:** PR #114 head의 추적 파일 전체입니다(13,402개 · 바이너리 제외 `git grep -I`).
- **S2 앞선 고정 결과:** 결과 PR head의 `research-exchange/claude-to-gpt/<TASK>/` 폴더입니다.
  - #86 `916bc678` · #88 `a5891f5b` · #90 `f2e59846` · #92 `8f9a1d93` · #94 `63942ef7`
  - #96 `e6c4f9d5` · #98 `c5abe694` · #100 `c16010b1` · #102 `b940b283` · #104 `ad13f077`
  - #106 `dacbcb09` · #108 `ca440842` · #110 `2c7c268b` · #112 `9e88dba8`
  - 이 PR들은 main에 병합되지 않아 S1에 없습니다. RAW-PRICE-CONTRACT · HARDENING 계열과 PR #102~#112 자료는 S2에서 읽습니다.
- **고정 검색어 14개(판정용):** `corporate_action` `m_qty` `m_price` `apply_date` `split` `reverse_split` `bonus_issue` `rights` `dividend` `adjusted` `event_id` `revision` `available_at` `src`
  - 방식: 대소문자 구분 · 부분 문자열(`git grep -n -I -F`)
  - 한 줄에 검색어가 여럿이면 검색어마다 한 행입니다.
- **보충 검색어 9개(trace 연결용 · 판정 집계와 따로 표시):** `rcept_no` `ORG_ADJ` `price_basis` `effective_date` `수정주가` `액면분할` `무상증자` `권리락` `nstk_ascnt`
  - 고정 14개에는 DART 사건 번호(`rcept_no`)와 KIS 가격 기준 인자(`FID_ORG_ADJ_PRC`)가 빠져 있어 덧붙입니다.

## match 분류 규칙(결정적 · 공식 실행 1회)
행마다 `class`(6갈래 중 하나) · `ca_relevant`(참/거짓) · `actual_path`(참/거짓) · 근거를 답니다.

1. **PR #114 폴더(S1)와 S2 폴더**
   - `code/*.py` 안의 장부 클래스 정의 구간은 `consumer`(합성), 나머지 줄은 `test`입니다.
   - `evidence/*` 는 `data`(합성 파생), `*.md` · `manifest.json` · `receipt.json` · `schema/*` 는 `doc`입니다.
   - ca_relevant=참, actual_path=거짓.
2. **그 밖(S1)**
   - 경로가 `tests/` 또는 `test_*.py`이면 `test`입니다.
   - `.md` · `.txt`이면 `doc`입니다.
   - `.json` · `.csv` · `.jsonl` · `.log` · `.tsv`이면 `data`입니다.
   - `.yml` · `.yaml`이면 `transformer`(워크플로 조립)입니다.
   - 코드(`.py` · `.html` · `.js` · `.sh`)는 파일 본문으로 정합니다.
     - 네트워크 호출 흔적(`requests.` · `urlopen` · `httpx` · `.request(`)이 있으면 `producer`
     - 파일 쓰기 흔적(`write_text` · `json.dump` · `open(…'w'`)이 있으면 `transformer`
     - 둘 다 없으면 `consumer`
3. **ca_relevant(S1 그 밖)**
   - 줄에 기업행위 · 가격 기준 문맥 낱말이 있으면 참입니다. 낱말은 `액면 분할 병합 무상 감자 수정주가 원주가 권리 배당 corporate reverse_split bonus m_qty m_price apply_date ORG_ADJ rights dividend available_at adjusted`입니다.
   - 그렇지 않으면 거짓이고, 근거를 붙입니다. 예: `.split(`이면 '문자열 나누기', `src`면 '기업행위 사건 칸 아님'.
4. **actual_path:** 1번 범위 밖에 있으면서 test · doc가 아닌 행은 참입니다. 운영 · 연구 코드와 실제 자료가 여기에 듭니다.
5. 규칙에 걸리지 않는 행은 `UNCLASSIFIED`로 남깁니다. 1행이라도 있으면 BLOCKED입니다.

## 판정 기준(GAPS · TRACE)
- GAPS 9개 필드를 각각 판정합니다(GPT PREREG 규칙 그대로).
  - `PRESENT_VERIFIED`: 실제 원천 → 생산 → 변환 → 소비 → 증거가 모두 이어짐
  - `PRESENT_UNLINKED`: 문서 · 합성 · 원천 칸만 있고 실제 연결이 없음
  - `ABSENT`: match가 없음
  - `CONFLICTING`: 정의가 서로 맞지 않음
  - 실제 자료가 있어야만 풀리면 `NEEDS_DATA`를 덧붙입니다.
  - 생산자가 없으면 `NO_PRODUCER`, 실제 사건이 없으면 `NO_ACTUAL_EVENT`를 덧붙입니다.
- TRACE는 `m_qty` · `m_price` · `apply_date` · `kind` · `src` 다섯 칸입니다. 칸마다 실제 원천 → … → PR #114 소비자 → 증거의 연결 또는 **첫 단절점**을 `path:line` + blob으로 적습니다.
- 주장(doc) · 코드 존재 · 실제 자료 연결을 따로 표시합니다.

## 판정
- 아래가 모두 맞으면 READY입니다. 하나라도 빠지면 BLOCKED입니다.
  - 고정 14개 match 전부 분류(UNCLASSIFIED 0)
  - S1 · S2 파일 해시 기록
  - 5칸 TRACE · 9칸 GAPS 완성
  - 원천 head 일치
- READY는 정적 감사의 완결만 뜻합니다. `PRESENT_VERIFIED`를 보장하지 않습니다.
- `actual_events=0` · `external_calls=0` · `code_execution=0`(저장소 코드) · `performance_verified=false` · `paper_validation_ready=false`
- 다음 단계는 감사가 특정한 단일 결손 하나만 제안합니다. 구현 · 수집 · 재생은 이번 PR에 넣지 않습니다.

## 산출물
- `INVENTORY.json` · `TRACE.md` · `GAPS.json` · `REPORT.md` · `manifest.json` · `receipt.json`
- `code/audit_inventory.py` · `evidence/run.log` · `evidence/search-counts.json`
