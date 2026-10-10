"""ERN-0036 round 2 — DART '매출액 또는 손익구조 30%(대규모 15%) 이상 변경' 공시 원문 · 판 복원 타당성 시험(수익 셈 없음 · 조회 전용).
사전등록: research-exchange/claude-to-gpt/ERN-0036/FEAS-PREREG.md
- 표본(수익 안 봄 · 미리 고정): public-daily-v2에서 모집단(6자리 숫자 · 끝 5/7/9 제외) 코드를
  '뒤에 사라짐'(마지막 날 20261007에 줄 없음) · '지금 있음'으로 나눠 sha256(코드) 작은 순으로 각 10 · 20개.
- 호출 상한 200(넘으면 멈춤 · 그 뒤 표본은 '미수행'으로 남김): corpCode.xml 1 · list.json(corp_code · 20190901 ~ 20200831 ·
  last_reprt_at=N · 100줄씩 · 그 기간 모든 쪽 · 덜 읽으면 '완전 아님') · document.xml(종목당 1 · 최대 30).
- 원문 고르기: 그 기간 손익구조 **최초 제출(제목에 '정정' 없음)** 가운데 접수일이 20200301에 가장 가까운 것.
- 대조 · 판정: quarter-data '(접수 해 − 1)-사업'과 비교 · verdict()가 사전등록 4절 기준으로 판정.
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


GONE = ["033270", "200230", "056080", "297890", "019210", "093050", "348950", "419530", "348150", "450140"]
NOW = ["006800", "004370", "010140", "105560", "005690", "028670", "002790", "086520", "003380", "003490",
       "000210", "005440", "108490", "090460", "006280", "030610", "079160", "328130", "026960", "161890"]


def sample():
    """사전등록 2절에 고정한 30개를 그대로 씀(CSV를 다시 훑은 값은 '일치 여부' 기록에만 씀 · 대체 실행 없음)."""
    return [(c, "gone") for c in GONE] + [(c, "now") for c in NOW]


def sample_from_csv():
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


WIN = ("20190901", "20200831")   # 피벗 20200301 둘레 1년 — 이 기간의 모든 쪽을 읽음


def listing(corp):
    """(목록, 상태, 완전 여부). total_page보다 덜 읽으면 완전 아님(절단)."""
    rows, page, total = [], 1, 1
    while page <= total:
        j = get("list.json", corp_code=corp, bgn_de=WIN[0], end_de=WIN[1], last_reprt_at="N", page_no=page, page_count=100).json()
        if j.get("status") == "013":
            return rows, "013", True
        if j.get("status") != "000":
            return rows, j.get("status"), False
        rows += j.get("list", [])
        total = int(j.get("total_page") or 1)
        page += 1
    return rows, "000", page > total


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


UNIT = {"원": 1, "천원": 10**3, "백만원": 10**6, "억원": 10**8}


def cells_of(row):
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
            for c in re.findall(r"<T[DEUH][^>]*>(.*?)</T[DEUH]>", row, flags=re.S | re.I)]


def parse(xml_text):
    """매출액 · 영업이익 · 당기순이익의 (당해, 직전) · 단위 · 재무제표 종류. 열 머리에서 '당해' · '직전' 열 자리를 찾아 씀.
    머리를 못 찾거나 숫자가 그 자리에 없으면 그 항목은 비움(0으로 채우지 않음)."""
    t = xml_text
    plain = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    unit = re.search(r"단위\s*[:：]\s*(원|천원|백만원|억원)", plain)
    kind = re.search(r"재무제표의\s*종류\s+(연결|별도|개별)", plain)
    rows = [cells_of(r) for r in re.findall(r"<TR[^>]*>(.*?)</TR>", t, flags=re.S | re.I)]
    cur = prev = None
    for cells in rows:
        j = " ".join(cells)
        if "당해" in j and "직전" in j:
            for k, c in enumerate(cells):
                c2 = c.replace(" ", "")
                if cur is None and c2.startswith("당해"):
                    cur = k
                if prev is None and c2.startswith("직전"):
                    prev = k
            break
    got, header_ok = {}, cur is not None and prev is not None and cur < prev
    for cells in rows:
        if not cells:
            continue
        head = cells[0].replace(" ", "").lstrip("-")
        key = ("매출" if head.startswith("매출액") else "영업이익" if head.startswith("영업이익") else
               "순이익" if head.startswith("당기순이익") else None)
        if not key or key in got or not header_ok:
            continue
        # 머리 줄의 '당해' · '직전' 칸 자리에 있는 값만 씀(그 자리가 숫자가 아니면 비움)
        if len(cells) > max(cur, prev):
            a_, b_ = cells[cur].replace(" ", ""), cells[prev].replace(" ", "")
            if NUM.fullmatch(a_) and NUM.fullmatch(b_):
                got[key] = [to_num(a_), to_num(b_)]
    m = (re.search(r"당해\s*사업\s*연도\D{0,30}?(20[0-9]{2})", plain)
         or re.search(r"(20[0-9]{2})\s*[.년]\s*0?1\s*[.월]\s*0?1\s*일?\s*~\s*(?:20[0-9]{2})\s*[.년]\s*12\s*[.월]\s*31", plain))
    return {"unit": unit.group(1) if unit else None, "kind": kind.group(1) if kind else None, "values": got,
            "header_ok": header_ok, "period_year": m.group(1) if m else None}


def body_xml(z):
    """ZIP 안 xml 가운데 '손익구조'가 든 것(여럿이면 가장 큰 것). 없으면 None."""
    best = None
    for f in z.infolist():
        if not f.filename.lower().endswith(".xml"):
            continue
        raw = z.read(f)
        enc = "euc-kr" if b"euc-kr" in raw[:300].lower() else "utf-8"
        text = raw.decode(enc, errors="replace")
        if "손익구조" in text and (best is None or len(raw) > len(best[0])):
            best = (raw, text)
    return best


def compare(code, rcept_dt, parsed):
    """quarter-data '(접수 해 − 1)-사업'과 대조. 기준: 연결 → CFS · 별도/개별 → OFS. 상대 차 ≤ 1% = 맞음 · 10^k배(k ≥ 1) 어긋남 = 단위 오류."""
    out = {"compare_year": None, "compare_basis": None, "compare_n": 0, "values": {}, "unit_error": 0, "match": 0, "mismatch": 0}
    f = ROOT / "quarter-data" / f"{code}.json"
    if not f.exists():
        out["why"] = "quarter-data 파일 없음"
        return out
    y = str(int(rcept_dt[:4]) - 1)
    out["compare_year"] = y
    out["period_year"] = parsed.get("period_year")
    out["period_error"] = int(parsed.get("period_year") is not None and parsed.get("period_year") != y)
    if parsed.get("period_year") is None:
        out["why"] = "공시 기간 못 뽑음(미확인)"
        return out
    if out["period_error"]:
        out["why"] = f"기간 다름(공시 {parsed.get('period_year')} / 비교 {y})"
        return out
    row = (json.loads(f.read_text()).get("rows") or {}).get(f"{y}-사업")
    if not row:
        out["why"] = "그해 사업보고서 값 없음"
        return out
    want = {"연결": "CFS", "별도": "OFS", "개별": "OFS"}.get(parsed.get("kind") or "")
    out["compare_basis"] = row.get("기준")
    if not want or row.get("기준") != want:
        out["why"] = f"기준 다름 · 못 견줌({parsed.get('kind')} / {row.get('기준')})"
        return out
    mul = UNIT.get(parsed.get("unit") or "")
    if not mul:
        out["why"] = "단위 없음"
        return out
    for k in ("매출", "영업이익", "순이익"):
        a = parsed["values"].get(k)
        b = row.get(k)
        if not a or b in (None, ""):
            continue
        a0, b0 = a[0] * mul, float(str(b).replace(",", ""))
        rel = abs(a0 - b0) / max(abs(b0), 1.0)
        unit_err = b0 != 0 and a0 != 0 and any(abs(abs(a0 / b0) - 10 ** e) / 10 ** e < 0.01 for e in (-6, -3, -1, 1, 3, 6))
        out["values"][k] = {"disclosed": a0, "report": b0, "relative_error": round(rel, 6), "unit_error": unit_err}
        out["compare_n"] += 1
        out["match"] += rel <= 0.01
        out["mismatch"] += rel > 0.01
        out["unit_error"] += unit_err
    return out


def verdict(items, stopped=None):
    """사전등록 4절 판정(분자 · 분모 · 사유)."""
    now = [i for i in items if i["group"] == "now"]
    gone = [i for i in items if i["group"] == "gone"]
    st = lambda xs, ok: [sum(1 for i in xs if ok(i)), len(xs)]
    steps = {"corp": st(now, lambda i: "corp_code" in i), "list_complete": st(now, lambda i: i.get("list_complete") is True),
             "doc": st(now, lambda i: "doc_sha256" in i), "parse": st(now, lambda i: i.get("status") == "숫자 뽑음")}
    comp = [i["compare"] for i in now if i.get("compare", {}).get("compare_n")]
    cn = sum(c["compare_n"] for c in comp)
    cm = sum(c["match"] for c in comp)
    ue = sum(c["unit_error"] for c in comp)
    gone_corp = st(gone, lambda i: "corp_code" in i)
    why = [f"{k} {a}/{b} < 90%" for k, (a, b) in steps.items() if b == 0 or a / b < 0.9]
    if len(comp) < 10:
        why.append(f"견줄 수 있는 종목 {len(comp)} < 10")
    if cn and cm / cn < 0.9:
        why.append(f"맞음 {cm}/{cn} < 90%")
    if ue:
        why.append(f"단위 오류 {ue}")
    if not gone_corp[1] or gone_corp[0] / gone_corp[1] < 0.5:
        why.append(f"gone 고유번호 {gone_corp[0]}/{gone_corp[1]} < 50%")
    pe = sum(i.get("compare", {}).get("period_error", 0) for i in now)
    if pe:
        why.append(f"기간 오류 {pe}")
    if stopped or any(str(i.get("status", "")).startswith("미수행") for i in items):
        why.append("호출 상한 · 멈춤으로 미수행 표본 있음")
    if len(now) != 20 or len(gone) != 10 or [i["code"] for i in items] != GONE + NOW:
        why.append("표본 수 · 명단이 고정 명단과 다름")
    return {"steps_now": steps, "compare_firms": len(comp), "compare_values": [cm, cn], "unit_errors": ue, "period_errors": pe,
            "gone_corp": gone_corp, "pass": not why, "why": why,
            "note": "gone 고유번호 회수율은 '과거 등장 · 지금 위 400 밖 코드' 범위의 값이고, 상장폐지 포괄성은 따로 NEEDS_DATA"}


def main():
    if not KEY:
        print("DART_CRTFC_KEY 없음")
        return 1
    smp = sample()
    csv_smp = sample_from_csv()
    out = {"sample_matches_csv": csv_smp == smp, "task": "ERN-0036", "stage": "feasibility", "started_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
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
            rows, st, complete = listing(corp)
            it["list_status"], it["list_n"], it["list_complete"] = st, len(rows), complete
            pl = [r for r in rows if "손익구조" in r.get("report_nm", "")]
            first = [r for r in pl if "정정" not in r.get("report_nm", "")]
            it["pl_n"], it["pl_first_n"], it["pl_correction_n"] = len(pl), len(first), len(pl) - len(first)
            if not first:
                it["status"] = "손익구조 최초 제출 없음(기간 안)"
                continue
            pick = min(first, key=lambda r: (abs(days(PIVOT, r["rcept_dt"])), r["rcept_dt"]))
            it.update(rcept_no=pick["rcept_no"], rcept_dt=pick["rcept_dt"], report_nm=pick["report_nm"])
            # 같은 회사 · ±60일 · 제목에 정정 — 같은 최초 공시의 정정이라고 입증하지 않음(근접 후보 · 미확인)
            it["correction_candidates_unverified"] = [r["rcept_no"] for r in pl if "정정" in r["report_nm"] and abs(days(pick["rcept_dt"], r["rcept_dt"])) <= 60]
            # 앞 60일 안 제목에 '잠정' — 같은 기간 · 숫자인지 맞추지 않음(선행 잠정 후보 · 결론 보류)
            it["prelim_candidates_60d_before"] = sum(1 for r in rows if "잠정" in r.get("report_nm", "") and 0 <= days(r["rcept_dt"], pick["rcept_dt"]) <= 60)
            r = get("document.xml", rcept_no=pick["rcept_no"])
            try:
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    best = body_xml(z)
            except (zipfile.BadZipFile, ValueError):
                it["status"] = "원문 받기 실패"
                continue
            if not best:
                it["status"] = "본문 xml 못 찾음"
                continue
            raw, text = best
            it["doc_sha256"] = hashlib.sha256(raw).hexdigest()
            it["parsed"] = parse(text)
            v = it["parsed"]["values"]
            ok = (all(k in v for k in ("매출", "영업이익", "순이익")) and it["parsed"]["unit"] and it["parsed"]["header_ok"]
                  and it["parsed"]["period_year"])
            it["status"] = "숫자 뽑음" if ok else "숫자 일부 · 단위 · 열 머리 · 기간 없음"
            if grp == "now":
                it["compare"] = compare(code, pick["rcept_dt"], it["parsed"])
    except RuntimeError as e:
        out["stopped"] = str(e)
    done = {i["code"] for i in out["items"]}
    if out.get("stopped") and out["items"]:
        out["items"][-1].setdefault("status", "미수행(상한 도달 중)")
    for code, grp in smp:
        if code not in done:
            out["items"].append({"code": code, "group": grp, "status": "미수행"})
    out["verdict"] = verdict(out["items"], out.get("stopped"))
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
