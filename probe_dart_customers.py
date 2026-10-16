"""DART 사업보고서 원문에 '주요 매출처 · 주요 고객'이 이름까지 적혀 있는지 찔러 봅니다(조회 전용 · MPOS H2 자료 감사).

- 종목 25개(공급망에 있을 법한 부품 · 장비 · 소재 회사 위주)의 사업보고서 목록(정정본 포함 · 접수일)을 받고,
  종목마다 사업연도 2018 · 2021 · 2024 원본 보고서 원문을 받아 매출처 관련 문단만 잘라 남깁니다.
- 키는 GitHub Secrets(DART_CRTFC_KEY)에서만 읽고, 주소 · 키 · 응답 본문 오류문은 찍지 않습니다.
- 저장: customer-probe/probe.json(공시 원문 일부 · 공개 자료). 호출 수는 약 25 + 75번.
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
CODES = ("009150 011070 042700 012330 204320 018880 039030 240810 036930 095340 058470 357780 005290 "
         "066970 247540 000660 005930 003670 006400 051910 010120 267260 272210 064350 047810").split()
YEARS = ("2018", "2021", "2024")
KEYS = ("주요 매출처", "주요매출처", "주요 고객", "주요고객", "주요 거래처", "주요거래처", "매출처", "고객사")
NAMED = re.compile(r"삼성|LG|엘지|현대|기아|SK|에스케이|애플|Apple|APPLE|테슬라|Tesla|TSMC|인텔|Intel|마이크론|Micron|"
                   r"화웨이|BOE|GM|포드|Ford|폭스바겐|VW|BMW|도요타|소니|Sony|퀄컴|Qualcomm|구글|Google|아마존|Amazon")
ANON = re.compile(r"[A-Z]사|고객사\s?[A-Z]|[A-Z]\s?고객|거래처\s?[A-Z]|비공개|기재\s?생략|영업\s?비밀|기밀")
OUT = Path("customer-probe/probe.json")
PAUSE = 0.7


def ask_json(key, endpoint, **params):
    for turn in range(3):
        try:
            return requests.get(API + endpoint, params={"crtfc_key": key, **params}, timeout=(10, 30)).json()
        except (requests.RequestException, ValueError) as error:
            if turn == 2:
                return {"status": "err", "why": type(error).__name__}
            time.sleep(3)


def ask_doc(key, rcept_no):
    for turn in range(3):
        try:
            r = requests.get(API + "document.xml", params={"crtfc_key": key, "rcept_no": rcept_no}, timeout=(10, 120))
            return r.content
        except requests.RequestException as error:
            if turn == 2:
                return type(error).__name__.encode()
            time.sleep(3)


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
    return re.sub(r"[ \t]+", " ", s)


def snippets(text):
    hits, last = [], -10**9
    for m in re.finditer("|".join(re.escape(k) for k in KEYS), text):
        if m.start() - last < 600:
            continue
        last = m.start()
        hits.append(text[max(0, m.start() - 150): m.start() + 650].strip())
        if len(hits) >= 8:
            break
    return hits


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
    today = date.today().strftime("%Y%m%d")
    calls, body = 0, {"made": today, "codes": {}}
    for code in CODES:
        corp = (official.corps or {}).get(code)
        if not corp:
            body["codes"][code] = {"why": "DART에 없음"}
            continue
        time.sleep(PAUSE)
        calls += 1
        got = ask_json(key, "list.json", corp_code=corp, bgn_de="20170101", end_de=today,
                       pblntf_detail_ty="A001", page_count=100)
        status = str(got.get("status"))
        if status in ("020", "010", "011", "012", "901"):
            print(f"멈춤 · DART 상태 {status} · 호출 {calls}")
            break
        rows = [{k: r.get(k) for k in ("rcept_no", "rcept_dt", "report_nm")} for r in (got.get("list") or [])]
        entry = {"name": official.names.get(code), "reports": rows, "docs": {}}
        for year in YEARS:
            pick = [r for r in rows if f"({int(year)}.12)" in (r["report_nm"] or "") and "정정" not in r["report_nm"]
                    and "첨부" not in r["report_nm"]]
            if not pick:
                entry["docs"][year] = {"why": "원본 보고서 없음"}
                continue
            r = sorted(pick, key=lambda x: x["rcept_dt"])[0]
            time.sleep(PAUSE)
            calls += 1
            raw = ask_doc(key, r["rcept_no"])
            doc = {"rcept_no": r["rcept_no"], "rcept_dt": r["rcept_dt"], "zip_bytes": len(raw)}
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    text = "\n".join(text_of(z.read(n)) for n in z.namelist())
            except zipfile.BadZipFile:
                doc["why"] = "원문 묶음 아님(" + str(len(raw)) + "바이트)"
                entry["docs"][year] = doc
                continue
            cut = snippets(text)
            doc.update({"text_chars": len(text), "snips": cut,
                        "named": sum(bool(NAMED.search(s)) for s in cut),
                        "anon": sum(bool(ANON.search(s)) for s in cut)})
            entry["docs"][year] = doc
        body["codes"][code] = entry
        d = entry["docs"]
        print(code, entry["name"], "보고서", len(rows), "·",
              " ".join(f"{y}:{len(v.get('snips', []))}/{v.get('named', '-')}/{v.get('anon', '-')}" for y, v in d.items()),
              "· 호출", calls, flush=True)
    body["calls"] = calls
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    got_docs = [v for e in body["codes"].values() for v in e.get("docs", {}).values() if "snips" in v]
    print(f"끝 · 원문 {len(got_docs)}개 · 문단 있음 {sum(bool(v['snips']) for v in got_docs)} · "
          f"이름 보임 {sum(v['named'] > 0 for v in got_docs)} · 익명 표시 {sum(v['anon'] > 0 for v in got_docs)} · 호출 {calls}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
