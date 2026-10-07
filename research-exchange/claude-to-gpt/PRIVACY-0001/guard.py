"""PRIVACY-0001 공개 전 민감정보 차단 게이트 2판(표준 라이브러리만, 규칙은 PREREG-LOCK 2 · 3장).

- scan_obj(obj): dict · list를 끝까지 따라가며 금지 키(정규화 뒤)와 문자열 값의 텍스트 규칙을 검사합니다.
- scan_text(text): 문서 · 메시지 텍스트를 줄마다 검사합니다.
- 결과에는 경로 · 줄 번호 · 규칙 코드만 담고 **값은 담지 않습니다**. self_check()가 결과 모양을 확인합니다.
- 명령줄: python3 -I guard.py 파일... → 파일마다 hash · 규칙 코드 · 개수 · PASS/FAIL만 출력합니다.
mutations는 변이 시험에서만 씁니다.
"""
import hashlib
import json
import re
import sys
import unicodedata

FORBIDDEN = ("accountno", "acctno", "cano", "acntprdtcd", "brokerorderno", "orderno", "odno", "rawresponse",
             "rawpayload", "appkey", "appsecret", "accesskey", "secretkey", "privatekey", "accesstoken",
             "refreshtoken", "authorization", "htsid", "sessionurl", "sessionid")
ALLOW_KEYS = {"orderid", "tradeid", "recordid", "evidenceref", "normalizedsha256", "rawpayloadsha256",
              "strategyhash", "cutoffhash"}
ORDER_TOKENS = {"orderno", "odno", "brokerorderno"}
EMPTY_TEXT = {"null", "none", "nil", "-"}
_SESSION_HOST = re.escape("claude" + ".ai/code/" + "session" + "_")
SESSION_RE = re.compile(_SESSION_HOST + r"[A-Za-z0-9]{6,}")
BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
ASSIGN_RE = re.compile(r"[\"'`]?([^\W\d_][\w\-]*)[\"'`]?\s*[:=]\s*[\"'`]?([^\s\"'`,;}\]]*)")
FINDING_KEYS = {"path", "line", "rule"}


class Guard:
    def __init__(self, mutations=()):
        self.mut = set(mutations)
        self.tokens = tuple(t for t in FORBIDDEN
                            if not ("M3" in self.mut and t in ORDER_TOKENS)
                            and not ("M7" in self.mut and t == "authorization"))

    def canon(self, key):
        k = unicodedata.normalize("NFKC", str(key))
        if "M1" not in self.mut:
            k = k.casefold()
        if "M2" in self.mut:
            return k
        return "".join(ch for ch in k if ch.isalnum())

    def forbidden_token(self, key):
        c = self.canon(key)
        if c in ALLOW_KEYS:
            return None
        if c in self.tokens:
            return c
        hits = [t for t in self.tokens if len(t) >= 6 and c.endswith(t)]
        return max(hits, key=len) if hits else None

    def _text_rules(self, s):
        rules = []
        if "M6" not in self.mut and SESSION_RE.search(s):
            rules.append(("TEXT_SESSION_URL", SESSION_RE.search(s).group(0)))
        if "M7" not in self.mut and BEARER_RE.search(s):
            rules.append(("TEXT_BEARER", BEARER_RE.search(s).group(0)))
        for m in ASSIGN_RE.finditer(s):
            tok = self.forbidden_token(m.group(1))
            val = m.group(2)
            if tok and val and val.casefold() not in EMPTY_TEXT:
                rules.append(("TEXT_KEY_ASSIGN:" + tok, val))
        return rules

    def _add(self, out, path, line, rule, value):
        f = {"path": path, "line": line, "rule": rule}
        if "M8" in self.mut or "M9" in self.mut:          # 변이: 발견 값을 결과에 넣음(노출)
            f["value"] = value
        out.append(f)

    def scan_obj(self, obj, path="$", out=None, depth=0):
        out = [] if out is None else out
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{path}.{k}"
                tok = self.forbidden_token(k)
                if tok and v not in (None, "", [], {}):
                    self._add(out, p, None, "KEY_FORBIDDEN:" + tok, v)
                if isinstance(v, dict) and "M4" not in self.mut:
                    self.scan_obj(v, p, out, depth + 1)
                elif isinstance(v, list) and "M5" not in self.mut:
                    self.scan_obj(v, p, out, depth + 1)
                elif isinstance(v, str):
                    for rule, val in self._text_rules(v):
                        self._add(out, p, None, rule, val)
        elif isinstance(obj, list) and "M5" not in self.mut:
            for i, v in enumerate(obj):
                p = f"{path}[{i}]"
                if isinstance(v, (dict, list)):
                    self.scan_obj(v, p, out, depth + 1)
                elif isinstance(v, str):
                    for rule, val in self._text_rules(v):
                        self._add(out, p, None, rule, val)
        elif isinstance(obj, str):
            for rule, val in self._text_rules(obj):
                self._add(out, path, None, rule, val)
        return out

    def scan_text(self, text):
        out = []
        for n, line in enumerate(text.splitlines(), 1):
            for rule, val in self._text_rules(line):
                self._add(out, None, n, rule, val)
        return out

    def self_check(self, findings):
        """결과 redaction 자기검사: 발견마다 path · line · rule 세 키만 있어야 함(값 금지)."""
        if "M9" in self.mut:
            return True
        return all(set(f) <= FINDING_KEYS for f in findings)


def summarize(findings):
    rules = {}
    for f in findings:
        rules[f["rule"]] = rules.get(f["rule"], 0) + 1
    # 규칙 코드를 dict 키로 쓰지 않음(코드 안의 토큰 이름이 다시 금지 키로 읽히지 않게) — [코드, 개수] 목록
    return {"rules": [[k, n] for k, n in sorted(rules.items())], "count": len(findings)}


def check_file(path, guard=None):
    g = guard or Guard()
    raw = open(path, "rb").read()
    text = raw.decode("utf-8", errors="replace")
    findings = g.scan_text(text)
    if path.endswith(".json"):
        try:
            findings += g.scan_obj(json.loads(text))
        except ValueError:
            pass
    s = summarize(findings)
    return {"sha256": hashlib.sha256(raw).hexdigest(), "rules": s["rules"], "count": s["count"],
            "result": "PASS" if not findings else "FAIL", "self_check": g.self_check(findings)}


if __name__ == "__main__":
    rep = {p: check_file(p) for p in sys.argv[1:]}
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    sys.exit(0 if all(r["result"] == "PASS" and r["self_check"] for r in rep.values()) else 1)
