"""DART에서 과거까지 주는 자료를 더 모읍니다(새 RL 재료, 공개 자료만).

python collect_dart_extra.py events|holders|quarter
- events  → dart-events/{code}.json : 주요사항보고서(2017~) — 자기주식 취득·처분·신탁, 유상·무상·유무상증자, 전환사채 ·
            신주인수권부사채 · 교환사채, 감자, 타법인주식·영업·유형자산 양수도, 합병 · 분할, 부도 · 영업정지 · 회생, 소송.
- holders → holder-data/{code}.json : 임원·주요주주 소유보고 · 5% 대량보유 보고. (DART가 최근 약 2년치만 줌 — 과거 검증엔 못 씀)
- quarter → quarter-data/{code}.json: 분기마다(1분기 · 반기 · 3분기 · 사업보고서) 주요계정 — 매출 · 영업이익 · 순이익 · 자산 ·
            부채 · 자본(연결 먼저, 없으면 별도)과 접수번호(= 공시 날짜). 2016~.
대상은 study/flow_universe.json(+ 그날 A·B그룹). 받은 해·보고서는 다시 묻지 않고 올해 것만 새로 봅니다.
키는 환경변수 DART_CRTFC_KEY로만 받고, 응답 본문과 키는 찍지 않습니다. 하루 호출 한도(2만)를 넘지 않게 멈춥니다.
"""
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import requests

from collect_investor_history import codes_to_collect
from providers import DataError, Official

API = "https://opendart.fss.or.kr/api/"
PAUSE = float(os.getenv("DART_PAUSE", "0.08"))
# 하루 한도 2만을 세 가지가 나눠 씀(매일 도는 DART 작업 몫을 남김). 넘으면 멈추고 다음 날 이어 받음.
BUDGETS = {"events": 7000, "holders": 700, "quarter": 9000}
START = "20170101"
EVENTS = {
    "자기주식취득": "tsstkAqDecsn.json", "자기주식처분": "tsstkDpDecsn.json",
    "자기주식신탁체결": "tsstkAqTrctrCnsDecsn.json", "자기주식신탁해지": "tsstkAqTrctrCcDecsn.json",
    "유상증자": "piicDecsn.json", "무상증자": "fricDecsn.json", "유무상증자": "pifricDecsn.json",
    "전환사채": "cvbdIsDecsn.json", "신주인수권부사채": "bdwtIsDecsn.json", "교환사채": "exbdIsDecsn.json",
    "감자": "crDecsn.json", "타법인주식양수": "otcprStkInvscrInhDecsn.json", "타법인주식양도": "otcprStkInvscrTrfDecsn.json",
    "영업양수": "bsnInhDecsn.json", "영업양도": "bsnTrfDecsn.json", "유형자산양수": "tgastInhDecsn.json",
    "유형자산양도": "tgastTrfDecsn.json", "합병": "cmpMgDecsn.json", "분할": "cmpDvDecsn.json",
    "부도": "dfOcr.json", "영업정지": "bsnSp.json", "회생절차": "ctrcvsBgrq.json", "소송": "lwstLg.json",
}
REPORTS = {"11013": "1분기", "11012": "반기", "11014": "3분기", "11011": "사업"}
ACCOUNTS = {"매출액": "매출", "영업이익": "영업이익", "당기순이익": "순이익", "자산총계": "자산", "부채총계": "부채",
            "자본총계": "자본", "영업이익(손실)": "영업이익", "당기순이익(손실)": "순이익", "수익(매출액)": "매출"}


class Stop(Exception):
    pass


class Dart:
    def __init__(self, budget=5000):
        self.key = os.environ.get("DART_CRTFC_KEY", "").strip()
        self.used = 0
        self.budget = int(os.getenv("DART_BUDGET", budget))

    def ask(self, endpoint, **params):
        if self.used >= self.budget:
            raise Stop("오늘 쓸 호출 수를 다 썼습니다.")
        time.sleep(PAUSE)
        self.used += 1
        for turn in range(3):
            try:
                data = requests.get(API + endpoint, params={"crtfc_key": self.key, **params}, timeout=(10, 30)).json()
                break
            except (requests.RequestException, ValueError):
                if turn == 2:
                    return None
                time.sleep(3)
        status = str(data.get("status", ""))
        if status == "013":
            return []
        if status == "020":
            raise Stop("DART 호출 한도에 걸렸습니다(020).")
        if status in ("010", "011", "012", "901"):
            raise Stop(f"DART 키가 거절됐습니다({status}).")
        if status != "000":
            return None
        return data.get("list") or []


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(path, body):
    path = Path(path)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def events(d, corp, code, today):
    path = Path("dart-events") / f"{code}.json"
    body = load(path) or {"code": code, "rows": {}, "받은날": {}}
    for name, ep in EVENTS.items():
        since = body["받은날"].get(name, START)
        got = d.ask(ep, corp_code=corp, bgn_de=since, end_de=today)
        if got is None:
            continue
        old = {r.get("rcept_no"): r for r in body["rows"].get(name, [])}
        for r in got:
            r = {k: v for k, v in r.items() if k not in ("corp_name", "corp_code")}
            old[r.get("rcept_no")] = r
        body["rows"][name] = sorted(old.values(), key=lambda r: str(r.get("rcept_no")))
        body["받은날"][name] = today
    save(path, body)
    return sum(len(v) for v in body["rows"].values())


def holders(d, corp, code, today):
    body = {"code": code, "받은날": today, "주의": "DART는 최근 약 2년치만 줌"}
    for name, ep in (("임원주요주주", "elestock.json"), ("대량보유", "majorstock.json")):
        got = d.ask(ep, corp_code=corp)
        body[name] = [{k: v for k, v in r.items() if k not in ("corp_name", "corp_code")} for r in (got or [])]
    save(Path("holder-data") / f"{code}.json", body)
    return len(body["임원주요주주"]) + len(body["대량보유"])


def compact(rows):
    """주요계정 줄들 → 연결(CFS) 먼저, 없으면 별도(OFS)로 매출·영업이익·순이익·자산·부채·자본."""
    for basis in ("CFS", "OFS"):
        pick = [r for r in rows if r.get("fs_div") == basis]
        if not pick:
            continue
        got = {"기준": basis, "접수번호": pick[0].get("rcept_no"), "기간": pick[0].get("thstrm_dt") or pick[0].get("thstrm_nm")}
        for r in pick:
            name = ACCOUNTS.get(str(r.get("account_nm", "")).strip())
            if name and name not in got:
                got[name] = r.get("thstrm_amount")
                got[name + "_작년"] = r.get("frmtrm_amount")
        return got
    return None


def quarter(d, corp, code, today):
    path = Path("quarter-data") / f"{code}.json"
    body = load(path) or {"code": code, "rows": {}}
    this_year = int(today[:4])
    for year in range(2016, this_year + 1):
        for rc, label in REPORTS.items():
            key = f"{year}-{label}"
            if key in body["rows"] and year < this_year - 1:
                continue
            if key in body["rows"] and body["rows"][key]:
                continue
            got = d.ask("fnlttSinglAcnt.json", corp_code=corp, bsns_year=str(year), reprt_code=rc)
            if got is None:
                continue
            body["rows"][key] = compact(got)
    save(path, body)
    return sum(1 for v in body["rows"].values() if v)


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    jobs = {"events": events, "holders": holders, "quarter": quarter}
    if kind not in jobs:
        print("events · holders · quarter 가운데 하나를 주세요.")
        return 1
    d = Dart(BUDGETS[kind])
    if not d.key:
        print("DART 키가 없습니다.")
        return 1
    try:
        official = Official()
        official.corp("005930")
    except DataError as error:
        print("DART 기업 목록을 받지 못했습니다 ·", error)
        return 1
    today = date.today().strftime("%Y%m%d")
    done = missing = 0
    for code in codes_to_collect():
        corp = (official.corps or {}).get(code)
        if not corp:
            missing += 1
            continue
        try:
            n = jobs[kind](d, corp, code, today)
        except Stop as why:
            print(f"멈춤 · {why} · 받은 종목 {done} · 호출 {d.used}", flush=True)
            return 2
        done += 1
        print(f"{code} · {n} · 호출 누계 {d.used}", flush=True)
    print(f"끝 · {kind} · 받은 종목 {done} · DART에 없는 종목 {missing} · 호출 {d.used}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
