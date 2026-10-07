"""PRIVACY-0001 합성 fixture(자리표시자만) — 실제 · 합성 비밀값을 파일에 넣지 않음.
자리표시자: {{SYN}} 합성 값, {{TOKEN}} 합성 토큰, {{SURL}} 합성 비공개 세션 주소 모양.
값은 시험 때 tests/materialize.py가 fixture id로 정해진 방식으로 메모리에서 만듭니다.
사용: python3 -I fixtures/make_fixtures.py fixtures/fixtures.json"""
import json, sys
H = "0123456789abcdef" * 4
A = []  # (id, kind, data, expected rule set)
def a(i, data, rules, kind="json"):
    A.append({"id": f"A{i:02d}", "kind": kind, "data": data, "expect_rules": sorted(rules)})
K = lambda c: "KEY_FORBIDDEN:" + c
a(1, {"ODNO": "{{SYN}}"}, [K("odno")])
a(2, {"odno": "{{SYN}}"}, [K("odno")])
a(3, {"order_no": "{{SYN}}"}, [K("orderno")])
a(4, {"ORDER-NO": "{{SYN}}"}, [K("orderno")])
a(5, {"orderNo": "{{SYN}}"}, [K("orderno")])
a(6, {"broker_order_no": "{{SYN}}"}, [K("brokerorderno")])
a(7, {"account_no": "{{SYN}}"}, [K("accountno")])
a(8, {"acctNo": "{{SYN}}"}, [K("acctno")])
a(9, {"CANO": "{{SYN}}"}, [K("cano")])
a(10, {"acnt_prdt_cd": "{{SYN}}"}, [K("acntprdtcd")])
a(11, {"appkey": "{{SYN}}"}, [K("appkey")])
a(12, {"APP_SECRET": "{{SYN}}"}, [K("appsecret")])
a(13, {"access-key": "{{SYN}}"}, [K("accesskey")])
a(14, {"secretKey": "{{SYN}}"}, [K("secretkey")])
a(15, {"private_key": "{{SYN}}"}, [K("privatekey")])
a(16, {"access_token": "{{SYN}}"}, [K("accesstoken")])
a(17, {"refreshToken": "{{SYN}}"}, [K("refreshtoken")])
a(18, {"Authorization": "{{SYN}}"}, [K("authorization")])
a(19, {"note": "Bearer {{TOKEN}}"}, ["TEXT_BEARER"])
a(20, {"raw_response": {"rt_cd": "0", "msg": "{{SYN}}"}}, [K("rawresponse")])
a(21, {"rawPayload": "{{SYN}}"}, [K("rawpayload")])
a(22, {"session_url": "{{SYN}}"}, [K("sessionurl")])
a(23, {"sessionId": "{{SYN}}"}, [K("sessionid")])
a(24, {"link": "{{SURL}}"}, ["TEXT_SESSION_URL"])
a(25, {"a": {"b": {"ODNO": "{{SYN}}"}}}, [K("odno")])
a(26, {"orders": [{"x": 1}, {"order_no": "{{SYN}}"}]}, [K("orderno")])
a(27, {"book": {"orders": [{"meta": {"acct_no": "{{SYN}}"}}]}}, [K("acctno")])
a(28, [{"access_token": "{{SYN}}"}], [K("accesstoken")])
a(29, "주문 기록 ODNO = {{SYN}} 이었음", ["TEXT_KEY_ASSIGN:odno"], kind="text")
a(30, "Authorization: Bearer {{TOKEN}}", ["TEXT_BEARER", "TEXT_KEY_ASSIGN:authorization"], kind="text")
a(31, "결과 링크는 {{SURL}} 입니다", ["TEXT_SESSION_URL"], kind="text")
a(32, {"kis_app_key": "{{SYN}}"}, [K("appkey")])
a(33, {"ＯＤＮＯ": "{{SYN}}"}, [K("odno")])
a(34, '{"orderNo": "{{SYN}}", "qty": 1}', ["TEXT_KEY_ASSIGN:orderno"], kind="text")
P = []
def p(i, data, kind="json"):
    P.append({"id": f"P{i:02d}", "kind": kind, "data": data, "expect_rules": []})
p(1, {"order_id": "o_000123", "trade_id": "t_01", "record_id": "r_01"})
p(2, {"evidence_ref": "ev_0123456789abcdef"})
p(3, {"normalized_sha256": H, "raw_payload_sha256": H})
p(4, {"strategy_hash": H, "cutoff_hash": H})
p(5, "1일봉 전략은 정배열과 수급을 보고 다음 거래일에 산다.", kind="text")
p(6, "`order_no` 필드는 원 주문번호를 담을 수 있으므로 공개하지 않는다.", kind="text")
p(7, "authorization 헤더와 토큰은 기록하지 않는다.", kind="text")
p(8, {"volcano_count": 3, "session": "REGULAR"})
p(9, "새 세션을 만들지 않는다. session_url 키는 금지 목록에 있다.", kind="text")
p(10, {"order_no": None})
p(11, {"orders": [{"order_id": "o1", "qty": 10}], "public_ok": True})
p(12, "ODNO 같은 키는 대소문자와 상관없이 막는다.", kind="text")
M = {"M1": ["A01", "A09", "A12"], "M2": ["A03", "A04", "A06"], "M3": ["A01", "A03", "A05"],
     "M4": ["A25", "A27"], "M5": ["A26", "A28"], "M6": ["A24", "A31"], "M7": ["A18", "A19", "A30"],
     "M8": ["REDACTION"], "M9": ["REDACTION"]}
assert len(A) >= 24 and len(P) >= 10
json.dump({"task": "PRIVACY-0001", "note": "자리표시자만 담은 합성 fixture. 값은 시험 때 메모리에서 만듦.",
           "attack": A, "allow": P, "mutants": M}, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(A), len(P), len(M))
