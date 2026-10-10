"""ERN-0036 round 2 — DART '매출액 또는 손익구조 30%(대규모 15%) 이상 변경' 공시 원문 · 판 복원 타당성 시험(수익 셈 없음 · 조회 전용).
사전등록: research-exchange/claude-to-gpt/ERN-0036/FEAS-PREREG.md
- 표본(수익 안 봄 · 미리 고정): public-daily-v2에서 모집단(6자리 숫자 · 끝 5/7/9 제외) 코드를
  '뒤에 사라짐'(마지막 날 20261007에 줄 없음) · '지금 있음'으로 나눠 sha256(코드) 작은 순으로 각 10 · 20개.
- 호출 상한 200(넘으면 멈춤): corpCode.xml 1 · list.json(corp_code · 20150101 ~ 20261007 · last_reprt_at=N · 100줄씩 · 종목당 최대 3쪽) ·
  document.xml(종목당 1 · 최대 30).
- 원문 고르기: 그 종목 손익구조 공시 가운데 접수일이 20200301에 가장 가까운 것(같으면 먼저 것).
- 저장: 뽑은 칸 · 원문 sha256 · 호출 기록만(원문 · 키 · 응답 본문은 저장 · 출력하지 않음).
python research/e010_probe.py            (환경: DART_CRTFC_KEY)"""
import csv
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "research-exchange/claude-to-gpt/ERN-0036/feas/probe.json"
KEY = os.getenv("DART_CRTFC_KEY", "").strip()
CAP, LAST, PIVOT = 200, "20261007", "20200301"
API = "https://opendart.fss.or.kr/api/"
calls = []


def pop(c):
    return bool(re.fullmatch(r"[0-9]{6}", c)) and not c.endswith(("5", "7", "9"))


def sample():
    seen, last = set(), set()
    for f in sorted((ROOT / "public-daily-v2").glob("*.csv")):
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if pop(r["코드"]):
                seen.add(r["코드"])
                if r["날"] == LAST:
                    last.add(r["코드"])
    h = lambda c: hashlib.sha256(c.encode()).hexdigest()
    gone = sorted(seen - last, key=h)[:10]
    now = sorted(last, key=h)[:20]
    return [(c, "gone") for c in gone] + [(c, "now") for c in now]


def get(ep, **p):
    if len(calls) >= CAP:
        raise RuntimeError("호출 상한")
    t0 = time.time()
    r = requests.get(API + ep, params={"crtfc_key": KEY, **p}, timeout=(10, 60))
    calls.append([ep, r.status_code, round(time.time() - t0, 2)])
    time.sleep(0.15)
    return r


def corp_map():
    raw = get("corpCode.xml").content
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        root = ElementTree.fromstring(z.read("CORPCODE.xml"))
    out = {}
    for n in root.findall("list"):
        s = (n.findtext("stock_code") or "").strip()
        if s:
            out[s] = (n.findtext("corp_code"), (n.findtext("corp_name") or "").strip(), (n.findtext("modify_date") or "").strip())
    return out


def listing(corp):
    rows = []
    for page in range(1, 4):
        j = get("list.json", corp_code=corp, bgn_de="20150101", end_de=LAST, last_reprt_at="N", page_no=page, page_count=100).json()
        if j.get("status") != "000":
            return rows, j.get("status")
        rows += j.get("list", [])
        if page >= int(j.get("total_page") or 1):
            break
    return rows, "000"


NUM = re.compile(r"-?\(?[0-9][0-9,]*\)?")


def days(a, b):
    """yyyymmdd 두 날 사이 날 수(b − a)."""
    d = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    return (d(b) - d(a)).days


def to_num(s):
    s = s.strip()
    neg = s.startswith("(") or s.startswith("-")
    v = int(re.sub(r"[^0-9]", "", s))
    return -v if neg else v


def parse(xml_text):
    """표 줄마다 칸 글을 모아 매출액 · 영업이익 · 당기순이익의 (당해, 직전) · 단위 · 재무제표 종류를 찾음."""
    t = xml_text
    unit = re.search(r"단위\s*[:：]\s*(원|천원|백만원|억원)", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    kind = re.search(r"재무제표의\s*종류\s*</?[^>]*>?\s*(?:<[^>]+>\s*)*(연결|별도|개별)", t)
    plain = html.unescape(re.sub(r"<[^>]+>", " ", t))
    if not kind:
        kind = re.search(r"재무제표의\s*종류\s+(연결|별도|개별)", re.sub(r"\s+", " ", plain))
    rows = re.findall(r"<TR[^>]*>(.*?)</TR>", t, flags=re.S | re.I)
    got = {}
    for row in rows:
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<T[DEU][^>]*>(.*?)</T[DEU]>", row, flags=re.S | re.I)]
        if not cells:
            continue
        head = cells[0].replace(" ", "")
        key = ("매출" if head.startswith("-매출액") or head.startswith("매출액") else
               "영업이익" if head.startswith("-영업이익") or head.startswith("영업이익") else
               "순이익" if head.startswith("-당기순이익") or head.startswith("당기순이익") else None)
        if key and key not in got:
            nums = [c for c in cells[1:] if NUM.fullmatch(c.replace(" ", ""))]
            if len(nums) >= 2:
                got[key] = [to_num(nums[0]), to_num(nums[1])]
    year = re.search(r"(20[12][0-9])\s*년\s*(?:12월\s*31일|사업연도|결산)", re.sub(r"\s+", " ", plain))
    return {"unit": unit.group(1) if unit else None, "kind": kind.group(1) if kind else None, "values": got,
            "year_hint": year.group(1) if year else None}


def main():
    if not KEY:
        print("DART_CRTFC_KEY 없음")
        return 1
    smp = sample()
    out = {"task": "ERN-0036", "stage": "feasibility", "started_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
           "sample": smp, "items": []}
    try:
        cmap = corp_map()
        for code, grp in smp:
            it = {"code": code, "group": grp}
            out["items"].append(it)
            if code not in cmap:
                it["status"] = "고유번호 없음"
                continue
            corp, name, mod = cmap[code]
            it.update(corp_code=corp, corp_name=name, corp_modify=mod)
            rows, st = listing(corp)
            it["list_status"], it["list_n"] = st, len(rows)
            pl = [r for r in rows if "손익구조" in r.get("report_nm", "")]
            it["pl_n"] = len(pl)
            it["pl_corrections"] = sum(1 for r in pl if "정정" in r.get("report_nm", ""))
            it["prelim_n"] = sum(1 for r in rows if "잠정" in r.get("report_nm", ""))
            if not pl:
                it["status"] = "손익구조 공시 없음"
                continue
            piv = date(2020, 3, 1)
            pick = min(pl, key=lambda r: (abs((date(int(r["rcept_dt"][:4]), int(r["rcept_dt"][4:6]), int(r["rcept_dt"][6:])) - piv).days), r["rcept_dt"]))
            it.update(rcept_no=pick["rcept_no"], rcept_dt=pick["rcept_dt"], report_nm=pick["report_nm"])
            same_corr = [r["rcept_no"] for r in pl if r["rcept_no"] != pick["rcept_no"] and abs(days(pick["rcept_dt"], r["rcept_dt"])) <= 60 and "정정" in r["report_nm"]]
            it["nearby_corrections"] = same_corr
            prior = [r["rcept_dt"] for r in rows if "잠정" in r.get("report_nm", "") and 0 <= days(r["rcept_dt"], pick["rcept_dt"]) <= 60]
            it["prelim_within_60d_before"] = len(prior)
            r = get("document.xml", rcept_no=pick["rcept_no"])
            try:
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    files = [f for f in z.infolist() if f.filename.lower().endswith(".xml")]
                    raw = z.read(max(files, key=lambda f: f.file_size))
            except (zipfile.BadZipFile, ValueError):
                it["status"] = "원문 받기 실패"
                continue
            enc = "euc-kr" if b"euc-kr" in raw[:300].lower() else "utf-8"
            text = raw.decode(enc, errors="replace")
            it["doc_sha256"] = hashlib.sha256(raw).hexdigest()
            it["parsed"] = parse(text)
            v = it["parsed"]["values"]
            it["status"] = "숫자 뽑음" if all(k in v for k in ("매출", "영업이익", "순이익")) and it["parsed"]["unit"] else "숫자 일부 · 단위 없음"
    except RuntimeError as e:
        out["stopped"] = str(e)
    out["calls"] = calls
    out["calls_n"] = len(calls)
    out["ended_kst"] = datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("호출", len(calls), "· 상태", dict(Counter(i.get("status") for i in out["items"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
