"""collect_dart_contracts.py 합성 시험: 본문 칸 뽑기 · 해지/정정 구분 · 목록에서 공급계약만 거르기(네트워크 없음)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["CUSTOMER_PAUSE"] = "0"
import collect_dart_contracts as k
import collect_dart_customers as c
c.time.sleep = lambda s: None
xml = ("<TABLE><TR><TD>1. 판매ㆍ공급계약 내용</TD><TD>반도체 장비</TD></TR>"
       "<TR><TD>2. 계약내역</TD><TD>계약금액(원)</TD><TD>12,345,678,900</TD></TR>"
       "<TR><TD></TD><TD>최근 매출액(원)</TD><TD>98,765,432,100</TD></TR>"
       "<TR><TD></TD><TD>매출액 대비(%)</TD><TD>12.50</TD></TR>"
       "<TR><TD>3. 계약상대방</TD><TD>삼성전자(주)</TD></TR>"
       "<TR><TD>5. 계약기간</TD><TD>시작일</TD><TD>2024-01-02</TD></TR>"
       "<TR><TD></TD><TD>종료일</TD><TD>2024-12-31</TD></TR></TABLE>").encode()
f = k.parse(c.lines_of(xml))
assert f["계약금액"] == "12345678900" and f["최근매출액"] == "98765432100" and f["매출액대비%"] == "12.50", f
assert f["시작일"] == "2024-01-02" and f["종료일"] == "2024-12-31" and f["상대"].startswith("삼성전자"), f
assert k.parse(c.lines_of(b"<P>no table</P>"))["계약금액"] is None
assert k.kind_of("단일판매ㆍ공급계약해지") == "해지" and k.kind_of("[기재정정]단일판매ㆍ공급계약체결") == "정정"
class R:
    def __init__(s, b): s.status_code, s.content = 200, b
rows = [{"rcept_no": "1", "rcept_dt": "20200101", "report_nm": "단일판매ㆍ공급계약체결"},
        {"rcept_no": "2", "rcept_dt": "20200102", "report_nm": "주식등의대량보유상황보고서"},
        {"rcept_no": "3", "rcept_dt": "20200103", "report_nm": "단일판매 ㆍ 공급계약해지"}]
it = iter([R(json.dumps({"status": "000", "total_count": 3, "total_page": 1, "list": rows}).encode())])
c.requests.get = lambda *a, **kw: next(it)
got, rc = k.listing(c.Dart("k"), "corp", "20261016")
assert [r["rcept_no"] for r in got] == ["1", "3"] and rc["all_I"] == 3, (got, rc)
print("공급계약 시험 통과")
