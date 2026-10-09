"""REPLAY-OFFICIAL-SEMANTICS-AUDIT-0001 · 판정 파일 생성(사전등록 §2 규칙 그대로 · 계산 없음 · 호출 없음).
python3 -I verdicts.py <_facts.json> <출력 폴더>"""
import json
import sys
from pathlib import Path

F = json.load(open(sys.argv[1]))
OUT = Path(sys.argv[2])
DF, KQ, KSD = F["detail_fields"], F["kis_q"], F["KSD"]
fk = lambda kind: [f'{x["key"]}({x["name"]})' for x in DF[kind]["date_ratio_fields"]]

# ═════ A. KIS ═════
kis = {
    "tier_note": "KIS Developers 포털(apiportal.koreainvestment.com)은 이 환경 정책으로 차단 → 사전등록 §1대로 한국투자증권 공식 저장소(open-trading-api, README '당사에서 제공하는 샘플코드 · 참고용')의 명시 문구로 판정. 포털 원문 대조는 못 함.",
    "items": [
        {"id": "A1", "claim": "endpoint · TR ID", "quotes": [KQ["api_name"], KQ["endpoint"], KQ["tr_id"]], "verdict": "ACCEPT"},
        {"id": "A2", "claim": "FID_ORG_ADJ_PRC 값 방향", "quotes": [KQ["adj_flag"]], "value_map": {"0": "ADJUSTED(수정주가)", "1": "RAW(원주가)"},
         "pr88_schema": {"1": "RAW", "0": "ADJUSTED"}, "verdict": "ACCEPT", "note": "PR #88 스키마와 같은 방향 · 저장소 broker_kis.py 300줄과도 일치"},
        {"id": "A3", "claim": "한 응답 행 수 · 연속조회", "quotes": [KQ["row_limit"], KQ["date2_limit"], KQ["no_cont_in_call"]],
         "verdict": "ACCEPT(최대 100건 · 이 API 예제는 연속조회 키 없이 호출)",
         "unknown": "기간이 100거래일을 넘을 때 어느 100건을 돌려주는지(앞/뒤) 문서에 없음 → UNKNOWN_KIS_DOC_SEMANTICS",
         "fail_closed": "창 하나는 거래일 100일 이하로 자름 · 응답이 정확히 100건이면 잘렸을 수 있으므로 창을 다시 나눠 재조회(동적 예산에 포함)"},
        {"id": "A3b", "claim": "시장 코드", "quotes": [KQ["market"], KQ["period"]], "verdict": "ACCEPT", "rule": "원주가 종가는 J(KRX) · D(일봉)로 고정. NX(NXT) · UN(통합) 금지"},
        {"id": "A4", "claim": "응답 날짜 · 종가 · 락 칸", "quotes": [KQ["f_date"], KQ["f_close"], KQ["f_lock"], KQ["f_prtt"], KQ["f_mod"]],
         "verdict": "ACCEPT(칸 이름)", "needs_data": ["flng_cls_code 값 목록(락 구분 코드 뜻)", "prtt_rate · mod_yn 값 뜻", "거래정지일 · 무거래일이 행 없음인지 · 같은 가격 행인지"],
         "verdict_needs": "NEEDS_DATA"},
        {"id": "A5", "claim": "33종목 원/수정 호출식", "quotes": [KQ["token"]],
         "formula": "base = 1(토큰 · 유효 1일 · 6시간 안 재발급 같은 값) + Σ_code 2 × ⌈N_code ÷ 100⌉, N_code = 그 종목에 필요한 거래일 수",
         "example_if_all_132_days": {"base": 1 + 33 * 2 * 2, "worst_retry2": (1 + 33 * 2 * 2) * 3, "cap": 500},
         "verdict": "ACCEPT(식) · 숫자는 거래일 달력 · 잘림 재조회에 따라 동적"},
    ],
    "pr88_contract_changes": ["market=J 고정을 스키마 const로(REVISE)", "응답 100건이면 잘림 의심 → 창 다시 나눔(REVISE)", "flng_cls_code · prtt_rate · mod_yn은 저장만 하고 뜻이 확인될 때까지 판단에 안 씀"]}

# ═════ B. DART 사건 경로 ═════
LISTQ = F["list_q"]
corr_common = {"original_link_field": "없음(list 응답 칸 17개에 원 접수번호 칸 없음)", "list_markers": [LISTQ["report_nm_correction"], LISTQ["rm_correction"]],
               "available_at_precision": LISTQ["rcept_dt"], "detail_api_version": F["detail_req"] + " → 상세 응답이 어느 정정 버전인지 가이드에 없음",
               "verdict": "UNKNOWN_CA_VERSION_PIT"}
events = []
for kind, ko in (("split", "주식 액면분할"), ("reverse_split", "주식병합")):
    events.append({"kind": kind, "ko": ko, "structured_opendart": "없음(OpenDART 6그룹 85개 API 전체 목록에 주식분할 · 병합 · 액면교체 이름 0개)",
                   "structured_verdict": "ACCEPT(없음 증명)", "not_same_as": "회사분할(cmpDvDecsn · 2020051)과 다른 사건",
                   "list_filter": {"available": [LISTQ["pblntf_ty_I"], LISTQ["I001"]], "report_nm_for_this_event": "공식 근거 없음(KRX 공시규정 · KIND 차단)",
                                   "verdict": "BLOCKED_NO_OFFICIAL_EVIDENCE"},
                   "document_path": {"quote": F["doc_q"], "verdict": "ACCEPT(경로) · NEEDS_DATA(원문 안 칸 구조 미공개)"},
                   "alt_official_source": {"api": KSD["ksdinfo_rev_split"]["title"], "fields": KSD["ksdinfo_rev_split"]["fields"],
                                           "ratio_note": "비율 칸 없음 · 변경전/변경후 액면가만 있음(비율로 바꾸는 식은 공식 근거 없음 → NEEDS_DATA)",
                                           "pit": "공개 시각 · 접수번호 칸 없음 → UNKNOWN_CA_VERSION_PIT", "verdict": "REVISE(일정 출처 후보로 추가) · PIT는 미확정"},
                   "correction_chain": corr_common, "fail_closed_reason": "BLOCKED_UNMAPPED_KIND(DART 탐지 경로 미확정)",
                   "overall": "BLOCKED_NO_OFFICIAL_EVIDENCE"})
ROWS = (("capital_reduction", "감자"), ("bonus_issue", "무상증자"), ("rights_issue", "유상증자"), ("rights_bonus_issue", "유무상증자"),
        ("merger", "합병"), ("spinoff", "회사분할"), ("spinoff_merger", "회사분할합병"))
KSD_FOR = {"capital_reduction": "ksdinfo_cap_dcrs", "bonus_issue": "ksdinfo_bonus_issue", "rights_issue": "ksdinfo_paidin_capin",
           "rights_bonus_issue": "ksdinfo_bonus_issue+ksdinfo_paidin_capin", "merger": "ksdinfo_merger_split", "spinoff": "ksdinfo_merger_split",
           "spinoff_merger": "ksdinfo_merger_split"}
for kind, ko in ROWS:
    d = DF[kind]
    missing = [n for n, ok in (("기준일", d["has_record_date"]), ("상장예정일", d["has_listing_date"]), ("권리락일", d["has_ex_rights_date"]),
                                ("매매거래정지기간", d["has_halt_period"])) if not ok]
    events.append({"kind": kind, "ko": ko, "structured_opendart": f'{d["endpoint"]}(apiId {d["apiId"]})', "structured_verdict": "ACCEPT",
                   "official_fields": fk(kind), "missing_official_fields": missing,
                   "list_filter": {"pblntf_ty": "B(주요사항보고) · B001", "verdict": "ACCEPT(유형 코드)"},
                   "alt_official_source": {"api": KSD_FOR[kind], "pit": "공개 시각 칸 없음 → UNKNOWN_CA_VERSION_PIT"},
                   "correction_chain": corr_common,
                   "fail_closed_reason": ("NEEDS_DATA(구조화 칸에 기준일 · 발행가 · 상장일 없음 → 원문 또는 KIS 예탁원 일정)" if kind == "rights_issue" else
                                          "UNKNOWN_CA_VERSION_PIT(정정 사슬) · 권리락일은 DART 칸에 없음"),
                   "overall": "REVISE" if kind != "rights_issue" else "NEEDS_DATA"})
dart_map = {"events": events, "common": {"list_page_count": LISTQ["page_count"], "list_last_reprt_at": LISTQ["last_reprt_at"],
            "rule_last_reprt_at": "반드시 N(정정 포함 전체) — Y는 지금 기준 최종본만 줘서 미래 정정을 과거에 쓰게 됨",
            "list_corp_code": LISTQ["bgn_de_limit"], "rcept_no": LISTQ["rcept_no"]},
            "summary": {"structured_api_exists": [e["kind"] for e in events if e["structured_verdict"] == "ACCEPT" and "없음" not in e["structured_opendart"]],
                        "no_structured_api": ["split", "reverse_split"], "split_vs_spinoff": "다른 사건으로 분리(ACCEPT)"}}

# ═════ C. 날짜 · 수량 · 매도 가능 ═════
SEM = []
for kind, ko in (("split", "액면분할"), ("reverse_split", "주식병합"), ("capital_reduction", "감자"), ("bonus_issue", "무상증자"),
                 ("rights_issue", "유상증자"), ("rights_bonus_issue", "유무상증자"), ("merger", "합병"), ("spinoff", "회사분할"), ("spinoff_merger", "회사분할합병")):
    avail = {"split": "KIS 액면교체: 기준일 · 매매거래정지기간 · 상장/등록일", "reverse_split": "KIS 액면교체: 기준일 · 매매거래정지기간 · 상장/등록일",
             "capital_reduction": "DART: 감자기준일 · 매매거래 정지예정기간 · 신주상장예정일 / KIS: 기준일 · 매매거래정지기간 · 상장/등록일",
             "bonus_issue": "DART: 신주배정기준일 · 신주의 상장 예정일 / KIS: 기준일 · 권리락일 · 상장/등록일",
             "rights_issue": "DART: (없음) / KIS: 기준일 · 권리락일 · 발행예정가 · 상장/등록일",
             "rights_bonus_issue": "DART: 무상분 신주배정기준일 · 상장 예정일 / KIS: 위 둘",
             "merger": "DART: 합병기일 · 매매거래 정지예정기간 · 신주의 상장예정일 / KIS: 기준일 · 매매거래정지기간 · 상장/등록일",
             "spinoff": "DART: 분할기일 · (감자 시) 매매거래정지 예정기간 · 신주의 상장예정일 / KIS: 합병_분할일정",
             "spinoff_merger": "DART: 분할합병기일 · (감자 시) 매매거래정지 예정기간 · 신주의 상장예정일"}[kind]
    SEM.append({"kind": kind, "ko": ko, "official_date_fields": avail,
                "t1_price_basis_first_trading_day": {"verdict": "BLOCKED_NO_OFFICIAL_EVIDENCE",
                                                     "why": "어느 날 원주가 기준이 바뀌는지(권리락일 · 거래 재개일)를 정의하는 KRX 규정 원문 차단. 칸 이름(권리락일 · 매매거래정지기간)만으로 뜻을 정하지 않음"},
                "t2_legal_effective": {"verdict": "BLOCKED_NO_OFFICIAL_EVIDENCE", "why": "기준일 · 효력일 · 합병/분할기일 중 법적 발생일을 정하는 근거(상법 · KRX)는 이번 허용 출처 밖이거나 차단"},
                "t3_first_sellable": {"verdict": "BLOCKED_NO_OFFICIAL_EVIDENCE", "why": "상장/등록일 · 신주의 상장 예정일이 매도 가능 첫날인지 공식 문구 없음(필드 이름뿐)"},
                "pr88_rule": {"price_basis_date_apply": "BLOCKED_NO_OFFICIAL_EVIDENCE", "listing_date_lock": "BLOCKED_NO_OFFICIAL_EVIDENCE",
                              "revise": "price_basis_date · listing_date마다 출처 칸(source_field)과 근거 등급을 레코드에 남기고, 근거 미확정이면 그 사건이 걸린 종목은 NAV 무효(PR #88 게이트)로 유지"},
                "data_side_check": "실제 수집 TASK에서 KIS 일봉 flng_cls_code(락 구분) · prtt_rate가 찍힌 날과 위 날짜 칸을 대조하는 검사는 가능(값 뜻은 NEEDS_DATA)"})
date_sem = {"events": SEM, "overall": "BLOCKED_NO_OFFICIAL_EVIDENCE",
            "no_substitution_rule": "권리락일 · 기준일 · 효력일 · 변경상장일을 서로 대체하지 않음(PR #88 price_basis_date를 기준일 · 효력일로 채우지 않음)",
            "unblock_needs": ["law.krx.co.kr(유가증권 · 코스닥 업무규정 · 시행세칙 · 공시규정)", "kind.krx.co.kr(공시 서식 · 매매거래정지 안내)", "apiportal.koreainvestment.com(락 구분 코드 값)"]}

# ═════ D. available_at · 정정 사슬 ═════
pit = {"available_at": {"quote": LISTQ["rcept_dt"], "precision": "date", "verdict": "ACCEPT",
                        "rule": "PR #88 규칙 유지: 날짜만 → 그날 23:59:59로 보아 당일 사용 금지 · 다음 거래일부터. same_day_pit는 DART만으로는 늘 false"},
       "correction_chain": {"quotes": [LISTQ["report_nm_correction"], LISTQ["rm_correction"]], "list_response_keys": F["list_keys"],
                            "original_rcept_field": "없음", "verdict": "UNKNOWN_CA_VERSION_PIT",
                            "pr88_revise": "PR #88 스키마의 root_rcept_no(필수)를 공식 칸에서 채울 수 없음 → 원문(document) 안 정정 대상 표시를 읽는 경로가 공식 문서로 확인될 때까지 정정본이 있는 사건은 UNKNOWN_CA_VERSION_PIT(수량 변경 없음 · NAV 무효)",
                            "not_allowed": ["보고서명 문자열 비교만으로 사슬 확정", "접수번호 앞 8자리를 날짜로 보고 정렬(가이드는 '14자리'만 말함)"]},
       "detail_api_version": {"quote": F["detail_req"], "verdict": "UNKNOWN_CA_VERSION_PIT", "rule": "상세 응답은 같은 rcept_no의 list 행과 맞을 때만 그 버전의 칸으로 씀"},
       "last_reprt_at": {"quote": LISTQ["last_reprt_at"], "rule": "N만 사용(Y 금지)", "verdict": "ACCEPT"},
       "ksdinfo": {"verdict": "UNKNOWN_CA_VERSION_PIT", "why": "예탁원 일정 응답에 공개 시각 칸 없음 → 그 레코드를 그날 알 수 있었는지 모름"}}

# ═════ E. 동적 호출 예산 ═════
budget = {"pseudocode": [
    "cap = {DART: 250, KIS: 500}; used = 0(실제 시도 수, 재시도 포함); RETRY = 2",
    "def allow(n_next): return used + n_next * (1 + RETRY) <= cap   # 각 요청 직전",
    "DART 1단계: corpCode 1 → 종목마다 list(corp_code, bgn_de, end_de, last_reprt_at=N, page_count=100) 첫 쪽",
    "  첫 쪽 total_page 읽고 남은 쪽마다 allow(1) 확인 · 실제 시도 수를 used에 더함",
    "사건 분류: report_nm → kind 표(공식 근거 있는 것만). 표에 없는 보고서명이 하나라도 있으면 2단계 전에 BLOCKED_UNMAPPED_KIND",
    "  (지금은 split · reverse_split 보고서명 근거 없음 → 그런 후보가 보이면 바로 BLOCKED_UNMAPPED_KIND)",
    "2단계: 고유 (종목, endpoint)마다 상세 1 + 정정 확인용 document는 사건마다 1 — 각각 allow(1) 뒤 호출",
    "남은 허용치 = (cap − used) // (1 + RETRY) 를 매 요청 뒤 다시 셈. 72는 1단계가 34회 · 재시도 0으로 끝났을 때의 예시일 뿐 고정 허용치 아님",
    "KIS: 토큰 1 → 종목마다 원/수정 창(거래일 ≤100)마다 allow(1) · 응답 100건이면 창 반으로 나눠 다시(추가 시도도 used)",
    "KIS 예탁원 일정(채택 시): tr_cont=='M'이면 다음 쪽 — 쪽마다 allow(1)",
    "어느 단계든 allow 실패 → 그 요청 0회로 멈추고 BLOCKED_CALL_BUDGET · 이미 받은 것은 캐시 해시만 기록"],
    "table": [
        {"part": "DART 1단계", "base": "1 + Σ_code total_page(code) (최소 1 + 33 = 34)", "worst": "base × 3 (최소 102)"},
        {"part": "DART 2단계", "base": "고유 (종목, endpoint) + 원문 확인 사건 수 — 1단계 결과로만 셈", "worst": "base × 3 · 남은 cap 안이어야 시작"},
        {"part": "KIS 시세", "base": "1 + Σ_code 2 × ⌈N_code/100⌉ + 잘림 재조회", "worst": "base × 3 (전 종목 132거래일이면 133 → 399)"},
        {"part": "KIS 예탁원(선택)", "base": "API 수 × 쪽 수(tr_cont)", "worst": "base × 3"}],
    "api_calls_this_task": 0}

# ═════ F. 148 경계 ═════
boundary = {"done": "기존 체결 148건 각각을 PR #76 판단일 목표 수량 의도로 결정적 매핑(PR #88)",
            "not_done": "전체 판단일 목표 D1 542 · BASKET 154(날 × 종목)를 원주가로 다시 환산한 재생",
            "consequence": "원주가 환산 floor 차이 · 기업행동 · 현금 한도로 PR #76에 없던 주문이 생기거나 있던 주문이 사라질 수 있음",
            "contract": "후속 실제 재생의 분모는 '기존 148'로 고정하지 않음 — 결정 기록 전체로 재생하고 EXTRA · VANISHED 주문을 따로 셈",
            "this_task": "전체 의도 파일 생성 · 재생 · 성과 계산 0"}

OUT.mkdir(parents=True, exist_ok=True)
date_sem["available_at_and_corrections"] = pit
for n, o in (("kis-basis-contract", kis), ("dart-event-source-map", dart_map), ("date-semantics-verdict", date_sem),
             ("dynamic-call-budget-contract", {"budget": budget, "decision_ledger_boundary": boundary})):
    (OUT / f"{n}.json").write_text(json.dumps(o, ensure_ascii=False, indent=1))
print(json.dumps({"kis": [(i["id"], i["verdict"]) for i in kis["items"]], "dart": [(e["kind"], e["overall"]) for e in events],
                  "dates": date_sem["overall"], "pit": [pit["available_at"]["verdict"], pit["correction_chain"]["verdict"]]}, ensure_ascii=False))
