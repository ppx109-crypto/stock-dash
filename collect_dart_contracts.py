"""DART 단일판매 · 공급계약 공시 본문(계약금액 · 매출액 대비 % · 계약 기간 · 상대)을 모읍니다(공개 자료 · 조회 전용).

- 사용자 2026-10-16 "다트에서 활용하지 못한 정보" → 공급계약 본문 금액부터. 지금 event-data는 제목만 있어 계약 크기를 모름.
- 대상: customer-data/_scope.json의 437종목(고정 범위) · 거래소 공시(pblntf_ty=I) · 2015-01-01 ~ · 원본 · 정정 · 해지 모두.
  제목에 '공급계약' 또는 '수주'가 든 것만(collect_events.py의 '공급계약' 갈래와 같은 낱말).
- 원문 ZIP은 그대로 보관(raw/<종목>/<접수번호>.zip → 저장 스크립트가 내용 지문 이름으로 릴리스 dart-contracts-raw-v1에 올림).
- 본문에서 뽑는 칸(풀이 판 k1 · 원문이 있으니 나중에 다시 뽑을 수 있음): 계약금액 · 최근 매출액 · 매출액 대비 % · 계약 시작 · 종료 · 상대.
- 쓰는 시점: 접수일(rcept_dt) **다음 거래일부터**(접수 시각 없음).
- 호출 예산 · 오류 구분 · 영수증은 collect_dart_customers.py(GPT #444 판 3)의 부품을 그대로 씁니다.
"""
import json
import os
import re
import sys
import time
import zipfile
import io
from datetime import date
from pathlib import Path

from collect_dart_customers import Dart, Stop, SaveFailed, check, corp_map, dart_status, lines_of, sha, commit

OUT = Path("contract-data")
RAW = Path(os.getenv("CONTRACT_RAW", "raw"))
PARSER = "k1"
FIRST = "20150101"
MARKS = ("공급계약", "수주")
SAVE_EVERY = int(os.getenv("CUSTOMER_SAVE_EVERY", "0"))


def listing(d, corp, today):
    rows, receipt, page = [], {"pages": []}, 1
    while True:
        http, content = d.get("list.json", 30, corp_code=corp, bgn_de=FIRST, end_de=today, pblntf_ty="I",
                              last_reprt_at="N", page_no=page, page_count=100)
        if http is None:
            receipt["fail"] = content
            return None, receipt
        status = dart_status(content)
        check(status)
        if status == "013":
            if page == 1 and not rows:
                receipt.update(total_count=0, total_page=0, complete=True)
                return [], receipt
            receipt["fail"] = f"{page}쪽 DART 013"
            return None, receipt
        if status != "000":
            receipt["fail"] = f"DART {status}"
            return None, receipt
        data = json.loads(content.decode("utf-8"))
        receipt.update(total_count=data.get("total_count"), total_page=data.get("total_page"))
        receipt["pages"].append(page)
        rows += [{k: x.get(k) for k in ("rcept_no", "rcept_dt", "report_nm", "rm")} for x in data.get("list") or []]
        if page >= int(data.get("total_page") or 1):
            nos = [x["rcept_no"] for x in rows]
            if len(set(nos)) != len(nos):
                receipt["fail"] = "접수번호 중복"
                return None, receipt
            receipt["complete"] = len(rows) == int(data.get("total_count") or 0)
            if not receipt["complete"]:
                receipt["fail"] = f"건수 불일치 {len(rows)}/{data.get('total_count')}"
                return None, receipt
            receipt["all_I"] = len(rows)
            return [r for r in rows if any(m in re.sub(r"\s+", "", r["report_nm"] or "") for m in MARKS)], receipt
        page += 1


NUM = r"(-?[\d,]+(?:\.\d+)?)"


def grab(text, label):
    m = re.search(label + r"[^|\n]*\|\s*" + NUM, text)
    return m.group(1).replace(",", "") if m else None


def parse(lines):
    """표 줄(' | ' 칸)에서 칸 이름 뒤 첫 숫자를 뽑음. 못 찾으면 None(없음 ≠ 0)."""
    text = "\n".join(lines)
    out = {
        "계약금액": grab(text, r"계약금액"),
        "최근매출액": grab(text, r"최근\s*매출액"),
        "매출액대비%": grab(text, r"매출액\s*대비"),
    }
    m = re.search(r"시작일\s*\|\s*(\d{4}[-.]\d{2}[-.]\d{2})", text)
    out["시작일"] = m.group(1) if m else None
    m = re.search(r"종료일\s*\|\s*(\d{4}[-.]\d{2}[-.]\d{2})", text)
    out["종료일"] = m.group(1) if m else None
    m = re.search(r"계약상대(?:방)?\s*\|\s*([^|\n]{1,60})", text)
    out["상대"] = m.group(1).strip() if m else None
    return out


def kind_of(name):
    flat = re.sub(r"\s+", "", name or "")
    if "해지" in flat:
        return "해지"
    return "정정" if "정정" in flat else "원본"


def fetch(d, code, r):
    filing = {**r, "kind": kind_of(r["report_nm"]), "parser": PARSER}
    http, content = d.get("document.xml", 60, rcept_no=r["rcept_no"])
    if http is None:
        filing["state"] = "미해결 · 받기 실패 · " + content
        return filing
    status = dart_status(content)
    check(status)
    filing["http"] = http
    if status in ("013", "014"):
        filing["state"] = f"자료 없음 · DART {status}"
        return filing
    if status != "zip" or http != 200:
        filing["state"] = f"미해결 · HTTP {http} · DART {status}"
        return filing
    folder = RAW / code
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{r['rcept_no']}.zip").write_bytes(content)
    filing.update(zip_sha256=sha(content), zip_bytes=len(content), members=[])
    lines = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            for name in z.namelist():
                raw = z.read(name)
                ls = lines_of(raw)
                filing["members"].append({"name": name, "sha256": sha(raw), "bytes": len(raw), "lines": len(ls)})
                lines += ls
    except zipfile.BadZipFile:
        filing["state"] = "미해결 · ZIP 깨짐"
        return filing
    filing["fields"] = parse(lines)
    filing["state"] = "받음"
    return filing


def load(code):
    try:
        return json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"code": code, "filings": []}


def save(body):
    OUT.mkdir(exist_ok=True)
    body["filings"].sort(key=lambda f: (f["rcept_dt"], f["rcept_no"]))
    (OUT / f"{body['code']}.json").write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def report(state, **info):
    OUT.mkdir(exist_ok=True)
    body = {"state": state, "parser": PARSER, "run": os.getenv("GITHUB_RUN_ID", "local"),
            "attempt": os.getenv("GITHUB_RUN_ATTEMPT", "1"), "at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), **info}
    (OUT / "_last_run.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    print("영수증 ·", json.dumps(body, ensure_ascii=False), flush=True)


def codes():
    picked = [c.strip() for c in os.getenv("CONTRACT_CODES", "").split(",") if c.strip()]
    if not picked:
        picked = json.loads(Path("customer-data/_scope.json").read_text(encoding="utf-8"))["codes"]
    return [c for c in picked if re.fullmatch(r"[0-9]{6}", c)]


def main():
    key = os.environ.get("DART_CRTFC_KEY", "").strip()
    if not key:
        print("DART 키가 없습니다.")
        return 1
    d = Dart(key)
    today = date.today().strftime("%Y%m%d")
    count = {"종목 끝": 0, "DART에 없음": 0, "목록 실패": 0, "새로 받음": 0, "자료 없음": 0, "미해결": 0}
    body, stop = None, None
    try:
        corps, names = corp_map(d)
        for n, code in enumerate(codes(), 1):
            corp = corps.get(code)
            body = load(code)
            if not corp:
                body["why"] = "DART에 없음"
                count["DART에 없음"] += 1
                save(body)
                body = None
                continue
            have = {f["rcept_no"] for f in body["filings"] if f.get("state") == "받음"}
            rows, receipt = listing(d, corp, today)
            body["name"] = names.get(code)
            body["list_receipt"] = {**receipt, "checked": today}
            if rows is None:
                count["목록 실패"] += 1
                save(body)
                body = None
                print(code, "목록 실패 ·", receipt.get("fail"), flush=True)
            else:
                body["listed_reports"] = rows
                new = 0
                for r in sorted(rows, key=lambda x: (x["rcept_dt"], x["rcept_no"])):
                    if r["rcept_no"] in have:
                        continue
                    f = fetch(d, code, r)
                    body["filings"] = [x for x in body["filings"] if x["rcept_no"] != r["rcept_no"]] + [f]
                    new += 1
                    st = f["state"]
                    count["새로 받음" if st == "받음" else "자료 없음" if st.startswith("자료 없음") else "미해결"] += 1
                save(body)
                body = None
                count["종목 끝"] += 1
                print(code, names.get(code), "공급계약", len(rows), "· 새로", new, "· 호출", d.used, flush=True)
            if SAVE_EVERY and n % SAVE_EVERY == 0:
                commit(f"{n}종목")
    except Stop as why:
        stop = why
        if body is not None:
            save(body)
    except SaveFailed as why:
        d.keep()
        report("저장 실패", why=str(why), used=d.used, **count)
        return 5
    d.keep()
    left = sum(1 for p in OUT.glob("[0-9]*.json")
               for f in json.loads(p.read_text(encoding="utf-8")).get("filings", []) if f.get("state", "").startswith("미해결"))
    if stop is not None:
        state = "멈춤 · 키 문제" if stop.kind == "auth" else "부분 수집 · " + ("호출 예산" if stop.kind == "budget" else "한도")
        report(state, why=str(stop), used=d.used, 남은_미해결=left, **count)
        rc = 3 if stop.kind == "auth" else 2
    elif count["목록 실패"] or left:
        report("미해결 남음", used=d.used, 남은_미해결=left, **count)
        rc = 4
    else:
        report("모두 받음", used=d.used, 남은_미해결=0, **count)
        rc = 0
    try:
        commit("끝")
    except SaveFailed as why:
        report("저장 실패", why=str(why), 앞_상태=rc, used=d.used, **count)
        return 5
    return rc


if __name__ == "__main__":
    sys.exit(main())
