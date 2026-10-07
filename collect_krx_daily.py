"""KRX 공식 Open API로 날짜마다 **그날 상장돼 있던 모든 종목**(뒤에 상장폐지된 종목 포함)의 일별 매매정보를 모읍니다.

까닭(2차 연구 · docs/PREREG-2.md): 연구 종목은 지금 살아 있는 종목뿐이라 생존자 편향이 있음. 한투는 상장폐지 종목 일봉을 주지 않고,
data.krx.co.kr은 로그인을 요구함. KRX Open API(인증키 · 서비스별 이용 신청)는 날짜 하나를 물으면 그날 전 종목을 줌.
저장: krx-data/YYYY.csv.gz — 한 줄 = 날짜 · 시장 · 종목코드 · 이름 · 종가 · 거래량 · 거래대금 · 시가총액 · 상장주식수 (원주가 · 그날 값 그대로).
이어 받기: 이미 있는 날은 건너뜀 · 한 번에 MAX_DAYS 날까지(제한 시간 · 하루 호출 한도 보호).
키: 환경 변수 KRX_AUTH_KEY(GitHub Secrets). 키 · 응답 본문은 찍지 않음(줄 수만).
python collect_krx_daily.py [시작일 YYYYMMDD]
"""
from __future__ import annotations

import csv
import gzip
import io
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

BASE = "https://data-dbg.krx.co.kr/svc/apis"
MARKETS = {"KOSPI": "sto/stk_bydd_trd", "KOSDAQ": "sto/ksq_bydd_trd"}
HOME = Path("krx-data")
COLS = ["date", "market", "code", "name", "close", "volume", "value", "mktcap", "shares"]
MAX_DAYS = int(os.getenv("KRX_MAX_DAYS", "400"))


def ask(path, day, key):
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{path}", headers={"AUTH_KEY": key}, params={"basDd": day}, timeout=(10, 60))
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            try:
                rows = r.json().get("OutBlock_1")
            except ValueError:
                return None
            return rows if isinstance(rows, list) else []
        if r.status_code in (401, 403):
            print(f"HTTP {r.status_code} — 키 또는 서비스 이용 신청을 확인하세요.")
            sys.exit(2)
        time.sleep(2 ** attempt)
    return None


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def row_of(day, market, r):
    code = str(r.get("ISU_SRT_CD") or r.get("ISU_CD") or "").strip()
    if len(code) == 12 and code.startswith("KR"):
        code = code[3:9]
    return [day, market, code.zfill(6), r.get("ISU_NM", ""), num(r.get("TDD_CLSPRC")), num(r.get("ACC_TRDVOL")),
            num(r.get("ACC_TRDVAL")), num(r.get("MKTCAP")), num(r.get("LIST_SHRS"))]


def load_year(y):
    p = HOME / f"{y}.csv.gz"
    if not p.exists():
        return []
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return list(csv.reader(fh))[1:]


def save_year(y, rows):
    HOME.mkdir(exist_ok=True)
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLS)
    w.writerows(rows)
    with gzip.open(HOME / f"{y}.csv.gz", "wt", encoding="utf-8") as fh:
        fh.write(buf.getvalue())


def main():
    key = os.environ.get("KRX_AUTH_KEY", "").strip()
    if not key:
        print("KRX_AUTH_KEY가 없습니다. GitHub 저장소 Settings → Secrets → Actions에 넣어 주세요.")
        return 1
    start = sys.argv[1] if len(sys.argv) > 1 else "20160104"
    d, end = date(int(start[:4]), int(start[4:6]), int(start[6:])), date.today()
    years, done, asked = {}, {}, 0
    while d <= end and asked < MAX_DAYS:
        if d.weekday() < 5:
            y, day = d.year, d.strftime("%Y%m%d")
            if y not in years:
                years[y] = load_year(y)
                done[y] = {r[0] for r in years[y]}
            if day not in done[y]:
                got, ok = [], True
                for market, path in MARKETS.items():
                    rows = ask(path, day, key)
                    if rows is None:
                        ok = False
                        break
                    got += [row_of(day, market, r) for r in rows]
                    time.sleep(0.15)
                asked += 1
                if ok and got:
                    years[y] += got
                    done[y].add(day)
                    print(f"{day}: {len(got)}종목", flush=True)
                elif ok:
                    done[y].add(day)          # 쉬는 날(빈 응답)
                if asked % 40 == 0:
                    save_year(y, years[y])
        d += timedelta(days=1)
    for y, rows in years.items():
        if rows:
            save_year(y, rows)
    print(f"끝 · 물은 날 {asked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
