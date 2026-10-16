"""DART 사업보고서 원문을 통째로 보관하고 '주요 매출처 · 주요 고객' 문단을 뽑습니다(공개 자료 · MPOS H2 고객–공급사 연결).

판 2(GPT #444 고칠 것 반영):
- 원문 보존: 접수번호마다 받은 ZIP을 그대로 raw/<종목>/<접수번호>.zip에 두고, 저장 스크립트가 종목마다 묶어
  내용 지문 이름(raw-<종목>-<tar sha256 앞 16자>.tar)으로 릴리스에 올립니다(덮어쓰기 금지 · 같은 이름은 같은 내용만).
  어느 ZIP이 어느 묶음에 있는지는 customer-data/raw-assets.jsonl에 남깁니다.
- 줄 · 표 구조 보존: 문단 · 표 행은 줄로, 칸은 ' | '로 남기고 줄바꿈을 지우지 않습니다. 장 제목은 '§ '줄로 남깁니다.
- 저장소 문단은 낱말 줄 앞 2줄 · 뒤 15줄 · 한 줄 240자까지(전체는 릴리스 원문에서 다시 뽑을 수 있음).
- 뽑은 문단에는 ZIP 안 파일 이름 · 줄 번호(정규화 뒤 0부터 센 줄 · XML 원문 줄 아님 · colspan/rowspan · 당기/전기 열 대응은 아직 검증 안 함) · 가장 가까운 장 제목 · 풀이 판(PARSER)을 붙이고,
  버린 낱말 자리 수(가까움 · 감사 문단 · 개수 상한)도 셉니다. 문단 없음 ≠ 고객 없음.
- 호출 상한: 실제 요청 한 번마다(재시도 · 기업 목록 포함) 먼저 예산을 보고 세고 기록합니다.
- 거절 · 한도: HTTP 401/403 · DART 010/011/012/901 → 멈춤(키 문제). HTTP 429 · DART 020 → 기록 뒤 멈춤(다음에 이어 받기).
  ZIP · JSON · XML 응답을 모두 가려 읽습니다. 주소 · 키 · 응답 본문 · 예외 문장은 찍지 않습니다(종류 이름 · 상태 번호만).
- 목록: last_reprt_at=N(원본 + 정정 모두)을 밝혀 쓰고, 쪽 넘기기 영수증(total_count · total_page · 받은 쪽)을 남깁니다.
  [첨부정정] · [첨부추가]는 받지 않되 '제외 범위'로 기록합니다.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import requests

API = "https://opendart.fss.or.kr/api/"
OUT = Path("customer-data")
RAW = Path(os.getenv("CUSTOMER_RAW", "raw"))
PARSER = "c2"
KEYS = re.compile(r"주요\s?매출처|주요\s?고객|주요\s?거래처|주요\s?판매처|매출처\s?현황|외부\s?고객")
SKIP = re.compile(r"감사절차|감사인|핵심감사사항")
BUDGET = int(os.getenv("CUSTOMER_BUDGET", "7000"))
USED_FILE = os.getenv("CUSTOMER_USED_FILE", "")
SAVE_EVERY = int(os.getenv("CUSTOMER_SAVE_EVERY", "0"))
PAUSE = float(os.getenv("CUSTOMER_PAUSE", "0.6"))
DEADLINE = float(os.getenv("CUSTOMER_MINUTES", "0")) * 60
STARTED = time.time()
FIRST = "20170101"
NEAR, CAP, BEFORE, AFTER, WIDE = 4, 10, 2, 15, 240


class Stop(Exception):
    """멈춤: kind = 'budget' · 'limit' · 'auth'."""

    def __init__(self, kind, why):
        super().__init__(why)
        self.kind = kind


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
        """실제 요청마다 예산을 먼저 보고 셉니다. (HTTP 상태, 내용) 또는 (None, 예외 종류)."""
        last = "?"
        for turn in range(3):
            if self.used >= BUDGET:
                raise Stop("budget", "이번에 쓸 호출 수를 다 썼습니다.")
            if DEADLINE and time.time() - STARTED > DEADLINE:
                raise Stop("budget", "이번 실행 시간을 다 썼습니다.")
            time.sleep(PAUSE)
            self.used += 1
            self.keep()
            try:
                r = requests.get(API + endpoint, params={"crtfc_key": self.key, **params}, timeout=(10, timeout))
            except requests.RequestException as error:
                last = type(error).__name__
                time.sleep(3)
                continue
            if r.status_code in (401, 403):
                raise Stop("auth", f"HTTP {r.status_code}")
            if r.status_code == 429:
                raise Stop("limit", "HTTP 429")
            if r.status_code >= 500:
                last = f"HTTP {r.status_code}"
                time.sleep(3)
                continue
            return r.status_code, r.content
        return None, last


def dart_status(content):
    """ZIP이면 'zip', 아니면 JSON · XML의 status 값(없으면 '?')."""
    if content[:2] == b"PK":
        return "zip"
    try:
        return str(json.loads(content.decode("utf-8")).get("status", "?"))
    except (UnicodeDecodeError, ValueError, AttributeError):
        pass
    try:
        return (ElementTree.fromstring(content).findtext("status") or "?").strip()
    except ElementTree.ParseError:
        return "?"


def check(status):
    if status == "020":
        raise Stop("limit", "DART 020")
    if status in ("010", "011", "012", "901"):
        raise Stop("auth", f"DART {status}")


def corp_map(d):
    http, content = d.get("corpCode.xml", 120)
    if http is None:
        raise Stop("limit", "기업 목록 받기 실패 · " + content)
    status = dart_status(content)
    check(status)
    if status != "zip":
        raise Stop("limit", f"기업 목록 응답 {status}")
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        root = ElementTree.fromstring(z.read("CORPCODE.xml"))
    corps, names = {}, {}
    for n in root.findall("list"):
        code = (n.findtext("stock_code") or "").strip()
        if code:
            corps[code] = n.findtext("corp_code")
            names[code] = n.findtext("corp_name")
    return corps, names


def listing(d, corp, today):
    rows, receipt, page = [], {"pages": []}, 1
    while True:
        http, content = d.get("list.json", 30, corp_code=corp, bgn_de=FIRST, end_de=today, pblntf_detail_ty="A001",
                              last_reprt_at="N", page_no=page, page_count=100)
        if http is None:
            receipt["fail"] = content
            return None, receipt
        status = dart_status(content)
        check(status)
        if status == "013":
            if page == 1 and not rows:
                receipt.update(total_count=0, total_page=0, complete=True)
                return rows, receipt
            receipt["fail"] = f"{page}쪽 DART 013(앞쪽 {len(rows)}건 뒤 빈 쪽)"
            return None, receipt
        if status != "000":
            receipt["fail"] = f"DART {status}"
            return None, receipt
        data = json.loads(content.decode("utf-8"))
        receipt.update(total_count=data.get("total_count"), total_page=data.get("total_page"))
        receipt["pages"].append(page)
        rows += [{k: x.get(k) for k in ("rcept_no", "rcept_dt", "report_nm", "rm")} for x in data.get("list") or []]
        if page >= int(data.get("total_page") or 1):
            receipt["complete"] = len(rows) == int(data.get("total_count") or 0)
            if not receipt["complete"]:
                receipt["fail"] = f"건수 불일치 {len(rows)}/{data.get('total_count')}"
                return None, receipt
            return rows, receipt
        page += 1


def lines_of(raw):
    for enc in ("utf-8", "cp949"):
        try:
            s = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        s = raw.decode("utf-8", "ignore")
    s = s.replace("\r", "").replace("\n", " ")
    s = re.sub(r"<TITLE[^>]*>(.*?)</TITLE>", lambda m: "\n§ " + re.sub(r"<[^>]+>", " ", m.group(1)) + "\n", s,
               flags=re.I | re.S)
    s = re.sub(r"<(TD|TE|TH)\b[^>]*>", " | ", s, flags=re.I)
    s = re.sub(r"<(P|TR|BR|TABLE|/TABLE|SECTION-\d|/SECTION-\d)\b[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&cr;", "\n")
    out = []
    for line in s.split("\n"):
        line = re.sub(r"[ \t　]+", " ", line).strip()
        if line:
            out.append(line)
    return out


def passages(member, lines):
    found, drop = [], {"near": 0, "audit": 0, "cap": 0}
    title, last, total = "", -10**9, 0
    for i, line in enumerate(lines):
        if line.startswith("§ "):
            title = line[2:]
        if not KEYS.search(line):
            continue
        total += 1
        if i - last < NEAR:
            drop["near"] += 1
            continue
        if SKIP.search(" ".join(lines[max(0, i - 1): i + 1])):
            drop["audit"] += 1
            continue
        if len(found) >= CAP:
            drop["cap"] += 1
            continue
        last = i
        found.append({"member": member, "line": i, "title": title,
                      "lines": [x[:WIDE] for x in lines[max(0, i - BEFORE): i + AFTER]]})
    return found, total, drop


def kind_of(name):
    name = name or ""
    if "첨부" in name:
        return "첨부(제외)"
    return "정정" if "정정" in name else "원본"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(code):
    try:
        return json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"code": code, "filings": []}


def save(body):
    OUT.mkdir(exist_ok=True)
    body["filings"].sort(key=lambda f: (f["rcept_dt"], f["rcept_no"]))
    (OUT / f"{body['code']}.json").write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def codes():
    picked = [c.strip() for c in os.getenv("CUSTOMER_CODES", "").split(",") if c.strip()]
    if not picked:
        picked = sorted(p.stem for p in Path("dart-events").glob("*.json"))
    return [c for c in picked if re.fullmatch(r"[0-9]{6}", c)]


def fetch(d, code, r):
    """보고서 하나: 원문 ZIP 보관 + 문단 뽑기. 반환 = filing 기록."""
    filing = {**r, "kind": kind_of(r["report_nm"]), "parser": PARSER}
    if filing["kind"] == "첨부(제외)":
        filing["state"] = "제외 범위(받지 않음)"
        return filing
    http, content = d.get("document.xml", 120, rcept_no=r["rcept_no"])
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
    filing.update(zip_sha256=sha(content), zip_bytes=len(content), members=[], passages=[], hits=0,
                  drop={"near": 0, "audit": 0, "cap": 0})
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            for name in z.namelist():
                raw = z.read(name)
                lines = lines_of(raw)
                found, total, drop = passages(name, lines)
                filing["members"].append({"name": name, "sha256": sha(raw), "bytes": len(raw), "lines": len(lines)})
                filing["passages"] += found
                filing["hits"] += total
                for k in drop:
                    filing["drop"][k] += drop[k]
    except zipfile.BadZipFile:
        filing["state"] = "미해결 · ZIP 깨짐"
        return filing
    filing["state"] = "받음"
    return filing


class SaveFailed(Exception):
    pass


def commit(note):
    hook = os.getenv("CUSTOMER_SAVE_CMD", "")
    if not hook:
        return
    result = subprocess.run(["bash", "-c", hook], check=False)
    if result.returncode != 0:
        raise SaveFailed(f"저장 실패({note}) · 상태 {result.returncode}")


def report(state, **info):
    """실행 영수증: 끝 상태와 셈(키 · 주소 · 응답 본문 없음)."""
    OUT.mkdir(exist_ok=True)
    body = {"state": state, "parser": PARSER, "run": os.getenv("GITHUB_RUN_ID", "local"),
            "attempt": os.getenv("GITHUB_RUN_ATTEMPT", "1"), "at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            **info}
    (OUT / "_last_run.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    print("영수증 ·", json.dumps(body, ensure_ascii=False), flush=True)


def main():
    key = os.environ.get("DART_CRTFC_KEY", "").strip()
    if not key:
        print("DART 키가 없습니다.")
        return 1
    d = Dart(key)
    today = date.today().strftime("%Y%m%d")
    count = {"종목 끝": 0, "DART에 없음": 0, "목록 실패": 0, "새로 받음": 0, "자료 없음": 0, "제외": 0, "미해결": 0}
    body = None
    stop = None
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
            have = {f["rcept_no"] for f in body["filings"] if f.get("state") in ("받음", "제외 범위(받지 않음)")}
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
                    filing = fetch(d, code, r)
                    body["filings"] = [f for f in body["filings"] if f["rcept_no"] != r["rcept_no"]] + [filing]
                    new += 1
                    st = filing["state"]
                    count["새로 받음" if st == "받음" else "제외" if st.startswith("제외") else
                          "자료 없음" if st.startswith("자료 없음") else "미해결"] += 1
                save(body)
                body = None
                count["종목 끝"] += 1
                print(code, names.get(code), "보고서", len(rows), "· 새로", new, "· 호출", d.used, flush=True)
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
        code = 3 if stop.kind == "auth" else 2
    elif count["목록 실패"] or left:
        report("미해결 남음", used=d.used, 남은_미해결=left, **count)
        code = 4
    else:
        report("모두 받음", used=d.used, 남은_미해결=0, **count)
        code = 0
    try:
        commit("끝")
    except SaveFailed as why:
        report("저장 실패", why=str(why), 앞_상태=code, used=d.used, **count)
        return 5
    return code


if __name__ == "__main__":
    sys.exit(main())
