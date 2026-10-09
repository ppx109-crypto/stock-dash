"""REPLAY-CONTRACT-HARDENING-0001 · 단계형 호출 예산(산술만 · 네트워크 안 씀).
python3 -E -P call_budget.py <PR86 target-coverage.json> <출력.json>

PR #86 collector_interface.py 27줄 결함: 주석에 상세 endpoint 7개를 적고 계산은 `1 + 종목 × (1 + 6)` → 33종목 232.
선언 7개 전수는 1 + 33 × (1 + 7) = 265 > 상한 250. 여기서는 목록을 단일 상수로 두고 길이를 코드가 직접 셉니다.

예산 규칙(fail-closed)
- 상한에는 인증 · 코드표(DART corpCode.xml 1회 · KIS tokenP 1회)와 재시도를 모두 넣습니다.
- 각 단계를 시작하기 전에 worst-case(= 기본 성공 호출 × (1 + 재시도))가 남은 상한 안인지 봅니다. 넘으면 호출 전에 BLOCKED_CALL_BUDGET.
- DART 2단계(상세) 호출 수는 1단계(list.json) 결과로만 셉니다. 1단계 결과 없이 숫자를 가정하지 않습니다(STAGE2_PENDING_LIST).
- 1단계 목록 쪽수(page)는 첫 쪽 응답의 total_page로만 알 수 있으므로, 쪽마다 같은 검사를 다시 합니다."""
import json
import math
import socket
import sys
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))

DART_DETAIL = ("piicDecsn", "fricDecsn", "pifricDecsn", "crDecsn", "cmpMgDecsn", "cmpDvDecsn", "cmpDvmgDecsn")
KIND_TO_ENDPOINT = {"rights_issue": "piicDecsn", "bonus_issue": "fricDecsn", "rights_bonus_issue": "pifricDecsn",
                    "capital_reduction": "crDecsn", "merger": "cmpMgDecsn", "spinoff": "cmpDvDecsn", "spinoff_merger": "cmpDvmgDecsn"}
# 저장소 collect_dart_extra.py 33~41줄의 주요사항 endpoint 23개에도 주식분할 · 병합 전용 API가 없음.
# → 분할 · 병합은 위 7개로 잡히지 않을 수 있어 사건마다 공시 원문(document) 1회로 셈하고, 경로는 실제 실행 TASK에서 공식 문서로 확인.
NO_STRUCTURED = ("split", "reverse_split")
DART_CAP, KIS_CAP, RETRY = 250, 500, 2
assert len(DART_DETAIL) == 7 and set(KIND_TO_ENDPOINT.values()) == set(DART_DETAIL)


def worst(base, retry=RETRY):
    return base * (1 + retry)


def dart_exhaustive(codes, list_per_code=1, n_ep=None):
    """선언한 상세 endpoint 전부를 종목마다 부르는 전수 상한."""
    n_ep = len(DART_DETAIL) if n_ep is None else n_ep
    return 1 + codes * (list_per_code + n_ep)


class Budget:
    """단계마다 worst-case를 남은 상한과 비교. 넘으면 그 단계 호출 0으로 멈춤."""

    def __init__(self, cap, retry=RETRY):
        self.cap, self.retry, self.used, self.log = cap, retry, 0, []

    def reserve(self, stage, base):
        need = worst(base, self.retry)
        ok = self.used + need <= self.cap
        self.log.append({"stage": stage, "base": base, "worst": need, "used_before": self.used, "cap": self.cap,
                         "decision": "ALLOW" if ok else "BLOCKED_CALL_BUDGET"})
        return ok

    def spend(self, actual):
        self.used += actual


def dart_stage2(events):
    """events: 1단계 list.json 결과 [(code, kind)] (로컬). 상세 호출 = 고유 (종목, endpoint) + 구조화 API 없는 사건마다 원문 1."""
    pairs, docs, unknown = set(), 0, 0
    for c, k in events:
        if k in KIND_TO_ENDPOINT:
            pairs.add((c, KIND_TO_ENDPOINT[k]))
        elif k in NO_STRUCTURED:
            docs += 1
        else:
            unknown += 1
    return {"detail_calls": len(pairs), "document_calls": docs, "unmapped_kinds": unknown, "base": len(pairs) + docs}


def dart_plan(codes, stage1_pages=None, events=None, stage1_actual=None, cap=DART_CAP, retry=RETRY):
    """stage1_pages: {code: total_page}(없으면 종목마다 1쪽으로 예약하고 첫 쪽 뒤 다시 검사).
    events: 1단계 결과 사건 [(code, kind)] — None이면 2단계는 STAGE2_PENDING_LIST."""
    b = Budget(cap, retry)
    if not b.reserve("corpCode.xml", 1):
        return {"status": "BLOCKED_CALL_BUDGET", "log": b.log}
    b.spend(1)
    s1 = codes if stage1_pages is None else sum(stage1_pages.values())
    if not b.reserve("list.json", s1):
        return {"status": "BLOCKED_CALL_BUDGET", "log": b.log}
    b.spend(s1 if stage1_actual is None else stage1_actual)
    if events is None:
        return {"status": "STAGE2_PENDING_LIST", "log": b.log, "stage2_max_base_after_stage1": (cap - b.used) // (1 + retry)}
    s2 = dart_stage2(events)
    if s2["unmapped_kinds"]:
        return {"status": "BLOCKED_UNMAPPED_KIND", "log": b.log, "stage2": s2}
    if not b.reserve("detail+document", s2["base"]):
        return {"status": "BLOCKED_CALL_BUDGET", "log": b.log, "stage2": s2}
    return {"status": "ALLOW", "log": b.log, "stage2": s2, "base_total": 1 + s1 + s2["base"], "worst_total": worst(1 + s1 + s2["base"], retry)}


def kis_plan(codes, n_days=127, warm=5, per_call=100, cap=KIS_CAP, retry=RETRY):
    per_code = math.ceil((n_days + warm) / per_call) * 2           # 원 · 수정 쌍
    base = 1 + codes * per_code                                     # tokenP 1 포함
    return {"auth_calls": 1, "per_code": per_code, "base": base, "worst": worst(base, retry), "cap": cap,
            "decision": "ALLOW" if worst(base, retry) <= cap else "BLOCKED_CALL_BUDGET"}


if __name__ == "__main__":
    TC, OUT = sys.argv[1:3]
    codes = json.load(open(TC))["unique_codes"]
    ex7, ex6 = dart_exhaustive(codes), dart_exhaustive(codes, n_ep=6)
    plan = {"codes": codes, "retry_per_request": RETRY, "cap_includes": ["인증 · 코드표 호출(KIS tokenP 1 · DART corpCode 1)", "재시도 전부"],
            "dart_detail_endpoints": list(DART_DETAIL), "dart_detail_endpoint_count": len(DART_DETAIL),
            "dart_no_structured_kinds": list(NO_STRUCTURED),
            "dart_exhaustive": {"pr86_reported(6개로 셈)": ex6, "declared_7": ex7, "cap": DART_CAP,
                                "base_within_cap": ex7 <= DART_CAP, "worst": worst(ex7), "worst_within_cap": worst(ex7) <= DART_CAP},
            "dart_staged_before_stage1": dart_plan(codes),
            "kis": kis_plan(codes),
            "network_calls_this_task": 0}
    Path(OUT).write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(json.dumps({"declared_7": ex7, "pr86_6": ex6, "cap": DART_CAP, "staged": plan["dart_staged_before_stage1"]["status"],
                      "stage2_max_base": plan["dart_staged_before_stage1"].get("stage2_max_base_after_stage1"),
                      "kis": plan["kis"]}, ensure_ascii=False))
