"""REPLAY-KOSPI-RULE2256-ARTICLE30-LOCK-0001 · 오프라인 결속 판정(네트워크 · 데이터 0).
python3 -I bind_check.py <PR99 SOURCE_PACKET.md> <PR98 snapshot-identity-and-train.json> <출력 폴더>"""
import datetime as dt
import hashlib
import json
import socket
import sys
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
PKT, E98, OUT = Path(sys.argv[1]), json.load(open(sys.argv[2])), Path(sys.argv[3])
pkt = PKT.read_text(encoding="utf-8")
TIER = "GPT_CAPTURED_OFFICIAL_INDEX"


def q(s):
    assert s in pkt, s
    return s


def block(tag):
    i = pkt.index(f"## {tag} ")
    j = pkt.find("\n## ", i + 3)
    return pkt[i:j if j > 0 else len(pkt)]


S1, S2, S3, S4 = (block(t) for t in ("S1", "S2", "S3", "S4"))
TEXT = "주식분할 또는 주식병합된 종목은 전일종가에 분할 또는 병합의 비율을 곱한 가격으로 한다."
version_ids = {
    "S1_header": q("`유가증권시장 업무규정 시행세칙 [일부개정 2024.10.29 규정 제2256호 <시행일:2024.11.4>]`"),
    "S1_buchik": q("`부칙<제2256호, 2024.10.29>`"),
    "S1_buchik_art1": q("`제1조(시행일) 이 세칙은 2024년 11월 4일부터 시행한다.`"),
    "S2_list": q("`유가증권시장 업무규정 시행세칙 [일부개정, 2024.10.29, 제2256호]`"),
    "S3_recent": q("`규정 제2256호 유가증권시장 업무규정 시행세칙 2024.10.29`"),
}
text_in = {s: (TEXT in b) for s, b in (("S1", S1), ("S2", S2), ("S3", S3), ("S4", S4))}
limits = {"S1": q("한계: 이번 고정 응답에서 제30조 제1항 제6호 정확 문장은 머리글과 같은 검색 블록에 노출되지 않았다."),
          "S2": q("한계: 목록 메타이며 제30조 문구 없음."), "S3": q("한계: 개정 목록 메타이며 제30조 문구 없음."),
          "S4": q("핵심 한계: S1의 규정 제2256호 머리글/부칙과 S4가 같은 크롤본 또는 같은 시행본이라는 직접 메타가 아직 없다.")}
# ACCEPT 증거 3종
ev1 = any(TEXT in b and ("2256" in b or "2024.11.4" in b or "2024년 11월 4일" in b) and "같은 검색 블록에 노출되지 않았다" not in b and "직접 메타가 아직 없다" not in b
          for b in (S1, S2, S3))
ev2 = TEXT in S1 and "같은 검색 블록에 노출되지 않았다" not in S1
ev3 = ("같은 크롤" in S4 or "동일 크롤" in S4) and "직접 메타가 아직 없다" not in S4
B_ok = ev1 or ev2 or ev3
eff = dt.date(2024, 11, 4); amend = dt.date(2024, 10, 29); train0 = dt.date(2025, 9, 18)
A_keep = E98["A"]["verdict"]
A_contra = not all(x in pkt for x in ("유가증권시장 업무규정 시행세칙",)) or "코스닥시장 업무규정 시행세칙 [일부개정" in pkt
out = {"A": {"verdict": A_keep if not A_contra else "BLOCKED_NO_OFFICIAL_EVIDENCE", "kept_from_pr98": True, "contradiction_in_pr99_packet": A_contra},
       "B": {"version_identifiers": version_ids, "article_text": TEXT, "article_text_present_in_block": text_in,
             "packet_limits": limits,
             "accept_evidence": {"1_text_inside_2256_version": ev1, "2_header_and_text_same_response": ev2, "3_same_crawl_meta": ev3},
             "date_compare": {"amend": amend.isoformat(), "effective": eff.isoformat(), "train_start": train0.isoformat(), "effective_before_train": eff < train0 and amend < train0},
             "new_vs_pr98": "부칙<제2256호> 제1조(시행일 2024-11-04)가 머리글 밖에서 직접 확인 · 공식 목록 2곳(S2 · S3)도 제2256호 = 2024.10.29 · 그러나 제6호 문구와의 결속은 그대로 없음",
             "verdict": "ACCEPT" if B_ok else "REVISE", "evidence_tier": TIER},
       "needs_data": "규정 제2256호(시행 2024-11-04) 시행본 또는 그 머리글/부칙과 같은 공식 색인 응답 안에 있는 제30조 제1항 제6호 정확 발췌 1건",
       "excluded": ["KOSDAQ", "비율 방향", "가격 기준일", "거래재개일", "최초 매도가능일", "NAV", "성과"],
       "packet_sha256": hashlib.sha256(PKT.read_bytes()).hexdigest(), "network_calls": 0}
out["status"] = "READY" if out["A"]["verdict"] == "ACCEPT" and out["B"]["verdict"] == "ACCEPT" else "BLOCKED"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "rule2256-article30-binding.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({"A": out["A"]["verdict"], "B": out["B"]["verdict"], "status": out["status"], "accept_evidence": out["B"]["accept_evidence"],
                  "text_in": text_in, "date_ok": out["B"]["date_compare"]["effective_before_train"]}, ensure_ascii=False))
