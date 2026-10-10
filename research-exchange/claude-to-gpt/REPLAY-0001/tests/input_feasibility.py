"""기존 495행 장부(RULES-0002@a61f033 d1_ledger_ASIS.csv)의 스키마 · 필수 필드 · 부분청산 묶음만 한 번 선형으로 점검.
사용: python3 -I tests/input_feasibility.py <csv 경로> <결과 json>
가격 캐시 · 새 원장 · API를 찾지 않음. 빠진 필드를 채우지 않음."""
import sys, csv, json, hashlib
P, OUT = sys.argv[1], sys.argv[2]
raw = open(P, "rb").read()
sha = hashlib.sha256(raw).hexdigest()
rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
cols = list(rows[0].keys()) if rows else []
groups, multi_exit, bad_dates, entry_eq_exit, slots = {}, 0, 0, 0, {}
for r in rows:  # 한 번 선형
    groups.setdefault((r["code"], r["entry"]), []).append(r)
    if not (len(r["entry"]) == 8 and r["entry"].isdigit() and len(r["exit"]) == 8 and r["exit"].isdigit()):
        bad_dates += 1
    if r["entry"] == r["exit"]:
        entry_eq_exit += 1
    slots[r["slots"]] = slots.get(r["slots"], 0) + 1
multi = {k: v for k, v in groups.items() if len(v) > 1}
multi_distinct_exit = sum(1 for v in multi.values() if len({x["exit"] for x in v}) > 1)
REQ = {
 "fill_id": None, "trade_id": "없음(code+entry 묶음으로 원 거래 후보만 만들 수 있음, 확정 id 아님)",
 "strategy_id": None, "security_id": "code", "at(시각+tz)": "entry/exit 날짜만(YYYYMMDD), 시각 · 시간대 없음",
 "side": "열 이름으로 추정 가능(entry=매수, exit=매도)", "qty": None, "price(체결가)": None,
 "fee/tax": None, "settle_date": None, "order_id": None,
 "ledger_pnl_pct": "pnl_pct_engine(대사 참고값만, 현금 계산에 쓰지 않음)",
 "alloc(칸)": "slots(칸 수, 주문 한도 원 금액 아님)"}
have = {"fill_id": "없음", "trade_id": "없음(후보만)", "strategy_id": "없음", "security_id": "있음",
        "at(시각+tz)": "날짜만", "side": "추정", "qty": "없음", "price(체결가)": "없음", "fee/tax": "없음",
        "settle_date": "없음", "order_id": "없음", "ledger_pnl_pct": "있음(참고만)", "alloc(칸)": "칸 수만"}
missing_required = ["at(시각+tz)", "qty", "price(체결가)"]
doc = {"task": "REPLAY-0001", "source": "RULES-0002@a61f033ecd16ba0976c955a93bfec70c7463ad53 "
       "research-exchange/claude-to-gpt/RULES-0002/results/d1_ledger_ASIS.csv",
       "sha256": sha, "rows": len(rows), "rows_expected": 495, "rows_match": len(rows) == 495,
       "columns": cols, "date_format_bad_rows": bad_dates, "entry_equals_exit_rows": entry_eq_exit,
       "slots_counts": dict(sorted(slots.items())),
       "groups_code_entry": len(groups), "groups_with_multiple_rows": len(multi),
       "rows_in_multi_groups": sum(len(v) for v in multi.values()),
       "multi_groups_with_distinct_exits": multi_distinct_exit,
       "partial_exit_link": "같은 (code, entry) 묶음의 여러 행은 부분청산 후보. 원 장부에 trade_id가 없어 확정 연결 불가 — "
                            "커널에 넣는다면 한 진입 + 여러 출구로 묶어야 하며 독립 매수로 늘리면 안 됨",
       "kernel_fields": REQ, "kernel_field_status": have,
       "missing_required_per_row": missing_required,
       "rows_missing_required": len(rows),
       "row_status": "모든 행 MISSING_REQUIRED(체결 시각 · 체결가 · 수량 없음). 채우지 않음",
       "historical_replay": "BLOCKED_NEEDS_DATA",
       "next_required_inputs": ["체결 시각(+09:00)과 순서", "체결 수량(정수)", "체결가(Decimal)",
                                "체결별 수수료 · 세금 또는 출처가 밝혀진 비용 모형", "trade_id · strategy_id(가명)",
                                "평가 가격의 as_of · available_at · version", "외부 입출금 시각과 금액"],
       "result": "READY(점검 끝) / 역사 재생 BLOCKED_NEEDS_DATA",
       "not_done": "가격 캐시 · 새 원장 · API 조회 · 전체 가격 재생 안 함"}
json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(sha, len(rows), cols, len(groups), len(multi), multi_distinct_exit, entry_eq_exit, bad_dates)
