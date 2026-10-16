"""collect_dart_customers.py 합성 시험(네트워크 없음 · 9개): 재시도 호출 세기 · 목록 불완전 · 제목만 낱말 · 끝 상태 · 원문 상태 나누기 · 예산 멈춤 · XML 020 · HTTP 429/403 · 원문 보관 · 줄 구조 · 첨부정정 제외 · 목록 쪽 넘기기."""
import io, json, os, sys, zipfile, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["CUSTOMER_PAUSE"] = "0"
import importlib, requests
import collect_dart_customers as c
importlib.reload(c)
c.time.sleep = lambda s: None

class R:
    def __init__(s, code, content): s.status_code, s.content = code, content

def seq(items):
    it = iter(items)
    def fake(*a, **k):
        x = next(it)
        if isinstance(x, Exception): raise x
        return x
    return fake

ok = 0
# 1. 재시도도 셈 · 예산 3이면 4번째 시도 전에 멈춤
c.BUDGET = 3
d = c.Dart("k")
c.requests.get = seq([requests.ConnectionError("x"), requests.ConnectionError("x"), R(200, b'{"status":"000"}')])
h, body = d.get("list.json", 5); assert h == 200 and d.used == 3, d.used
try:
    d.get("list.json", 5); raise AssertionError("예산 안 멈춤")
except c.Stop as e: assert e.kind == "budget"
ok += 1
# 2. 원문 XML 020 → limit 멈춤
c.BUDGET = 100
d = c.Dart("k")
c.requests.get = seq([R(200, b'<?xml version="1.0" encoding="UTF-8"?><result><status>020</status><message>x</message></result>')])
try:
    c.fetch(d, "000001", {"rcept_no": "1", "rcept_dt": "20200101", "report_nm": "사업보고서 (2019.12)", "rm": ""}); raise AssertionError
except c.Stop as e: assert e.kind == "limit"
ok += 1
# 3. HTTP 429 → limit · 403 → auth · XML 010 → auth · XML 014 → 원문 없음 기록
for resp, kind in [(R(429, b""), "limit"), (R(403, b""), "auth"), (R(200, b"<result><status>010</status></result>"), "auth")]:
    c.requests.get = seq([resp])
    try:
        c.fetch(d, "000001", {"rcept_no": "1", "rcept_dt": "20200101", "report_nm": "사업보고서", "rm": ""}); raise AssertionError
    except c.Stop as e: assert e.kind == kind, (e.kind, kind)
c.requests.get = seq([R(200, b"<result><status>014</status></result>")])
f = c.fetch(d, "000001", {"rcept_no": "1", "rcept_dt": "20200101", "report_nm": "사업보고서", "rm": ""})
assert f["state"] == "자료 없음 · DART 014", f["state"]
for resp in [R(200, b"<result><status>800</status></result>"), R(200, b"<result><status>900</status></result>"),
             R(404, b"<html>x</html>"), R(200, b"garbage")]:
    c.requests.get = seq([resp])
    f = c.fetch(d, "000001", {"rcept_no": "1", "rcept_dt": "20200101", "report_nm": "사업보고서", "rm": ""})
    assert f["state"].startswith("미해결"), f["state"]
ok += 1
# 4. 정상 ZIP: 원문 보관 · 줄 구조 · 장 제목 · 감사 문단 버림 셈
xml = ("<DOCUMENT><SECTION-1><TITLE ATOC=\"Y\">II. 사업의 내용</TITLE><P>마. 주요 매출처</P>"
       "<TABLE><TR><TD>삼성전자</TD><TD>29%</TD></TR><TR><TD>Xiaomi</TD><TD>10%</TD></TR></TABLE>"
       "<P>a</P><P>b</P><P>c</P><P>d</P><P>우리가 수행한 주요 감사절차</P><P>주요 고객의 월별 매출 추세</P></SECTION-1></DOCUMENT>").encode()
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z: z.writestr("1.xml", xml)
tmp = tempfile.mkdtemp(); c.RAW = c.Path(tmp)
c.requests.get = seq([R(200, buf.getvalue())])
f = c.fetch(d, "000001", {"rcept_no": "20200101000001", "rcept_dt": "20200101", "report_nm": "[기재정정]사업보고서 (2019.12)", "rm": ""})
assert f["state"] == "받음" and f["kind"] == "정정"
assert (c.Path(tmp) / "000001" / "20200101000001.zip").read_bytes() == buf.getvalue()
p = f["passages"]; assert len(p) == 1 and p[0]["title"] == "II. 사업의 내용", p
assert "| 삼성전자 | 29%" in p[0]["lines"] and "| Xiaomi | 10%" in p[0]["lines"], p[0]["lines"]
assert f["hits"] == 2 and f["drop"]["audit"] == 1, (f["hits"], f["drop"])
ok += 1
# 5. 첨부정정은 받지 않고 제외 범위로 기록(호출 0)
u = d.used
f = c.fetch(d, "000001", {"rcept_no": "2", "rcept_dt": "20200101", "report_nm": "[첨부정정]사업보고서 (2019.12)", "rm": ""})
assert f["state"].startswith("제외") and d.used == u
ok += 1
# 6. 목록 쪽 넘기기 영수증 + last_reprt_at=N
seen = []
pages = [R(200, json.dumps({"status": "000", "total_count": 3, "total_page": 2, "list": [{"rcept_no": "a", "rcept_dt": "1", "report_nm": "x"}, {"rcept_no": "b", "rcept_dt": "2", "report_nm": "y"}]}).encode()),
         R(200, json.dumps({"status": "000", "total_count": 3, "total_page": 2, "list": [{"rcept_no": "c", "rcept_dt": "3", "report_nm": "z"}]}).encode())]
it = iter(pages)
def fake(url, params=None, timeout=None):
    seen.append(params); return next(it)
c.requests.get = fake
rows, rc = c.listing(d, "corp", "20261016")
assert len(rows) == 3 and rc["pages"] == [1, 2] and rc["complete"] and all(p["last_reprt_at"] == "N" for p in seen)
ok += 1
# 7. 목록 불완전: 건수 불일치 · 뒤쪽 013 → 실패(None)
c.requests.get = seq([R(200, json.dumps({"status": "000", "total_count": 2, "total_page": 1, "list": [{"rcept_no": "a", "rcept_dt": "1", "report_nm": "x"}]}).encode())])
rows, rc = c.listing(d, "corp", "20261016"); assert rows is None and "불일치" in rc["fail"], rc
c.requests.get = seq([R(200, json.dumps({"status": "000", "total_count": 2, "total_page": 2, "list": [{"rcept_no": "a", "rcept_dt": "1", "report_nm": "x"}]}).encode()),
                      R(200, b'{"status":"013"}')])
rows, rc = c.listing(d, "corp", "20261016"); assert rows is None and "013" in rc["fail"], rc
c.requests.get = seq([R(200, b'{"status":"013"}')])
rows, rc = c.listing(d, "corp", "20261016"); assert rows == [] and rc["complete"]
ok += 1
# 8. 제목에만 낱말 · 뒤에 고객 표
lines = c.lines_of('<TITLE ATOC="Y">주요 매출처</TITLE><TABLE><TR><TD>삼성전자</TD><TD>30%</TD></TR></TABLE>'.encode())
found, total, drop = c.passages("1.xml", lines)
assert total == 1 and len(found) == 1 and "| 삼성전자 | 30%" in found[0]["lines"], (lines, found)
ok += 1
# 9. main: 목록 실패 · 원문 미해결이 있으면 '모두 받음'(0)이 아니라 4 · 영수증 기록
work = tempfile.mkdtemp(); c.OUT = c.Path(work) / "customer-data"; c.RAW = c.Path(work) / "raw"
os.environ["DART_CRTFC_KEY"] = "k"; os.environ["CUSTOMER_CODES"] = "000001,000002"
c.corp_map = lambda d: ({"000001": "c1", "000002": "c2"}, {"000001": "가", "000002": "나"})
c.listing = lambda d, corp, today: ((None, {"fail": "x"}) if corp == "c1" else
                                    ([{"rcept_no": "r1", "rcept_dt": "20200101", "report_nm": "사업보고서 (2019.12)", "rm": ""}], {"complete": True}))
c.requests.get = seq([R(200, b"<result><status>800</status></result>")])
assert c.main() == 4
rec = json.loads((c.OUT / "_last_run.json").read_text(encoding="utf-8"))
assert rec["state"] == "미해결 남음" and rec["목록 실패"] == 1 and rec["미해결"] == 1, rec
# 9b. 한도 멈춤은 2(부분 수집) · 키 문제는 3
c.requests.get = seq([R(429, b"")]); assert c.main() == 2
c.requests.get = seq([R(403, b"")]); assert c.main() == 3
ok += 1
print("시험 통과", ok, "/ 9")
