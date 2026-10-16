"""DART 사업보고서 원문에서 '주요 매출처 · 주요 고객' 문단을 모읍니다(공개 자료 · MPOS H2 고객–공급사 연결).

- 대상: dart-events/에 있는 종목(437) · 사업보고서(사업연도 2016 ~) 원본과 [기재정정]본 모두 · 접수일(rcept_dt) 그대로.
  그 시점에 공개된 판만 쓰려고 정정본도 따로 남깁니다(오늘 공급망을 옛날로 거꾸로 채우지 않음).
- 남기는 것: 원문에서 매출처 낱말 둘레 문단(풀이는 나중에 다시 할 수 있게 원문 그대로). 감사 의견 문단은 뺍니다.
- 키는 GitHub Secrets(DART_CRTFC_KEY)에서만 읽고, 주소 · 키 · 응답 오류문은 찍지 않습니다.
- 다시 돌리면 이미 받은 접수번호는 건너뜁니다. 호출 예산(CUSTOMER_BUDGET · 기본 7000)에서 멈춥니다.
"""
import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import date
from pathlib import Path

import requests

from providers import DataError, Official

API = "https://opendart.fss.or.kr/api/"
OUT = Path("customer-data")
KEYS = re.compile(r"주요\s?매출처|주요\s?고객|주요\s?거래처|주요\s?판매처|매출처\s?현황|외부\s?고객")
SKIP = re.compile(r"감사절차|감사인|핵심감사사항")
BUDGET = int(os.getenv("CUSTOMER_BUDGET", "7000"))
PAUSE = 0.6
FIRST = "20170101"
USED_FILE = os.getenv("CUSTOMER_USED_FILE", "")


class Stop(Exception):
    pass


class Dart:
    def __init__(self, key):
        self.key = key
        self.used = 0
        if USED_FILE:
            try:
                self.used = int(Path(USED_FILE).read_text().strip() or 0)
            except (OSError, ValueError):
                self.used = 0

    def keep(self):
        if USED_FILE:
            Path(USED_FILE).write_text(str(self.used))

    def get(self, endpoint, timeout, **params):
        if self.used >= BUDGET:
            raise Stop("이번에 쓸 호출 수를 다 썼습니다.")
        time.sleep(PAUSE)
        self.used += 1
        for turn in range(3):
            try:
                return requests.get(API + endpoint, params={"crtfc_key": self.key, **params}, timeout=(10, timeout))
            except requests.RequestException:
                if turn == 2:
                    return None
                time.sleep(3)

    def listing(self, corp, today):
        rows, page = [], 1
        while True:
            r = self.get("list.json", 30, corp_code=corp, bgn_de=FIRST, end_de=today, pblntf_detail_ty="A001",
                         page_no=page, page_count=100)
            try:
                data = r.json()
            except (AttributeError, ValueError):
                return None
            status = str(data.get("status"))
            if status == "013":
                return rows
            if status == "020":
                raise Stop("DART 호출 한도(020).")
            if status in ("010", "011", "012", "901"):
                raise Stop(f"DART 키 거절({status}).")
            if status != "000":
                return None
            rows += [{k: x.get(k) for k in ("rcept_no", "rcept_dt", "report_nm", "rm")} for x in data.get("list") or []]
            if page >= int(data.get("total_page") or 1):
                return rows
            page += 1

    def document(self, rcept_no):
        r = self.get("document.xml", 120, rcept_no=rcept_no)
        if r is None:
            return None
        try:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                return [z.read(n) for n in z.namelist()]
        except zipfile.BadZipFile:
            try:
                if str(r.json().get("status")) == "020":
                    raise Stop("DART 호출 한도(020).")
            except ValueError:
                pass
            return None


def text_of(raw):
    for enc in ("utf-8", "cp949"):
        try:
            s = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        s = raw.decode("utf-8", "ignore")
    s = re.sub(r"<(TD|TE|TH)[^>]*>", " | ", s, flags=re.I)
    s = re.sub(r"<(P|TR|TITLE|BR)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&cr;", "\n")
    return re.sub(r"\s+", " ", s)


def passages(text):
    out, last = [], -10**9
    for m in KEYS.finditer(text):
        if m.start() - last < 500:
            continue
        if SKIP.search(text[max(0, m.start() - 200): m.start() + 60]):
            continue
        cut = text[max(0, m.start() - 120): m.start() + 900]
        last = m.start()
        out.append({"at": m.start(), "text": cut.strip()})
        if len(out) >= 14:
            break
    return out


def kind_of(name):
    name = name or ""
    if "첨부" in name:
        return None
    return "정정" if "정정" in name else "원본"


def load(code):
    try:
        return json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"code": code, "filings": []}


def save(body):
    OUT.mkdir(exist_ok=True)
    body["filings"].sort(key=lambda f: (f["rcept_dt"], f["rcept_no"]))
    (OUT / f"{body['code']}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")


def codes():
    picked = [c.strip() for c in os.getenv("CUSTOMER_CODES", "").split(",") if c.strip()]
    if not picked:
        picked = sorted(p.stem for p in Path("dart-events").glob("*.json"))
    return [c for c in picked if re.fullmatch(r"[0-9]{6}", c)]


def main():
    key = os.environ.get("DART_CRTFC_KEY", "").strip()
    if not key:
        print("DART 키가 없습니다.")
        return 1
    try:
        official = Official()
        official.corp("005930")
    except DataError as error:
        print("DART 기업 목록을 받지 못했습니다 ·", error)
        return 1
    d = Dart(key)
    today = date.today().strftime("%Y%m%d")
    done = failed = 0
    try:
        for code in codes():
            corp = (official.corps or {}).get(code)
            body = load(code)
            if not corp:
                body["why"] = "DART에 없음"
                save(body)
                continue
            have = {f["rcept_no"] for f in body["filings"] if f.get("passages") is not None}
            rows = d.listing(corp, today)
            if rows is None:
                failed += 1
                print(code, "목록 실패", flush=True)
                continue
            body["name"] = official.names.get(code)
            body["listed_reports"] = rows
            new = 0
            for r in sorted(rows, key=lambda x: x["rcept_dt"]):
                kind = kind_of(r["report_nm"])
                if kind is None or r["rcept_no"] in have:
                    continue
                parts = d.document(r["rcept_no"])
                filing = {**r, "kind": kind}
                if parts is None:
                    filing["passages"] = None
                    filing["why"] = "원문 받기 실패"
                else:
                    text = " ".join(text_of(p) for p in parts)
                    filing["chars"] = len(text)
                    filing["passages"] = passages(text)
                body["filings"] = [f for f in body["filings"] if f["rcept_no"] != r["rcept_no"]] + [filing]
                new += 1
            body["checked"] = today
            save(body)
            d.keep()
            done += 1
            print(code, body["name"], "보고서", len(rows), "· 새로", new, "· 호출", d.used, flush=True)
    except Stop as why:
        print(f"멈춤 · {why} · 끝낸 종목 {done} · 호출 {d.used}", flush=True)
        if "body" in locals():
            save(body)
        d.keep()
        return 2
    print(f"끝 · 종목 {done} · 목록 실패 {failed} · 호출 {d.used}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
