"""REPLAY-KOSPI-INTEGRATED-SNAPSHOT-LOCK-0001 · 오프라인 판정(네트워크 · 데이터 0).
python3 -I snapshot_check.py <PR97 SOURCE_PACKET.md> <PR96 article-30-1-6-timeline.json> <출력 폴더>
사전등록 규칙 그대로. 인용은 패킷에 글자 그대로 있어야 함."""
import datetime as dt
import hashlib
import json
import re
import socket
import sys
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
PKT, T96, OUT = Path(sys.argv[1]), json.load(open(sys.argv[2])), Path(sys.argv[3])
pkt = PKT.read_text(encoding="utf-8")
TIER = "GPT_CAPTURED_OFFICIAL_INDEX"


def q(s):
    assert s in pkt, s
    return s


def block(tag):
    i = pkt.index(f"## {tag} ")
    j = pkt.find("\n## ", i + 3)
    return pkt[i:j if j > 0 else len(pkt)]


S1, S2, S3 = block("S1"), block("S2"), block("S3")
URL = "https://law.krx.co.kr/las/LawBon.jsp?lawid=000111"
header = q("유가증권시장 업무규정 시행세칙 [일부개정 2024.10.29 규정 제2256호 <시행일:2024.11.4>]")
art1 = q("제1조(목적) 이 세칙은 「유가증권시장 업무규정」(이하 “규정”이라 한다)의 시행에 관하여 필요한 사항을 규정함을 목적으로 한다.")
m = re.search(r"\[일부개정 (\d{4})\.(\d{1,2})\.(\d{1,2}) 규정 제(\d+)호 <시행일:(\d{4})\.(\d{1,2})\.(\d{1,2})>\]", header)
amend = dt.date(int(m[1]), int(m[2]), int(m[3]))
effective = dt.date(int(m[5]), int(m[6]), int(m[7]))
reg_no = m[4]
TRAIN = (dt.date(2025, 9, 18), dt.date(2026, 3, 31))
SEARCH = dt.date(2026, 10, 9)
crawl_mid = SEARCH - dt.timedelta(days=61)                 # '약 2개월 전'
crawl_band = (crawl_mid - dt.timedelta(days=31), crawl_mid + dt.timedelta(days=31))
pub_mid = SEARCH - dt.timedelta(days=round(1.9 * 365.25))  # '약 1.9년 전' — 시행일 아님 · 교차 확인용

# 제6호 문구 비교(완전일치)
ex_S2 = re.search(r"정확 발췌:\n\s+- `([^`]+)`", S2).group(1)
ex_S3 = re.search(r"정확 발췌:\n\s+- `([^`]+)`", S3).group(1)
ex_96 = {r["source"]: r["exact_excerpt"] for r in T96["rows"] if r["exact_excerpt"]}
strip_q = lambda s: s.strip("“”\"")
cmp = {"S2==S3": ex_S2 == ex_S3,
       **{f"S2==PR96.{k}": ex_S2 == v for k, v in ex_96.items()},
       **{f"S2==PR96.{k}(따옴표 제거)": ex_S2 == strip_q(v) for k, v in ex_96.items()}}
quote_only_diff = [k for k, v in ex_96.items() if ex_S2 != v and ex_S2 == strip_q(v)]

# A
same_result = ("lawid=000111" in S1) and (header in S1)
A = {"claim": "lawid 000111의 정식 규정명 = 유가증권시장 업무규정 시행세칙", "evidence_tier": TIER, "url": URL,
     "official_index_text": [header, art1], "url_has_lawid": "lawid=000111" in S1, "name_in_same_result": same_result,
     "packet_note": q("머리글은 같은 URL의 색인 결과에 직접 표시되었다."),
     "inference": "제1조가 「유가증권시장 업무규정」의 시행 세칙임을 밝혀 정식명과도 일관",
     "verdict": "ACCEPT" if same_result else "REVISE"}
# B — 네 조건
c1 = effective < TRAIN[0] and amend < TRAIN[0]
c2 = crawl_band[0] > TRAIN[1]                               # 근사 폭 아래끝도 Train 끝 뒤
c3_exact = bool(ex_S2) and "제30조(기준가격) 제1항 제6호" in S2
same_block_stated = not ("동시에 노출된 것은 아니지만" in S2)
same_crawl_stated = bool(re.search(r"같은 크롤|동일 크롤|same crawl", S2))
c3_same_snapshot = same_block_stated or same_crawl_stated
c4 = "더 늦은" not in S1 and header.count("일부개정") == 1     # 머리글은 최종 개정 하나만 표시
B_conds = {"①_amend_and_effective_before_train": {"ok": c1, "amend": amend.isoformat(), "effective": effective.isoformat(), "reg_no": reg_no, "train_start": TRAIN[0].isoformat()},
           "②_crawl_after_train": {"ok": c2, "crawl_approx": crawl_mid.isoformat(), "band": [d.isoformat() for d in crawl_band], "train_end": TRAIN[1].isoformat(),
                                    "note": "크롤은 시행 근거가 아니라 그 시점 머리글의 관찰 시점"},
           "③_exact_text_6ho": {"ok": c3_exact, "text": ex_S2, "location": "제30조(기준가격) 제1항 제6호"},
           "③b_same_snapshot_as_header": {"ok": c3_same_snapshot, "packet_says": q("이번 검색 응답 한 블록에 머리글과 제30조 문장이 동시에 노출된 것은 아니지만 URL은 동일하다."),
                                          "why": "같은 URL이지만 다른 응답 블록 · 같은 크롤본이라는 명시 없음 → 사전등록 정의상 연결에 추론 필요"},
           "④_no_later_amendment_in_header": {"ok": c4, "note": "통합본 머리글은 최종 일부개정 하나(2024.10.29)만 표시 → 관찰 시점(약 2026-08)까지 더 늦은 개정 없음"}}
all_direct = c1 and c2 and c3_exact and c3_same_snapshot and c4
B = {"claim": "Train 기간 시행본에 제30조 제1항 제6호 산식이 있었다", "evidence_tier": TIER, "conditions": B_conds,
     "string_compare": cmp, "quote_only_difference": quote_only_diff,
     "published_crosscheck": {"published_approx": pub_mid.isoformat(), "note": "Published 약 1.9년 전 ≈ 2024-11 — 일부개정 2024-10-29와 어긋나지 않음(시행일 근거로 쓰지 않음)"},
     "robustness": ("두 발췌가 다른 크롤본이라도, 제6호 발췌의 크롤(약 2026-08, PR #95 패킷)이 [2024-11-04, 머리글 크롤] 안이면 결론은 같음. "
                    "어긋나는 경우는 머리글 크롤 뒤 제6호가 바뀌었다가 2022 문구로 되돌아간 경우뿐 — 가능성은 낮지만 공식 근거로 배제되지는 않음"),
     "verdict": "ACCEPT" if all_direct else ("REVISE" if (c1 and c2 and c3_exact and c4) else "BLOCKED_NO_OFFICIAL_EVIDENCE")}
status = "READY" if A["verdict"] == "ACCEPT" and B["verdict"] == "ACCEPT" else "BLOCKED"
out = {"A": A, "B": B, "status": status, "excluded": ["KOSDAQ", "비율 방향", "가격 기준일", "거래재개일", "최초 매도가능일", "NAV", "성과"],
       "packet_sha256": hashlib.sha256(PKT.read_bytes()).hexdigest(), "network_calls": 0}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "snapshot-identity-and-train.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({"A": A["verdict"], "B": B["verdict"], "status": status, "conds": {k: v["ok"] for k, v in B_conds.items()},
                  "string_compare": cmp, "quote_only_diff": quote_only_diff}, ensure_ascii=False))
