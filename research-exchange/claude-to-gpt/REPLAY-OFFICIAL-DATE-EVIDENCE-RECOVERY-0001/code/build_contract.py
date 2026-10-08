"""REPLAY-OFFICIAL-DATE-EVIDENCE-RECOVERY-0001 · 판정 JSON 생성(계산은 요일 셈뿐 · 호출 없음).
python3 -I build_contract.py <access.jsonl> <출력 폴더>"""
import datetime as dt
import json
import sys
from pathlib import Path

ACC = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
OUT = Path(sys.argv[2])
ok = {a["id"]: a["http"] == "200" and a["bytes"] > 1000 for a in ACC}
assert not any(ok.values()), "원문을 받은 항목이 있으면 이 판정표가 아니라 원문 인용 판정을 써야 함"
TIER = "GPT_CAPTURED_OFFICIAL_INDEX"
U = {a["id"]: a["url"] for a in ACC}


def next_weekday(s):
    d = dt.date.fromisoformat(s) + dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d.isoformat()


EX = [  # SOURCE_PACKET 발췌 일정(정정 뒤 기준)
    {"id": "S1", "kind": "split", "effective": "2026-08-13", "halt": ["2026-08-11", "2026-08-25"], "listing": "2026-08-26", "correction": "상장일정 확정"},
    {"id": "S1b", "kind": "split", "effective": "2025-01-08", "halt": ["2025-01-06", "2025-01-23"], "listing": "2025-01-24", "correction": "발행주식총수 정정 포함"},
    {"id": "S2", "kind": "reverse_split", "effective": "2026-08-25", "halt": ["2026-08-21", "2026-09-11"], "listing": "2026-09-14", "correction": "주식병합 일정 변경"}]
for e in EX:
    e["halt_end_next_weekday"] = next_weekday(e["halt"][1])
    e["listing_equals_next_weekday"] = e["listing"] == e["halt_end_next_weekday"]
    e["effective_inside_halt"] = e["halt"][0] <= e["effective"] <= e["halt"][1]
    e["source_url"] = U[e["id"]]
    e["evidence_tier"] = TIER
    e["holiday_note"] = "요일로만 셈 · KRX 휴장일 달력 원문 미확인"

def item(value, field, urls, tier, verdict, why, inference=None):
    return {"value": value, "source_field": field, "source_url": urls, "evidence_tier": tier, "verdict": verdict, "why": why, "inference": inference}

events = {}
for kind, code, name, urls in (("split", "70128", "주식분할 결정", [U["S1"], U["S1b"]]), ("reverse_split", "70129", "주식병합 결정", [U["S2"]])):
    exs = [e for e in EX if e["kind"] == kind]
    events[kind] = {
        "report_form_code": item(code, "KIND 공시서식 파일명 · 서식 제목", urls, TIER, "ACCEPT",
                                 f"패킷이 공식 KIND URL과 서식 제목 '{code}_{name}'을 함께 적음 · 파일명 {code}.htm" + (" · 서로 다른 공시 2건에서 같은 코드" if kind == "split" else " · 예시 1건")),
        "report_name": item(name, "KIND 서식 제목", urls, TIER, "ACCEPT", "서식 제목 그대로(KIND 기준)"),
        "dart_report_nm": item(None, "OpenDART list.report_nm", [], "NONE", "BLOCKED_NO_OFFICIAL_EVIDENCE",
                               "KIND 서식 코드가 DART 공시목록 report_nm 문자열 · pblntf_detail_ty와 같다는 공식 근거가 패킷에 없음 → DART 1단계 탐지에는 아직 못 씀"),
        "legal_effective_date": item("필드 '신주의 효력발생일' 값", "신주의 효력발생일", urls, TIER, "ACCEPT",
                                     "필드 이름이 법적 효력발생일을 직접 가리킴 · 가격 기준일 · 매도 가능일로 대체 금지",
                                     inference="예시 모두 효력일이 매매거래정지 기간 안" if all(e["effective_inside_halt"] for e in exs) else None),
        "halt_period": item("필드 '매매거래정지예정기간' 시작/종료", "매매거래정지예정기간(시작일) · (종료일)", urls, TIER, "ACCEPT", "필드 존재(예정 일정 · 실제는 정정 · 시장 조치로 바뀔 수 있음)"),
        "listing_date": item("필드 '신주권상장예정일'", "신주권상장예정일", urls, TIER, "ACCEPT", "필드 존재(예정일)"),
        "price_basis_date": item(None, "KRX 시행세칙 기준가격 조항(S3) · 인용조문(S4)", [U["S3"], U["S4"]], TIER, "BLOCKED_NO_OFFICIAL_EVIDENCE",
                                 "S3는 산식(직전 매매거래일 종가에 분할/병합 비율 반영)만 정함 · 첫 적용 달력일을 직접 정하지 않음. S4 '호가하는 날 분할/병합되는 종목'이 거래 재개일인지 문구 없음. 원문 대조 실패 · 시장 범위(코스닥) · 현행 조문 여부 미확인",
                                 inference="정지 기간에는 매매가 없으므로 '직전 매매거래일'은 정지 전 마지막 거래일이고, 산식이 쓰이는 첫날은 정지 뒤 첫 거래일로 보임(추론 · 공식 문구 아님)"),
        "first_sellable_date": item(None, "매매거래정지예정기간(종료일) · 신주권상장예정일", urls, TIER, "REVISE",
                                    f"예시 {sum(e['listing_equals_next_weekday'] for e in exs)}/{len(exs)}건에서 '정지 종료 다음 평일 = 신주권상장예정일'. 일반 규칙의 공식 문구 없음 → 사건마다 두 값이 같을 때만 후보로 쓰고, 다르거나 하나라도 없으면 UNKNOWN",
                                    inference="두 값이 같으면 그날을 첫 매도 가능일 후보로(실제 날짜는 정정 · 시세 자료로 확인 필요)"),
        "examples": exs}

contract = {"task_id": "REPLAY-OFFICIAL-DATE-EVIDENCE-RECOVERY-0001", "scope": ["split", "reverse_split"],
            "direct_access": {"attempts": len(ACC), "succeeded": 0, "per_url_max": 1, "retries": 0},
            "events": events,
            "correction_rule": {"rule": "정정본은 공개(가용) 시각이 판단 cutoff 이전인 최신 버전만 사용 · 일정은 정정마다 다시 읽음 · 예시처럼 정정으로 일정이 바뀔 수 있음",
                                "keep_pr90": {"UNKNOWN_CA_VERSION_PIT": "유지(원 접수 연결 공식 칸 없음 · KIND 원문 대조 실패)", "same_day_ban": "유지(접수 시각 근거 없음)", "fail_closed": "유지"},
                                "examples": [{"id": e["id"], "correction_reason": e["correction"]} for e in EX]},
            "pr88_narrow_revision": {
                "fill_now": ["kind(split · reverse_split) ← KIND 서식 70128 · 70129", "legal_effective_date ← '신주의 효력발생일'(회계 수량 전환일로 쓰지 않음)",
                             "halt_start · halt_end ← '매매거래정지예정기간'(새 칸)", "listing_date ← '신주권상장예정일'",
                             "ratio 후보 ← 분할/병합 전후 1주당 가액 · 발행주식총수 두 경로가 같을 때만(다르면 UNKNOWN)",
                             "각 날짜 칸에 source_field · evidence_tier 기록(새 칸)"],
                "still_unknown": ["price_basis_date(첫 적용일 일반 규칙)", "first_sellable_date 일반 규칙(사건별 '정지 종료 다음 거래일 = 상장예정일'일 때만 후보)",
                                  "DART report_nm ↔ 70128/70129 대응", "KIND 공시의 가용 시각 정밀도", "정정 사슬 원 접수 연결", "코스닥 시장 규정 적용", "KRX 휴장일 반영"],
                "accounting_rule_until_resolved": "분할/병합 종목은 정지 시작일부터 NAV 무효(PR #88 게이트 그대로). 정지 기간을 '공식 정지라 유효'로 보는 HALT_CARRY는 price_basis_date가 ACCEPT된 뒤에만 제안",
                "practical_blocker": "kind.krx.co.kr가 이 환경에서 서버 403이라, 실제 수집 TASK에서도 70128/70129 원문을 KIND에서 받을 수 없음 → OpenDART document.xml에 같은 거래소공시 본문이 있는지(NEEDS_DATA)가 다음 확인 대상"},
            "status": "BLOCKED", "status_why": "price_basis_date 일반 규칙과 first_sellable_date 일반 규칙이 공식 문구로 직접 증명되지 않음(원문 대조 5/5 실패 · 색인 발췌뿐)"}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "split-reverse-split-date-contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=1))
(OUT / "source-access-log.json").write_text(json.dumps({"attempts": ACC, "rule": "URL마다 1회 · 재시도 없음 · 새 네트워크 허용 요청 없음 · 원문 본문은 403 안내문뿐이라 근거로 안 씀"}, ensure_ascii=False, indent=1))
print(json.dumps({k: {f: v[f]["verdict"] for f in ("report_form_code", "report_name", "dart_report_nm", "legal_effective_date", "price_basis_date", "first_sellable_date")} for k, v in events.items()}, ensure_ascii=False))
print(json.dumps([{x: e[x] for x in ("id", "halt_end_next_weekday", "listing", "listing_equals_next_weekday", "effective_inside_halt")} for e in EX], ensure_ascii=False))
