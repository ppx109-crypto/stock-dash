"""REPLAY-RAW-PRICE-CONTRACT-0001 · data-contract.json · unknown-reasons.json 만들기(네트워크 없음).
python3 -E -P contract_evidence.py <target-coverage.json> <수집 계획.json> <출력 폴더>"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import raw_replay as R
TC, PLAN, OUT = sys.argv[1:4]
tc, plan = json.load(open(TC)), json.load(open(PLAN))
OUT = Path(OUT)
contract = {
 "scope": tc["scope"], "targets": {k: tc[k] for k in ("fills", "by_sleeve_side", "classes", "unique_code_date", "unique_codes", "unique_dates", "off_tick_unique_code_date")},
 "inputs_to_adapter": {
  "fills": "fill_id · sleeve(D1|BASKET) · date · code(로컬) · side · intent(buy: notional 원 · sell: fraction 또는 qty)",
  "raw": "check_raw_pair 결과(날짜별 close · status) — RAW와 ADJUSTED 같은 요청 쌍",
  "ca": "resolve_ca 결과(정정 사슬 · 필수 칸 · same_day_pit)",
  "rate": "kernel2.Costs(cost_contract · 비용 2배) rate(side, code, day, notional)",
  "cash0_and_days": "소계정 250만 원 · Train 거래일 달력"},
 "intent_mapping_for_real_run(다음 TASK)": "PR #76 원장의 수정 기준 수량을 그대로 쓰지 않음. buy notional = PR #76 목표의 금액(수정 수량 × 수정 종가)을 의도 금액으로 · sell = 그 시점 보유 대비 비율. 이 매핑은 실제 원주가 · 기업행동이 있을 때 별도 TASK에서 고정.",
 "invariants": ["체결가 = 그날 공식 원주가 종가 · 호가 배수(아니면 INVALID_OFFICIAL_RAW · 체결 안 함)",
                "매수 수량 = floor(min(의도 금액, 현금 한도)/원주가) · 비용 포함 현금 ≥ 0",
                "매도 수량 ≤ 기업행동 조정 뒤 보유(넘으면 SELL_CAPPED)",
                "비용 · 세금 = 원주가 × 원수량 × rate",
                "일별 MTM = 원주가 종가 × 실제 수량(값 없으면 STALE 표시)",
                "기업행동 = 효력일 장 시작 전 CA_QTY · CA_CASH 레코드",
                "기말현금 = 기초 − 매수대금 − 매수비용 + 매도대금 − 매도비용 + 명시적 현금조정(두 경로 비교)",
                "기말수량 = 매수 − 매도 + 명시적 수량조정 · 음수 0",
                "on-tick 125건을 원주가로 간주하지 않음 · off-tick을 가까운 호가로 반올림하지 않음"],
 "public_local_boundary": {"public": ["개수 · 비율", "salted hash(fill_id → sha(code|date|side) 앞 16자)", "salt sha256", "schema 검증 결과", "파일 · 요청 sha256"],
                           "local_only_not_committed": ["targets_local_only.json(실제 종목 · 날짜 · 수량 · 저장 종가)", "salt", "API 응답 원문 · 캐시", "보고서명 · 원문"]},
 "next_real_run": {"credentials": plan["credential_names"], "kis_calls_upper": plan["kis_calls_upper"], "dart_calls_upper": plan["dart_calls_upper"],
                   "caps": {"KIS": plan["kis_cap"], "DART": plan["dart_cap"]}, "within_caps": plan["within_caps"],
                   "environment": "이 세션 환경변수 주입(현재 없음 · PR #82) · 네트워크 허용(openapi.koreainvestment.com:9443 · opendart.fss.or.kr)은 실행 TASK에서 확인",
                   "forbidden": plan["forbidden_endpoints"]},
 "external_calls_this_task": 0, "train_replay_runs_this_task": 0}
unknown = {"codes": R.UNKNOWN,
           "current_148_status": {"UNKNOWN_NEEDS_OFFICIAL_RAW(공식 원주가 없음 · 이번 TASK에서 받지 않음)": tc["fills"],
                                  "of_which_IMPOSSIBLE_RAW_FILL_priority": tc["classes"].get("IMPOSSIBLE_RAW_FILL", 0),
                                  "of_which_UNKNOWN_RAW_OR_ADJUSTED": tc["classes"].get("UNKNOWN_RAW_OR_ADJUSTED", 0)},
           "rule": "공식 필드 없으면 추정 · 반올림으로 채우지 않고 위 코드로 남김"}
(OUT / "data-contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=1))
(OUT / "unknown-reasons.json").write_text(json.dumps(unknown, ensure_ascii=False, indent=1))
print("계약 · UNKNOWN 표 작성")
