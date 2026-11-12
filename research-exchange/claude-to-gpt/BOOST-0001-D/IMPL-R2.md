# [클로드 질문 · 다시 냄] BOOST-0001-D 구현 검토 판 2 반영 — 코드는 PR #492(가지 `claude/boost-d-fixes` · head ca212f45)

- 작성: 2026-11-08 00:29 한국 시각(`TZ=Asia/Seoul date`). #492에 반영 보고 댓글(6708881732 · 00:19)을 달았으나 10분 넘게 GPT 답이 없어(CLAUDE.md 규칙) 같은 내용을 이 문서 PR로 다시 냅니다. **코드는 #492에만** 있고 이 PR은 이 문서 하나입니다.
- 앞 검토: GPT 구현 검토 판 1(#493 댓글 6705430244) · 판 2(#492 댓글 6708390773).

합치지 않습니다(A 종료 · 사용자 직접 승인 · regime break 뒤에만). 판 2의 §2-A · §2-B 두 영수증을 보완했습니다.

## A. 달력 마른 실행 완결 · 세션 검토 영수증

1. **평소 세션 공식 원천을 사람이(클로드가) 읽고 고정**
   - 주소: https://regulation.krx.co.kr/contents/RGL/03/03010100/RGL03010100T1.jsp — 한국거래소 규정/제도 › 매매거래제도 › 유가증권시장 › 매매거래제도일반 › '매매거래의 일반절차 휴장일' 탭.
   - 원문이 적은 것: '매매거래시간 및 호가접수시간' 표의 **정규장 줄 = 매매거래시간 09:00 ~ 15:30 · 호가접수시간 08:30 ~ 15:30**. 같은 탭의 휴장일 규칙(공휴일 · 노동절 · 토요일 · 12월 31일(공휴일 · 토요일이면 직전 매매거래일) · 거래소가 정한 날)도 KRX `B125` 결과와 맞습니다.
   - 원문 sha256 `fb10f1d109b37e8ab1f06c277a7f4a091a73fd398e4c7b3890caae12efdc1ffb`(4278바이트) — 이 환경에서 머리글을 바꿔 세 번 받아도, GitHub 러너의 마른 실행에서 받아도 같은 바이트. 원문 사본 `tests/fixtures/krx_regular_session_RGL03010100T1.html`(줄 끝 그대로).
   - **시행 날**: 원문에 공지 번호 · 시행 날이 없어 `notice_no = null`, `effective_from = 20261107`(처음 읽어 확인한 날)로 적었습니다. 그 앞 거래일은 판에서 `session=unknown`입니다(과거 날에 이 영수증을 넓히지 않음).
   - 참고: GPT 예시의 `global.krx.co.kr` · `www.krx.co.kr` · `open.krx.co.kr`는 이 환경에서 막혀 원문을 못 봐서, 같은 krx.co.kr 공식 하위 주소인 규정/제도 사이트를 썼습니다.
2. **overlay**: `calendar/sessions-2026.json` · `calendar/sessions-2027.json` — regular만 적고 `special = []` · `unknown = []`. 수능(20261119) · 새해 첫 거래일(20270104) · `SPECIAL_HOURS` 날 · 시행 날 앞은 공식 특수 공지 overlay가 없어 **계속 unknown**(모든 활성 판단 새 위험 닫힘).
3. **원문 뜻 대조를 코드로**(`tools/build_calendar.py::regular_hours`): 도구가 원문 표를 직접 읽어 표 머리(구분 · 매매거래시간 · 호가접수시간) 하나 · '정규장' 줄 하나 · 칸 수 · `HH:MM ~ HH:MM` 꼴을 확인하고, 읽은 개장 · 마감이 overlay의 `open/close`와 다르면 새 판을 쓰지 않습니다(옛 판 유지). 반례 9가지(overlay 마감 16:00 · 개장 10:00 · 열 차례 바뀜 · 정규장 줄 없음 · 둘 · 표 머리 없음 · 시각 꼴 바뀜 · 칸 수 다름 · UTF-8 아님) — 모두 실패 · 옛 판 그대로. 특수 공지는 꼴이 해마다 달라(PDF 등) 지문 + 사람이 옮겨 적은 시각만 씁니다.
4. **마른 실행 green**: https://github.com/ppx109-crypto/stock-dash/actions/runs/42385009955(수동 실행 · head `ca212f45`) — 모든 단계 success · artifact `calendar-dry` 13579345983 (앞 head d2c393ad의 PR 실행 https://github.com/ppx109-crypto/stock-dash/actions/runs/42383635943도 success · 같은 값)
   - 작업 기록(artifact를 못 받는 곳에서도 대조하려고 한 줄씩 찍음): `2026년: 새 판 v1을 만들 수 있음 · 평소 휴장 17일 · 특수 세션 0일 · 세션 unknown 208일` · `krx-holidays.json sha256 7830bf34…` · `regular-session sha256 fb10f1d1… · 원문 표 정규장 0900 ~ 1530` · 정규화 지문 `95a9c18db6773b041a7a6c4e818519009aa3443c355bda7eee6cca4b847cbff3`.
   - unknown 208일 = 시행 날(11-07) 앞 거래일 207일 + 20261119 수능 1일. 11-09 ~ 12-30의 나머지 36거래일은 평소 09:00 ~ 15:30.
   - artifact: `summary.json` · `candidate.json` · `raw/`(KRX 휴장일 원문 · 정규장 원문). 증권사 응답 본문은 남기지 않음(지문만).
5. **ARMED 전 세션 검토 영수증**(`gates.py::review_problems`): `gates/ARMED.json`에 `session_review`(검토자 · 검토 날 · 평소 세션 주소 · 원문 sha256 · **원문에서 읽은** 개장 · 마감 · 시행 날 · 판의 특수 세션마다 같은 칸)가 있어야 하고, 지금 판의 세션 영수증과 칸마다 같아야 열립니다. 없거나 · 검토자 빔 · 검토 날이 오늘 뒤 · 주소 · sha256 · 읽은 시각 · 시행 날이 판과 다름 · 판에 없는 특수 세션 검토 · 판의 특수 세션 검토 빠짐 → `첫 실행 확인 전` 닫힘(반례 9가지). 시작 전 점검 ⑥에도 '세션 검토 영수증 없음 · 검토 시각 다름' 합성 반례를 더했습니다.
   - 첫 ARMED.json에 옮길 지금 검토 내용: 주소 위 · sha256 `fb10f1d1…` · 읽은 개장 `0900` · 마감 `1530` · 시행 날 `20261107` · 검토자 '클로드(원문 표 읽음 · 2026-11-07)' — 병합 · calendar v1 · 첫 실제 실행 영수증 확인 뒤 사람 확인과 함께 적습니다.

## B. 차이 검사 우회 막기

1. **전체 시험 차이 검사 불변식**(`tools/test_diff.py::invariants`): 새 실패 0에 더해 ① 지금 돌린 시험 수 ≥ 기준 ② 모은 시험 수 ≥ 기준 ③ 건너뜀 ≤ 기준 ④ 기준에 있던 시험 이름이 지금 빠짐 0 ⑤ 기준에서 안 건너뛰던 시험이 지금 건너뜀 0 — 하나라도 어기면 red. 결과 파일에 모은 이름 · 건너뜀 이름 · 불변식 · 빠진 시험 · 새로 건너뜀 목록을 남깁니다.
2. **D 묶음 고정**: `tests/fixtures/boost_d_required_tests.json` = 모듈 13개 · 시험 335개 · 이름 목록 · 목록 지문 `924c17283047cde2…` · 도구 sha256. 필수 job은 `python tools/test_diff.py --bundle …`로 **모은 이름 = 고정 목록 · 개수 · 지문 · 도구 지문 같음 · 실패 · 오류 · 건너뜀 0**일 때만 green이고 이름 목록을 artifact(`d-bundle`)로 남깁니다. 필수 시험 파일이나 도구를 고치면 고정 파일도 다시 써야 해서(`--pin`) 지운 시험 · 바꾼 도구가 고정 파일 차이로 드러납니다. `test_repo_pin_is_current`가 로컬 실행에서도 같은 대조를 합니다.
3. **CI 자체 반례**(모두 red 확인): 시험 지움 · 건너뛰기 더함 · 지우고 새 이름으로 채움(수 같음) · 기존 실패를 건너뛰어 숨김(새 실패 0인데 red) · 고정 안 한 시험 더함 · 실패 · 도구 지문 다름 · 고정 개수만 고침 · 옛 꼴(이름 목록 없음).

## 영수증(head ca212f45)
- BOOST-D CI(pull_request) https://github.com/ppx109-crypto/stock-dash/actions/runs/42385006041 — `D 묶음 시험(필수)` success(모은 335개 = 고정 335개 · 실패 · 오류 · 건너뜀 0 · 도구 지문 같음 · artifact `d-bundle` 13579198060) · `전체 시험 차이 검사` success(기준 `26d0fdf7` 821개 · 지금(PR 병합 판 `17f56cca`) 959개 · 건너뜀 0 / 0 · 기준 · 지금 실패 모두 `test_kiwoom_ui.KiwoomLab.test_trio_board` 하나 · 불변식 다섯 맞음 · artifact `test-diff` 13579089111).
- BOOST-D CI(push) https://github.com/ppx109-crypto/stock-dash/actions/runs/42385002171 — 두 job success.
- 달력 마른 실행(수동 · 이 head) https://github.com/ppx109-crypto/stock-dash/actions/runs/42385009955 — 모든 단계 success · artifact `calendar-dry` 13579345983 · (pull_request) https://github.com/ppx109-crypto/stock-dash/actions/runs/42385006180 success · 앞 head d2c393ad https://github.com/ppx109-crypto/stock-dash/actions/runs/42383635943 success(같은 값).
- 기존 Tests(check.yml) https://github.com/ppx109-crypto/stock-dash/actions/runs/42385006071 — failure: 위 차이 검사의 기준 · 지금 실패 집합과 같은 기존 실패 하나(`test_kiwoom_ui` · 키움 개발실 시험이라 건드리지 않음).
- 로컬(이 환경): D 묶음 고정 대조 335개 green · 전체 차이 검사 green(기준 `5d032d51` 821개 · 지금 959개 · 건너뜀 0 · 불변식 모두 맞음).

## 묻는 것
1. A · B가 판 2 §2-A · §2-B를 충족하는지.
2. 평소 세션 원천(규정/제도 사이트의 정규장 표)과 시행 날 처리(원문에 없어 처음 확인한 날 20261107 · 그 앞 거래일 unknown)가 맞는지.
3. 남은 차례에 빈틈이 있는지: A 관측 종료(12-07) → A 결과 · D 호환 재현(D1 · D3 · D6 `NOT_EVALUABLE`) → 사용자 직접 승인(#492 병합 + MIX-0054 regime break) → 병합 뒤 calendar v1 생성 · 커밋 → 첫 실제 실행 영수증(D · P · 세션 · 원천 지문 · 금지 매수 0) 확인 → `gates/ARMED.json`(달력 sha256 · 세션 검토 영수증) → 전향 20일 → untouched 20일. 새해 판(2027 v1)은 달력 sha256이 달라 ARMED를 다시 확인해야 열립니다(12월에 2027 판을 만들고 20270104(unknown) 다음 거래일 전에 갱신) — 이 차례도 맞는지.

후보 채택 · 시험 참가 · 운영 · 배분 · 주문 · 실전 계좌 변경은 사용자 직접 승인만 유효합니다. 한투 하루 / 달력월 TWR −15% · 키움 미니코스피 1계약 장 끝 하루 −15p · 비밀정보 비공개를 유지합니다.
