"""REPLAY-OFFICIAL-SEMANTICS-AUDIT-0001 · 공식 문서 근거표 생성(받은 원문에서 인용을 기계로 뽑음 · 데이터 API 호출 없음).
python3 -I build_evidence.py <받은 원문 폴더> <fetch_log.jsonl> <KIS 공식 저장소 로컬 복제> <출력 폴더>
- 인용은 원문 HTML/코드에서 태그 · 공백만 정리한 그대로입니다. 원문에 없으면 AssertionError로 멈춥니다(추정 금지).
- 원문 파일은 커밋하지 않고 sha256만 남깁니다."""
import hashlib
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAW, LOG, KIS, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
NOW = datetime.now(timezone(timedelta(hours=9))).replace(microsecond=0).isoformat()
FETCH = [json.loads(l) for l in open(LOG) if l.strip()]
BY = {f["name"]: f for f in FETCH if "name" in f}
KIS_COMMIT = subprocess.run(["git", "-C", str(KIS), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def clean(t):
    t = re.sub(r"<br\s*/?>", " / ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def rows(name):
    t = open(RAW / name, encoding="utf-8", errors="replace").read()
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        out.append([clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)])
    return out


def dart_src(name):
    f = BY[name]
    m = re.search(r"apiId=(\d+)", f["url"])
    return {"url": f["url"], "retrieved_at_kst": f["retrieved_at_kst"], "http": f["http"], "sha256": f["sha256"], "tier": "OPENDART_DEV_GUIDE"}


def q_dart(name, must):
    flat = " || ".join(" | ".join(r) for r in rows(name))
    assert must in flat, (name, must)
    i = flat.index(must)
    return flat[i:i + len(must)]


def resp_keys(name):
    """응답 표(첫 칸이 응답키인 표)의 키 목록."""
    t = open(RAW / name, encoding="utf-8", errors="replace").read()
    for tb in re.findall(r"<table[^>]*>(.*?)</table>", t, re.S):
        rs = [[clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)] for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S)]
        if rs and rs[0] and rs[0][0] == "응답키":
            return [(r[0], r[1] if len(r) > 1 else "") for r in rs[1:] if r and r[0]]
    raise AssertionError(name)


def kis_src(rel):
    p = KIS / rel
    return {"url": f"https://github.com/koreainvestment/open-trading-api/blob/{KIS_COMMIT}/{rel}", "repo_commit": KIS_COMMIT,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "retrieved_at_kst": NOW, "http": "git(공개 저장소 읽기)",
            "tier": "KIS_OFFICIAL_SAMPLE(한국투자증권 공식 저장소 · README: 당사 제공 샘플 · 참고용)"}


def q_kis(rel, must):
    t = (KIS / rel).read_text(encoding="utf-8")
    assert must in t, (rel, must)
    return must


# ═════ 1. OpenDART API 전체 목록(6그룹) — 분할 · 병합 구조화 API 없음 증명 ═════
groups = {}
for g, nm in (("DS001", "dart_guide_main"), ("DS002", "dart_guide_DS002"), ("DS003", "dart_guide_DS003"), ("DS004", "dart_guide_DS004"),
              ("DS005", "dart_guide_ds005"), ("DS006", "dart_guide_DS006")):
    groups[g] = [r[1] for r in rows(nm) if len(r) > 2 and r[0].isdigit()]
all_names = [n for v in groups.values() for n in v]
split_like = [n for n in all_names if re.search(r"주식분할|액면분할|주식병합|액면병합|액면교체", n)]
corp_split = [n for n in all_names if "분할" in n]

# ═════ 2. 공시검색 · 원문 ═════
list_q = {
    "page_count": q_dart("dart_detail_2019001", "페이지당 건수(1~100) 기본값 : 10, 최대값 : 100"),
    "last_reprt_at": q_dart("dart_detail_2019001", "최종보고서만 검색여부(Y or N) / 1) 기본값: N (N지정시 정정보고서를 포함한 제출 보고서 전체를 검색함)"),
    "bgn_de_limit": q_dart("dart_detail_2019001", "고유번호(corp_code)가 없는 경우 검색기간은 3개월로 제한"),
    "pblntf_ty_I": q_dart("dart_detail_2019001", "I : 거래소공시"),
    "I001": q_dart("dart_detail_2019001", "I001 | 수시공시"),
    "rcept_dt": q_dart("dart_detail_2019001", "공시 접수일자(YYYYMMDD)"),
    "report_nm_correction": q_dart("dart_detail_2019001", "[기재정정] : 본 보고서명으로 이미 제출된 보고서의 기재내용이 변경되어 제출된 것임"),
    "rm_correction": q_dart("dart_detail_2019001", "정 : 본 보고서 제출 후 정정신고가 있으니 관련 보고서를 참조하시기 바람"),
    "rcept_no": q_dart("dart_detail_2019001", "접수번호(14자리)"),
}
list_keys = [k for k, _ in resp_keys("dart_detail_2019001")]
doc_q = {"document_req": q_dart("dart_detail_2019003", "rcept_no | 접수번호 | STRING(14) | Y | 접수번호"),
         "document_out": q_dart("dart_detail_2019003", "Zip FILE (binary)")}
detail_req = q_dart("dart_detail_2020024", "bgn_de | 시작일(최초접수일) | STRING(8) | Y | 검색시작 접수일자(YYYYMMDD)")

DETAIL = {"rights_issue": ("2020023", "piicDecsn"), "bonus_issue": ("2020024", "fricDecsn"), "rights_bonus_issue": ("2020025", "pifricDecsn"),
          "capital_reduction": ("2020026", "crDecsn"), "merger": ("2020050", "cmpMgDecsn"), "spinoff": ("2020051", "cmpDvDecsn"),
          "spinoff_merger": ("2020052", "cmpDvmgDecsn")}
WANT = re.compile(r"비율|기준일|기일|상장|매매거래|권리락|배정|주당|발행가|정지")
detail_fields = {}
for kind, (aid, ep) in DETAIL.items():
    ks = resp_keys(f"dart_detail_{aid}")
    detail_fields[kind] = {"endpoint": ep, "apiId": aid, "date_ratio_fields": [{"key": k, "name": n} for k, n in ks if WANT.search(n)],
                           "has_record_date": any("기준일" in n for _, n in ks), "has_listing_date": any("상장" in n and "예정일" in n for _, n in ks),
                           "has_ex_rights_date": any("권리락" in n for _, n in ks), "has_halt_period": any("매매거래" in n and "정지" in n for _, n in ks),
                           "has_original_rcept_field": any(re.search(r"원.*접수|최초.*접수|정정", n) for _, n in ks), "n_response_keys": len(ks),
                           "source": dart_src(f"dart_detail_{aid}")}

# ═════ 3. KIS(공식 저장소) ═════
CH = "examples_llm/domestic_stock/inquire_daily_itemchartprice/inquire_daily_itemchartprice.py"
CHK = "examples_llm/domestic_stock/inquire_daily_itemchartprice/chk_inquire_daily_itemchartprice.py"
AUTH = "examples_llm/kis_auth.py"
kis_q = {
    "api_name": q_kis(CH, "[국내주식] 기본시세 > 국내주식기간별시세(일/주/월/년)[v1_국내주식-016]"),
    "endpoint": q_kis(CH, 'API_URL = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"'),
    "tr_id": q_kis(CH, 'tr_id = "FHKST03010100"'),
    "adj_flag": q_kis(CH, "fid_org_adj_prc (str): [필수] 수정주가 원주가 가격 여부 (ex. 0:수정주가 1:원주가)"),
    "row_limit": q_kis(CH, "실전계좌/모의계좌의 경우, 한 번의 호출에 최대 100건까지 확인 가능합니다."),
    "date2_limit": q_kis(CH, "fid_input_date_2 (str): [필수] 입력 날짜 2 (ex. 조회 종료일자 (최대 100개))"),
    "market": q_kis(CH, "fid_cond_mrkt_div_code (str): [필수] 조건 시장 분류 코드 (ex. J:KRX, NX:NXT, UN:통합)"),
    "period": q_kis(CH, "fid_period_div_code (str): [필수] 기간분류코드 (ex. D:일봉 W:주봉, M:월봉, Y:년봉)"),
    "no_cont_in_call": q_kis(CH, 'res = ka._url_fetch(API_URL, tr_id, "", params)'),
    "f_date": q_kis(CHK, "'stck_bsop_date': '주식 영업 일자'"), "f_close": q_kis(CHK, "'stck_clpr': '주식 종가'"),
    "f_lock": q_kis(CHK, "'flng_cls_code': '락 구분 코드'"), "f_prtt": q_kis(CHK, "'prtt_rate': '분할 비율'"), "f_mod": q_kis(CHK, "'mod_yn': '변경 여부'"),
    "token": q_kis(AUTH, "# Token 발급, 유효기간 1일, 6시간 이내 발급시 기존 token값 유지, 발급시 알림톡 무조건 발송"),
    "readme_official": q_kis("README.md", "**[당사에서 제공하는 샘플코드에 대한 유의사항]**"),
    "readme_reference": q_kis("README.md", "고객님의 개발 부담을 줄이고자 참고용으로 제공되고 있습니다."),
}
KSD = {}
for n, title, fields in (
        ("ksdinfo_rev_split", "# [국내주식] 종목정보 > 예탁원정보(액면교체일정)[국내주식-148]",
         ["'record_date': '기준일'", "'inter_bf_face_amt': '변경전액면가'", "'inter_af_face_amt': '변경후액면가'", "'td_stop_dt': '매매거래정지기간'", "'list_dt': '상장/등록일'"]),
        ("ksdinfo_bonus_issue", "# [국내주식] 종목정보 > 예탁원정보(무상증자일정)[국내주식-144]",
         ["'record_date': '기준일'", "'fix_rate': '확정배정율'", "'right_dt': '권리락일'", "'odd_pay_dt': '단주대금지급일'", "'list_date': '상장/등록일'"]),
        ("ksdinfo_cap_dcrs", "# [국내주식] 종목정보 > 예탁원정보(자본감소일정) [국내주식-149]",
         ["'record_date': '기준일'", "'reduce_cap_rate': '감자배정율'", "'comp_way': '계산방법'", "'td_stop_dt': '매매거래정지기간'", "'list_dt': '상장/등록일'"]),
        ("ksdinfo_merger_split", "# [국내주식] 종목정보 > 예탁원정보(합병_분할일정)[국내주식-147]",
         ["'record_date': '기준일'", "'merge_rate': '비율'", "'td_stop_dt': '매매거래정지기간'", "'list_dt': '상장/등록일'", "'odd_amt_pay_dt': '단주대금지급일'"]),
        ("ksdinfo_paidin_capin", "# [국내주식] 종목정보 > 예탁원정보(유상증자일정)[국내주식-143]",
         ["'record_date': '기준일'", "'fix_rate': '확정배정율'", "'fix_price': '발행예정가'", "'right_dt': '권리락일'", "'list_date': '상장/등록일'"])):
    rel_chk = f"examples_llm/domestic_stock/{n}/chk_{n}.py"
    rel = f"examples_llm/domestic_stock/{n}/{n}.py"
    KSD[n] = {"title": q_kis(rel_chk, title), "fields": [q_kis(rel_chk, f) for f in fields],
              "continuation": q_kis(rel, 'if tr_cont == "M":'), "source": kis_src(rel_chk),
              "available_at_field": False, "note": "응답 칸 목록에 공개 시각 · 접수번호 칸 없음 → 그 레코드가 언제 알려졌는지 모름"}
local_repo = {"file": "broker_kis.py", "line": 300, "claim": "FID_ORG_ADJ_PRC=0은 수정주가", "tier": "REPO_CODE(근거 순위 4)"}

# ═════ 출력 ═════
OUT.mkdir(parents=True, exist_ok=True)
blocked_hosts = [f for f in FETCH if f.get("http") in ("000", "403")]
matrix = {"generated_at_kst": NOW, "rule": "공식 도메인 원문만 · WebFetch(AI 요약) 미사용 · 원문은 로컬 보관(커밋 안 함) · sha256만 공개",
          "fetches": FETCH, "kis_official_repo": {"url": "https://github.com/koreainvestment/open-trading-api", "commit": KIS_COMMIT,
                                                   "how": "공개 저장소 git 읽기(코드 실행 안 함)", "readme_official": kis_q["readme_official"], "readme_reference": kis_q["readme_reference"]},
          "access_failures": [{"host": re.sub(r"https?://([^/]+).*", r"\1", f["url"]), "url": f["url"], "http": f["http"], "why": f.get("err") or "서버 403(Access Denied)"} for f in blocked_hosts],
          "rows": [
              {"id": "DART-LIST-ALL", "source": [dart_src(n) for n in ("dart_guide_main", "dart_guide_DS002", "dart_guide_DS003", "dart_guide_DS004", "dart_guide_ds005", "dart_guide_DS006")],
               "claim": "OpenDART API 6그룹 전체 목록에 주식분할 · 주식병합 · 액면교체 이름의 API가 없음", "field": "API명",
               "evidence": {"groups": {g: len(v) for g, v in groups.items()}, "total": len(all_names), "split_like_names": split_like, "names_with_분할": corp_split},
               "verdict": "ACCEPT" if not split_like else "REVISE"},
              {"id": "DART-LIST-API", "source": [dart_src("dart_detail_2019001")], "claim": "공시검색 칸 · 정밀도 · 정정 표시", "field": "list.json", "evidence": list_q,
               "response_keys": list_keys, "verdict": "ACCEPT"},
              {"id": "DART-DOCUMENT", "source": [dart_src("dart_detail_2019003")], "claim": "공시원문은 접수번호로 zip 파일 · 내부 칸 구조는 가이드에 없음", "evidence": doc_q, "verdict": "ACCEPT(경로) · NEEDS_DATA(원문 안 칸)"},
              {"id": "DART-DETAIL-REQ", "source": [dart_src("dart_detail_2020024")], "claim": "상세 API 검색 기간은 '최초접수일' 기준", "evidence": detail_req,
               "verdict": "ACCEPT", "consequence": "상세 응답이 어느 정정 버전인지 가이드에 없음 → 버전 PIT로 쓰지 않음(UNKNOWN_CA_VERSION_PIT)"},
              {"id": "KIS-CHART", "source": [kis_src(CH), kis_src(CHK)], "claim": "기간별 시세 endpoint · TR · 원/수정 값 방향 · 100건 · 시장 코드 · 응답 칸", "evidence": kis_q, "verdict": "ACCEPT(공식 샘플 등급 · 포털 원문 대조 못 함)"},
              {"id": "KIS-KSDINFO", "source": [v["source"] for v in KSD.values()], "claim": "예탁원 기업행동 일정 API 5개의 칸", "evidence": {k: {"title": v["title"], "fields": v["fields"]} for k, v in KSD.items()},
               "verdict": "ACCEPT(칸 존재) · UNKNOWN_CA_VERSION_PIT(공개 시각 칸 없음)"},
              {"id": "REPO-BROKER", "source": [local_repo], "claim": "저장소 코드도 0 = 수정주가로 씀", "verdict": "ACCEPT(일치 · 보조)"},
              {"id": "KRX-RULES", "source": [{"url": f["url"], "http": f["http"], "retrieved_at_kst": f["retrieved_at_kst"]} for f in FETCH if "krx" in f.get("url", "")],
               "claim": "권리락 · 매매거래정지 · 변경상장 · 주식분할/병합 공시 항목(거래소 규정)", "verdict": "BLOCKED_NO_OFFICIAL_EVIDENCE", "why": "law.krx.co.kr · www.krx.co.kr 환경 정책 차단 · kind.krx.co.kr 서버 403(2회)"},
              {"id": "KIS-PORTAL", "source": [{"url": f["url"], "http": f["http"], "retrieved_at_kst": f["retrieved_at_kst"]} for f in FETCH if "apiportal" in f.get("url", "")],
               "claim": "KIS Developers 포털 원문", "verdict": "BLOCKED_NO_OFFICIAL_EVIDENCE", "why": "apiportal.koreainvestment.com 환경 정책 차단 → 공식 저장소로 대신"},
              {"id": "DART-WEB", "source": [{"url": f["url"], "http": f["http"], "retrieved_at_kst": f["retrieved_at_kst"]} for f in FETCH if "dart.fss.or.kr" in f.get("url", "") and "opendart" not in f.get("url", "")],
               "claim": "DART 공시 사이트(보고서명 선택지)", "verdict": "BLOCKED_NO_OFFICIAL_EVIDENCE", "why": "dart.fss.or.kr 환경 정책 차단"}]}
(OUT / "official-source-matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=1))
json.dump({"groups": groups, "list_q": list_q, "list_keys": list_keys, "detail_fields": detail_fields, "kis_q": kis_q, "KSD": KSD, "split_like": split_like,
           "corp_split": corp_split, "doc_q": doc_q, "detail_req": detail_req}, open(OUT / "_facts.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({"api_total": len(all_names), "groups": {g: len(v) for g, v in groups.items()}, "split_like": split_like, "with_분할": corp_split,
                  "list_has_original_rcept_key": any("orgn" in k or "orig" in k for k in list_keys), "list_keys": list_keys,
                  "detail_flags": {k: {x: v[x] for x in ("has_record_date", "has_listing_date", "has_ex_rights_date", "has_halt_period", "has_original_rcept_field")} for k, v in detail_fields.items()},
                  "kis_commit": KIS_COMMIT, "access_failures": len(blocked_hosts)}, ensure_ascii=False))
