"""REPLAY-KOSPI-RULE-TEMPORAL-LOCK-0001 · 오프라인 비교 · 판정(네트워크 · 데이터 0).
python3 -I compare.py <PR95 SOURCE_PACKET.md> <출력 폴더>
- 패킷 블록(P1~P5)을 나눠, 따옴표 정확 발췌만 글자 단위 비교. GPT 요약 사실은 단서로만.
- 사전등록 규칙 그대로."""
import hashlib
import json
import re
import socket
import sys
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
PKT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
pkt = PKT.read_text(encoding="utf-8")
TIER = "GPT_CAPTURED_OFFICIAL_INDEX"
blk = {}
for m in re.finditer(r"^## (P\d) — (.+?)$", pkt, re.M):
    start = m.end()
    nxt = re.search(r"^## ", pkt[start:], re.M)
    blk[m.group(1)] = {"title": m.group(2).strip(), "body": pkt[start:start + (nxt.start() if nxt else len(pkt) - start)]}
assert set(blk) == {"P1", "P2", "P3", "P4", "P5"}, blk.keys()


def has(p, s):
    return s in blk[p]["body"]


def url(p):
    return re.search(r"URL: (\S+)", blk[p]["body"]).group(1)


def exact(p):
    return re.findall(r"“([^”]+)”", blk[p]["body"])


PUB = {"P4": "2018-12-28", "P3": "2020-05-07", "P2": "2022-08-26", "P1": "통합 화면(색인 크롤 약 2026-08 · 공개일 표시 없음)"}
ORDER = ["P4", "P3", "P2", "P1"]
rows = []
for p in ORDER:
    ex = [e for e in exact(p) if "분할" in e]
    rows.append({"source": p, "url": url(p), "pub_date": PUB[p], "evidence_tier": TIER,
                 "article": "제30조 제1항 제6호" if (has(p, "제1항 제6호") or has(p, "제30조 제1항 제6호")) else None,
                 "article_title_shown": has(p, "제30조(기준가격)"),
                 "exact_excerpt": ex[0] if ex else None,
                 "claimed_same_as": (re.search(r"제1항 제6호는 (P[\d·P]+)[^\n]*같은 산식 문구", blk[p]["body"]).group(1) if re.search(r"같은 산식 문구", blk[p]["body"]) else None),
                 "pub_is_not_effective": has(p, "공개일") and ("시행일" in blk[p]["body"])})
# 글자 단위 비교(정확 발췌가 있는 것끼리만)
ex_rows = [r for r in rows if r["exact_excerpt"]]
base = ex_rows[0]["exact_excerpt"] if ex_rows else None
first_diff = []
prev = None
for r in rows:
    if r["exact_excerpt"] is None:
        r["text_compare"] = "비교 불가 · 정확 발췌 없음(패킷은 '같은 산식 문구'라고만 적음 = GPT 주장)"
        continue
    if prev is None:
        r["text_compare"] = "비교 기준(가장 이른 정확 발췌)"
    else:
        same = r["exact_excerpt"] == prev["exact_excerpt"]
        r["text_compare"] = f"{prev['source']}와 글자 단위 {'같음' if same else '다름'}"
        if not same:
            first_diff.append({"from": prev["source"], "to": r["source"]})
    prev = r
comparable = [r["source"] for r in ex_rows]

# A. 시장 식별 단서
clues = {
    "kosdaq_transfer_listing_in_art30(P1)": has("P1", "코스닥시장에서 이전상장하는 종목을 별도로 다룬다"),
    "kospi_listing_rule_ref(P1)": has("P1", "유가증권시장 상장규정을 직접 참조"),
    "kospi_listing_rule_ref(P3)": has("P3", "유가증권시장 상장규정을 참조"),
    "kospi_listing_rule_ref(P4)": has("P4", "유가증권시장 상장규정을 참조"),
    "etn_6_2(P2)": has("P2", "상장지수증권"),
    "separate_rules_listed(P5)": has("P5", "`유가증권시장 업무규정 시행세칙`과 `코스닥시장 업무규정 시행세칙`이 별도 규정"),
}
direct_binding = {"P1_title_binding": not has("P1", "정식 규정명과 lawid의 직접 결합 문구는 색인에 없다"),
                  "P5_lawid_binding": not has("P5", "목록이 각 정식명과 lawid `000111`을 직접 연결하지 않는다")}
contradiction = has("P1", "코스닥시장 상장규정을 직접 참조") or any(has(p, "코스닥시장 업무규정") and p != "P5" for p in blk)
A = {"claim": "lawid 000111 = 유가증권시장 업무규정 시행세칙", "evidence_tier": TIER,
     "official_index_text": [x for x in exact("P1")],
     "clues_gpt_summarized": clues, "direct_binding": direct_binding, "contradiction_found": contradiction,
     "inference": ("제30조 안에서 '코스닥시장에서 이전상장하는 종목'을 별도로 다루고(다른 시장에서 '들어오는' 종목 처리), 재상장 · 변경상장 정의가 유가증권시장 상장규정을 참조 → "
                   "유가증권시장 쪽 규정이라는 일관된 단서. 상장지수증권(6호의2)도 같은 방향의 약한 단서. 모두 GPT 요약 사실이며 정확 발췌 아님"),
     "verdict": "ACCEPT" if any(direct_binding.values()) else ("BLOCKED_NO_OFFICIAL_EVIDENCE" if contradiction else "REVISE"),
     "why": "정식명 ↔ lawid 직접 결합 없음(P1 · P5 한계에 명시) · 내부 참조는 모순 없이 일관"}
# B. 존속성
pre = [r for r in rows if r["source"] in ("P4", "P3", "P2")]
post = [r for r in rows if r["source"] == "P1"]
gap_note = {"adjacent_amend_2023_04_12": has("P1", "2023-04-12 개정·삭제 표시"),
            "no_change_mark_for_6ho_seen": has("P1", "제1항 제6호 자체의 2023-04-12 이후 변경 표시는 확인되지 않았다"),
            "absence_is_not_evidence": True,
            "uncovered": "P2(2022-08-26 공개) ~ P1(약 2026-08 크롤) 사이 공개본 · 개정 이력 전체 목록이 패킷에 없음 → Train 중 그 호가 바뀌었다가 되돌아왔을 가능성을 공식 근거로 배제 못 함"}
same_pre_post = bool(pre and post and pre[-1]["exact_excerpt"] and post[0]["exact_excerpt"] and pre[-1]["exact_excerpt"] == post[0]["exact_excerpt"])
B = {"claim": "제30조 제1항 제6호 산식이 Train(2025-09-18~2026-03-31)에 존속", "evidence_tier": TIER,
     "last_exact_before_train": pre[-1]["source"] if pre else None, "first_exact_after_train": post[0]["source"] if post else None,
     "same_text_before_after": same_pre_post, "article_same": all(r["article"] == "제30조 제1항 제6호" for r in rows),
     "gap": gap_note,
     "verdict": "BLOCKED_NO_OFFICIAL_EVIDENCE" if not same_pre_post else ("ACCEPT" if False else "REVISE"),
     "why": "전(P2 2022-08-26)과 후(P1 통합 화면) 정확 발췌가 글자 단위 같고 조 · 항 · 호도 같음. 그러나 중간 개정표시 전체가 없고 '변경 표시 미확인'은 부재 관찰일 뿐 → 중간 공백 직접 배제 불가"}
timeline = {"rows": rows, "comparable_exact_sources": comparable, "first_text_difference": first_diff or f"비교 가능한 범위({' · '.join(comparable)})에서 없음",
            "not_comparable": [r["source"] for r in rows if r["exact_excerpt"] is None], "B": B,
            "packet_sha256": hashlib.sha256(PKT.read_bytes()).hexdigest()}
identity = {"A": A, "P5": {"url": url("P5"), "note": "현재 목록에서 두 시행세칙이 별도 규정임만 확인 · lawid 연결 없음"},
            "packet_sha256": timeline["packet_sha256"]}
status = "READY" if A["verdict"] == "ACCEPT" and B["verdict"] == "ACCEPT" else "BLOCKED"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "lawid-000111-identity.json").write_text(json.dumps(identity, ensure_ascii=False, indent=1))
(OUT / "article-30-1-6-timeline.json").write_text(json.dumps({**timeline, "status": status, "excluded": ["KOSDAQ", "비율 방향", "가격 기준일", "거래재개일", "최초 매도가능일"], "network_calls": 0}, ensure_ascii=False, indent=1))
print(json.dumps({"A": A["verdict"], "B": B["verdict"], "status": status, "comparable": comparable, "first_diff": timeline["first_text_difference"],
                  "not_comparable": timeline["not_comparable"], "clues": clues, "contradiction": contradiction}, ensure_ascii=False))
