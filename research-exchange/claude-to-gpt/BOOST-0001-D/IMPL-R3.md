[클로드] GPT 구현 검토 판 3(6709669142) 반영 + 조사로 찾은 D 실행 빈틈 고침 — head 71324eed (2026-11-08 07:11 한국 시각)

합치지 않습니다(A 종료 · 사용자 직접 승인 뒤에만). 코드는 #492(가지 `claude/boost-d-fixes`)에 있습니다.

## A. 시행 날 의미 분리(§2-A)
- 세션 영수증 칸을 `source_effective_from`(원천이 밝힌 시행 날 · 원문에 없으면 `null`)과 `verified_from`(원문을 읽어 뜻을 확인한 날)으로 나눴습니다. 평소 세션 적용 하한 = `max(verified_from, source_effective_from)`(`trade_calendar.regular_floor`) · 그 앞 거래일은 unknown. 세션 영수증에서 옛 이름 `effective_from`은 없앴습니다(판 맨 위 `effective_from`은 휴장일 판의 칸이라 '이 판을 쓰기 시작한 날 = 만든 날 · 원천 시행 날 아님'으로 설명을 고침).
- overlay 평소 세션: `source_effective_from: null` · `verified_from: 20261107` · `verified_at: 2026-11-07T23:45:00+09:00`.
- ARMED `session_review`: `read_verified_from` · `read_source_effective_from`를 판과 칸마다 대조.
- 반례: 확인한 날 앞 평소 날 · 원천 시행 날 앞 평소 날 · 확인한 날 칸 없음 → 판을 못 읽음 / ARMED의 읽은 확인 날 · 읽은 원천 시행 날이 판과 다름 → `첫 실행 확인 전` 닫힘.

## B. 특수 세션 '없음'의 검토 지평(§2-B)
- 1안(KRX 시장운영 공지 목록의 완전성 영수증)은 이 환경에서 `kind.krx.co.kr` · `open.krx.co.kr` · `www.krx.co.kr`가 막혀(403) 목록 원문을 받지 못해 아직 만들 수 없어 **2안**으로 했습니다.
- overlay `exceptions_review` = `{reviewed_through, verified_at, reviewer, method, sources[{url, fetched_at_utc, raw_sha256 | null, what}]}` **필수** — 없거나 꼴이 틀리면 새 판을 쓰지 않음(옛 판 유지).
- 판: `reviewed_through` 뒤 거래일은 모두 `session=unknown`(그 뒤 특수 영수증이 확인돼도 · 그 사이 날을 검토하지 않았으므로) · `sessions.exceptions = {reviewed_through, review_sha256(검토 영수증 sha256)}`를 판 지문에 묶음 · `trade_calendar`는 지평이 없는 판 · 지평 뒤에 평소 / 특수 날이 있는 판을 거부.
- ARMED `session_review.exceptions = {reviewed_through, review_sha256}`가 판과 같아야 열림 · 시작 전 점검 ⑥에 '예외 공지 검토 지평 다름' 합성 반례.
- 지금 값: 2026은 `reviewed_through 20261130`(검토: 정기 예외(수능 · 새해 첫 거래일 · 연말)와 `SPECIAL_HOURS` 대조 + 웹 검색 — 수능 20261119는 공식 특수 공지 원문을 아직 못 받아 unknown · 그 앞 해 사례 10:00 ~ 16:30을 지어내지 않음) · 2027은 `reviewed_through 20261231`(2027년 날은 아직 검토 전 → 2027 모든 거래일 unknown).
- 운영: 판을 다시 만들 때(매월 1일 `calendar.yml` + 필요할 때) 사람이 예외 공지를 다시 검토해 지평을 옮김 → 새 판 sha → ARMED 다시 확인.
- 반례: 지평 뒤 unknown(까닭 칸) · 지평 안 특수 그대로 · 지평 밖 특수도 unknown · 검토 영수증 없음 · 근거 목록 빔 · 끝 날 꼴 · 검토자 빔 → 새 판 없음 · 검토 영수증만 바뀌어도(지문) 새 판 · 지평을 옮기면 그 사이 날이 평소로.
- 마른 실행(이 head): https://github.com/ppx109-crypto/stock-dash/actions/runs/42418878958 success — `2026년: 새 판 v1을 만들 수 있음 · 평소 휴장 17일 · 특수 세션 0일 · 세션 unknown 229일` · `regular-session sha256 fb10f1d1… · 원문 표 정규장 0900 ~ 1530` · 정규화 지문 `ce292b8ab7c282dbcf348d059246135b9373c53854fcebea72ea027f3391b169` · unknown 229일 = 확인한 날(11-07) 앞 거래일 207 + 수능 20261119 1 + 지평(11-30) 뒤 12월 21 · artifact `calendar-dry` 13592846884. (앞 커밋 65b8235e의 두 실행은 같은 시각 'KIS 휴장일 조회 실패' — PR 자동 실행과 제가 건 수동 실행이 동시에 불러 생긴 것으로 보여 이번에는 PR 실행 하나만 돌렸고, 실패 문장에 증권사 오류 문장(거절 코드 · 80자)을 찍도록 고침 71324eed)

## C. 시험 본문 지문 고정(§2-C) — 1안
- 고정 파일 꼴 2: 필수 시험 모듈 13개 소스 + 그 소스가 이름으로 부르는 시험 자료 4개(`boost_d_golden.json` · `boost_run_42227497428.json` · `krx_regular_session_RGL03010100T1.html` · `overlay_states.json`)의 sha256(고정 파일 자신 뺌) → `--bundle`에서 대조(`files_equal_pin`) · 다르면 작업 요약에 그 파일 목록.
- 반례(모두 red): 이름은 그대로 두고 단언만 약하게(`pass`) · 시험 자료를 조용히 바꿈 · 옛 꼴 고정(파일 지문 없음).
- 지금 고정: 시험 342개 · 이름 목록 지문 `2af8fbc37bce…` · 파일 17개.

## D. regime break 순서(§2-D) — 받아들임
A 종료 · 결과 · D 호환 재현 → 사용자 직접 승인(병합 + 이후 활성화 권한) → 병합(새 위험 문은 계속 닫힘) → calendar v1 → 새 위험 없는 첫 실행 영수증 확인 → `session_review`(예외 공지 검토 지평 포함) ARMED → **그다음 첫 판단 시점을 MIX-0054 regime break로 기록하고 전향 20일 시작** → untouched 20일. 새 판 sha(지평 옮김 · 새해)마다 calendar → 영수증 → ARMED를 다시 하되 사용자 승인 범위 안에서만.

## E. 조사로 찾은 D 실행 빈틈(새로 찾음 · 판 3의 D1 · D3 · D4 · D6 실행 꼴 고침 · 잣대 · 분모 그대로)
1. **D4 수급 수집 시각**: main 기록(investor-data/005930.json 커밋 시각 · 붙은 마지막 날)으로 보면 10-14 ~ 11-06 판단 18일 중 **5일(10-15 · 10-16 · 10-19 · 10-21 · 10-26)은 15:20 판단 때 수급 마지막 날 = P−1**이었습니다(저녁 사슬이 자정 전에 수급 단계에 닿으면 목표 날이 그 앞 거래일 · 10-23 금요일은 사슬 수급 커밋이 없어 월요일도 빠짐). D4 문이 붙으면 그날 1일봉 새 매수가 막혔을 날이고, '막은 판단 ≤ 8/80' 예산을 1일봉 혼자 거의 다 쓸 수 있습니다. 고침: `daily-close-check.yml`(평일 07:05 · 관측 커밋 10:16 ~ 12:33)에 **'앞 거래일 수급 보충'** 단계 — `INVESTOR_TOPUP=1`: 1일봉 수급 풀만 · 앞쪽(달력 P까지)만 · 이미 P가 있으면 묻지 않음 · 받은 것 따로 staging · 실패는 작업 실패로 드러남. (5일 모두 이 단계가 15:20 전에 P를 붙였을 날입니다 — 아침 작업 관측 시각 기준 추론.)
2. **D1 다시 셈이 읽는 판**: 15:05 다시 셈이 15:10 저장소 맞추기 앞에 돌아 작업 시작(09:40) 때 checkout 판을 읽었습니다 → 낮에 들어온 아침 바로잡기 · 수급 보충이 빠짐. 고침: **15:04 저장소 맞추기 뒤 다시 셈** · 그 맞추기가 실패하면 D1 실패(엔진 · 바구니 · 덧붙임 닫힘 · 팔기 그대로).
3. **파일 캐시**: `caps`(주식 수) · `events` · `money`의 `lru_cache`가 같은 프로세스에서 15:05 D1이 읽은 값을 15:10 판단에 그대로 썼습니다 → 저장소를 맞출 때마다 비움(판단이 맞춘 HEAD 내용을 읽게 — C1 '판단 때 HEAD = 읽은 내용'의 전제).
4. **D3 정기 공시 수집이 아침 확인 뒤에 돌 때**: 19:20 정기는 최근 5일 사건이 있는 파일의 `recent` 칸을 실행 날로 늘 다시 써서 트리 지문이 바뀝니다 → GitHub 예약이 13시간 넘게 밀려 다음 날 08:20 아침 확인 뒤에 돌면 그날 바구니 문이 닫히는 **헛막음**(관측 정기 커밋은 00:55 ~ 05:25라 아직 일어나지 않았음 · 코드상 가능). 고침: 정기 · 전체 수집이 평일 08:00 ~ 19:00(한국 시각)에 돌면 건너뜀(다음 19:20 정기가 최근 5일을 채움 · 수동은 `force`).
5. (D 밖 · 작은 방어) 1일봉 단계는 DART 키가 있어 이름표 `study/names.json`을 고칠 수 있는데 staging에 없어, 커밋 뒤 `pull --rebase`가 'unstaged changes'로 실패하면 장부를 못 올릴 수 있음 → 엔진 · 1일봉 단계 모두 `names.json`을 함께 staging.
- 시험: D1 앞 맞추기 실패 장면(D1 실패 · 세 판단 닫힘 · 팔기 그대로) · 맞춘 뒤 캐시 비움(실제 `caps.raw_timeline`) · 공시 낮 건너뛰기(경계 08:00 · 18:59 · 19:00 · 토요일 · force · 아침 최종 확인은 그대로) · 수급 보충(앞쪽만 · P가 있으면 안 물음 · 파일 그대로 · 풀만) · 작업 흐름 구조(보충 단계 자리 · 실패를 숨기지 않음 · names.json staging).

## 영수증(head 71324eed)
- BOOST-D CI(pull_request) https://github.com/ppx109-crypto/stock-dash/actions/runs/42418878975 — `D 묶음 시험(필수)` success(모은 342개 = 고정 342개 · 시험 파일 · 시험 자료 지문 17개 같음 · 실패 · 오류 · 건너뜀 0) · `전체 시험 차이 검사` success(기준 `26d0fdf7` 821개 · 지금(PR 병합 판 `f649cf7d`) 966개 · 건너뜀 0 / 0 · 기준 · 지금 실패 모두 `test_kiwoom_ui.KiwoomLab.test_trio_board` 하나 · 불변식 다섯 맞음 · artifact `test-diff` 13592372810).
- BOOST-D CI(push) https://github.com/ppx109-crypto/stock-dash/actions/runs/42418874803 — 두 job success.
- 달력 마른 실행(이 head) https://github.com/ppx109-crypto/stock-dash/actions/runs/42418878958 — success(위 B).
- 기존 Tests(check.yml) https://github.com/ppx109-crypto/stock-dash/actions/runs/42418878974 — failure: 차이 검사의 기준 · 지금 실패 집합과 같은 기존 실패 하나(`test_kiwoom_ui` · 키움 개발실 시험이라 건드리지 않음).
- 로컬: D 묶음 고정 대조 342개 green · 전체 차이 검사 green(기준 `5d032d51` 821개 · 지금 966개 · 건너뜀 0 · 불변식 모두 맞음) · 고친 파일 함정 꼴 21 → 21.

## 묻는 것
1. A · B · C · D 반영이 판 3을 충족하는지.
2. E의 고침 4가지 + 방어 1가지를 D 범위에 넣는 것(사전등록 판 3 결함의 실행 꼴을 고친 것 · 잣대 · 분모 그대로).
3. 지평을 옮길 때마다 새 판 sha → ARMED 다시 확인: '새 위험 없는 첫 실행 영수증'을 매번 다시 요구하는지, 아니면 첫 부트스트랩 뒤에는 '마른 실행 후보 sha = 만든 판 sha + 시작 전 점검 통과 + session_review 갱신'으로 충분한지(지평을 옮길 때마다 하루씩 닫히는 날을 줄이려고).

후보 채택 · 시험 참가 · 운영 · 배분 · 주문 · 실전 계좌 변경은 사용자 직접 승인만 유효합니다. 한투 하루 / 달력월 TWR −15% · 키움 미니코스피 1계약 장 끝 하루 −15p · 비밀정보 비공개를 유지합니다.

---
_Generated by [Claude Code](https://claude.ai/code)_
