"""REPLAY-KRX-PRICE-BASIS-RULE-LOCK-0001 · 오프라인 판정(네트워크 · 데이터 0).
python3 -I decide.py <PR93 SOURCE_PACKET.md> <PR92 split-reverse-split-date-contract.json> <출력 폴더>
- 아래 사실표의 인용은 SOURCE_PACKET에 글자 그대로 있어야 함(없으면 멈춤).
- 사전등록 §2 규칙을 그대로 적용."""
import hashlib
import json
import socket
import sys
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
PKT, PR92, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
pkt = PKT.read_text(encoding="utf-8")
c92 = json.load(open(PR92))
TIER = "GPT_CAPTURED_OFFICIAL_INDEX"


def q(s):
    assert s in pkt, s
    return s


SRC = {
    "S1": {"lawid": "000111", "pub": "2024-05-23", "kind": "인용조문(RefBon)", "title": q("`종목별 매매거래정지후 매매거래 재개등`"),
           "facts": [q("검색 색인은 일부 정지사유의 재개일을 다음 매매거래일 또는 거래소가 정하는 날로 표시한다.")],
           "currentness": q("2024-05-23 공개본이라는 것만 캡처됨. 현재 통합본·시행일·규정 정식명은 이 패킷만으로 미확정."), "exact_excerpt": False},
    "S2": {"lawid": "000111", "pub": None, "kind": "통합 화면(LawBon)",
           "facts": [q("“주식분할 또는 주식병합된 종목은 전일종가에 분할 또는 병합의 비율을 곱한 가격으로 한다.”"),
                     q("분할·병합되는 날에는 `당일의 기준가격`을 사용한다는 문구가 표시됨.")],
           "currentness": q("검색 색인 수집 시점은 약 2026년 8월로 표시되었으나, 현행 시행일·정식 규정명은 직접 원문에서 확인하지 못함."), "exact_excerpt": True},
    "S3": {"lawid": "000111", "pub": "2022-08-26", "kind": "인용조문(RefBon)",
           "facts": [q("장기간 거래정지 뒤 최초 호가일에 분할·병합되는 종목은 `당일의 기준가격`을 사용하는 유형으로 열거됨.")],
           "currentness": q("2022-08-26 공개본. 이후 개정·현행 적용 여부 미확정."), "exact_excerpt": False},
    "S4": {"lawid": "000212", "pub": "2019-04-17", "kind": "인용조문(RefBon)",
           "facts": [q("“직전 매매거래일 종가에 분할 또는 병합비율을 곱한 가격”"), q("분할·병합되는 종목의 기준가격 산식으로 표시됨.")],
           "currentness": q("2019-04-17 공개본. 시장·정식 규정명·현행성은 이 패킷만으로 미확정."), "exact_excerpt": True},
    "S5": {"lawid": "000210/000212", "pub": "2013-09-11/2013-09-13", "kind": "비교 화면(PrtLawThree)",
           "facts": [q("분할·병합되는 날에 `당일의 기준가격`을 사용한다."), q("기준가격은 직전 매매거래일 종가와 분할·병합 비율로 계산한다.")],
           "currentness": q("2013 공개본. 시장·정식 규정명·현행성은 직접 원문에서 확인하지 못함."), "exact_excerpt": False},
    "S6": {"lawid": "000210", "pub": "2013-09-11", "kind": "단일 조문 화면(LawThreeJoIfr)",
           "facts": [q("S5의 기준가격 산식·당일 관계를 단일 조문 화면에서도 검색 색인이 표시함.")],
           "currentness": q("2013 공개본. 현행성 미확정."), "exact_excerpt": False},
}
MARKET_CLAIM = q("S1~S3이 유가증권시장, S4~S6이 코스닥시장이라는 대응은 이번 과제에서 검증할 주장이지 전제가 아니다.")
# 패킷 안에 lawid와 시장을 잇는 문구가 있는지(규칙 2) — '유가증권'·'코스닥' 낱말이 lawid 행과 같은 S 블록에 있는지 기계로 확인
blocks = {s: pkt.split(f"## {s} ")[1].split("\n## ")[0] for s in SRC}
market_text_in_block = {s: any(w in b.split("currentness")[0] for w in ("유가증권시장", "코스닥시장")) for s, b in blocks.items()}
assert not any(market_text_in_block.values()), market_text_in_block      # 블록 본문에 시장 문구 없음
FORM_DIFF = {"S2(000111)": "전일종가 × 분할 또는 병합의 비율", "S4(000212)": "직전 매매거래일 종가 × 분할 또는 병합비율"}

AXES = ("rule_name_and_market", "lawid_and_article", "version_or_effective_date", "formula", "same_day_equals_resumption", "consistent_with_pr92")


def cell(market, kind):
    lawids = ["000111"] if market == "KOSPI" else ["000212", "000210"]
    src = [s for s, v in SRC.items() if any(l in v["lawid"] for l in lawids)]
    ax = {
        "rule_name_and_market": {"status": "증거 없음", "why": "패킷 블록 어디에도 lawid ↔ 시장 문구 없음 · 정식 규정명 미확정(S1 · S2 · S4 · S5 currentness)", "claimed_by_packet": MARKET_CLAIM},
        "lawid_and_article": {"status": "부분", "why": f"lawid {'/'.join(lawids)}는 URL 사실 · 조문 번호 · 별표 위치는 패킷에 없음(S1은 조문 표제만)"},
        "version_or_effective_date": {"status": "증거 없음", "why": "공개일만 있고 시행일 · 현행 여부 없음. Train(2025-09-18~2026-03-31)에 시행 중이던 버전 확인 불가",
                                      "pubs": {s: SRC[s]["pub"] for s in src}},
        "formula": {"status": "색인 문구 있음(REVISE 상한)",
                    "text": [f for s in src for f in SRC[s]["facts"] if "곱한" in f or "계산" in f],
                    "ratio_direction": "증거 없음 — '분할 비율'이 (뒤 주식 수 ÷ 앞)인지 (앞 액면 ÷ 뒤)인지 문구 없음. PR #92 ratio 후보(주식 수 배율)라면 가격 배수는 그 역수여야 하므로 방향 확정 전 산식 적용 금지"},
        "same_day_equals_resumption": {"status": "증거 없음",
                                       "text": [f for s in src for f in SRC[s]["facts"] if "당일" in f or "재개" in f or "최초 호가일" in f],
                                       "why": "'분할·병합되는 날' · '최초 호가일'이 거래 재개일이라는 문구 없음. S3(최초 호가일)는 가장 가깝지만 000111 · 2022 공개본 · 요약 사실(정확 발췌 아님)"},
        "consistent_with_pr92": {"status": "모순 없음(보조)",
                                 "why": "PR #92 예시 3/3 '정지 종료 다음 평일 = 상장예정일' · 효력일은 정지 중 — 산식이 정지 뒤 첫 거래일에 쓰인다는 추론과 충돌 없음(일반 규칙 아님)"},
    }
    if market == "KOSDAQ":
        ax["same_day_equals_resumption"]["why"] += " · 코스닥 쪽 후보(000212/000210)에는 S3 같은 '최초 호가일' 문구도 없음(2013 · 2019 공개본뿐)"
    all_ok = all(v["status"] in ("ACCEPT",) for v in ax.values())
    return {"market": market, "event": kind, "candidate_sources": src, "evidence_tier": TIER, "axes": ax,
            "rule_identity_verdict": "BLOCKED_NO_OFFICIAL_EVIDENCE",
            "formula_verdict": "REVISE", "formula_note": "색인 정확 발췌(S2 · S4)는 있으나 시장 · 버전 · 비율 방향 미확정 · 직접 원문 아님",
            "price_basis_date": {"value": None, "verdict": "ACCEPT" if all_ok else "BLOCKED_NO_OFFICIAL_EVIDENCE",
                                 "candidates": {"거래 재개일(정지 뒤 첫 거래일)": "INFERENCE(가장 그럴듯함 · 공식 연결 문구 없음)",
                                                "신주권상장예정일": "INFERENCE(사례 3/3에서 재개일과 같음 · 일반 규칙 아님)",
                                                "신주의 효력발생일": "사용 금지(PR #92 반증: 정지 중)"}},
            "needs_data": ["lawid별 정식 규정명과 시장(유가증권시장 업무규정 시행세칙 / 코스닥시장 업무규정 시행세칙 여부)",
                           "기준가격 조항의 조문 번호 · 항 · 호와 Train 기간에 시행 중이던 버전의 시행일",
                           "'분할·병합되는 날'(또는 '최초 호가일')이 매매거래 재개일임을 정하는 조문 직접 문구",
                           "분할 · 병합 비율의 정의(가격에 곱하는 방향)"]}


cells = [cell(m, k) for m in ("KOSPI", "KOSDAQ") for k in ("split", "reverse_split")]
identity = {"sources": {s: {k: v for k, v in d.items()} for s, d in SRC.items()}, "market_claim_in_packet": MARKET_CLAIM,
            "market_text_found_in_blocks": market_text_in_block, "formula_wording_difference": FORM_DIFF,
            "verdict_by_lawid": {"000111": "시장 · 정식명 · 시행일 증거 없음(유가증권 주장 미검증)", "000212": "같음(코스닥 주장 미검증)", "000210": "같음(2013 공개본만)"},
            "packet_sha256": hashlib.sha256(PKT.read_bytes()).hexdigest(), "evidence_tier": TIER}
decision = {"cells": cells, "pr92_cross": {k: {f: c92["events"][k][f]["verdict"] for f in ("legal_effective_date", "price_basis_date", "first_sellable_date")} for k in c92["events"]},
            "keep": ["UNKNOWN_CA_VERSION_PIT", "당일 사용 금지", "분할 · 병합 종목은 정지 시작일부터 NAV 무효", "fail-closed"],
            "status": "READY" if all(c["price_basis_date"]["verdict"] == "ACCEPT" for c in cells) else "BLOCKED",
            "network_calls": 0, "data_calls": 0}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "rule-identity-matrix.json").write_text(json.dumps(identity, ensure_ascii=False, indent=1))
(OUT / "price-basis-date-decision.json").write_text(json.dumps(decision, ensure_ascii=False, indent=1))
print(json.dumps({"cells": [(c["market"], c["event"], c["rule_identity_verdict"], c["formula_verdict"], c["price_basis_date"]["verdict"]) for c in cells],
                  "status": decision["status"], "market_text_found": market_text_in_block}, ensure_ascii=False))
