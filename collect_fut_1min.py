"""선물 1분봉 모으기 — 미니 코스피200 · 코스피200 · 코스닥150 선물(한국투자증권 조회 전용).

사용자 2026-10-13 "16시에 미니코스피 선물, 코스피선물, 코스닥 선물 1m자료를 전부 다운로드해주고
(내가 전달해줬던 파일처럼)". 키움에서 받은 파일(kiwoom-data/kospi200_futures_1min.csv)과 같은 모양으로
상품마다 한 파일에 날마다 덧붙입니다: datetime,code,open,high,low,close,volume

- 근월물: 만기일(둘째 목요일) 당일부터는 다음 월물(사용자 파일이 10-08 · 09-10 · 08-13에 이렇게 바뀜).
- 종목 목록은 한투 공개 마스터 파일(fo_idx_code_mts)에서 읽습니다.
- 응답 본문은 찍지 않습니다. 줄 수 · 시각 범위 · 칸 이름만 찍습니다.

python collect_fut_1min.py probe          # 종목 목록 · 분봉 한 번씩 찔러 보기(저장 없음)
python collect_fut_1min.py collect [날짜]  # 그날 1분봉을 futures-1m/에 덧붙임(날짜 없으면 오늘)
"""
import csv
import io
import os
import re
import sys
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "futures-1m"
MASTER_URL = "https://new.real.download.dws.co.kr/common/master/fo_idx_code_mts.mst.zip"
PATH = "/uapi/domestic-futureoption/v1/quotations/inquire-time-fuopchartprice"
TR = "FHKIF03020200"
HEAD = ["datetime", "code", "open", "high", "low", "close", "volume"]
# 상품 → (파일 이름, 키움식 코드 앞 세 자리, 분기물만인지)
PRODUCTS = {
    "mini_kospi200": ("mini_kospi200_futures_1min.csv", "A05", False),
    "kospi200": ("kospi200_futures_1min.csv", "A01", True),
    "kosdaq150": ("kosdaq150_futures_1min.csv", "A06", True),
}
MONTH_CH = "123456789ABC"


def second_thursday(y, m):
    d = date(y, m, 1)
    d += timedelta(days=(3 - d.weekday()) % 7)
    return d + timedelta(days=7)


def contract_month(code):
    """키움식 8자리 코드(A056B000)에서 (연, 월). 아니면 None."""
    m = re.fullmatch(r"A0[0-9]{2}([0-9])([1-9ABC])000", code or "")
    if not m:
        return None
    y = 2020 + int(m.group(1))
    if y < 2024:
        y += 10
    return y, MONTH_CH.index(m.group(2)) + 1


def kiwoom_code(prefix, y, m):
    return f"{prefix}{y % 10}{MONTH_CH[m - 1]}000"


def front_code(prefix, day, quarterly):
    """그날 근월물 키움식 코드. 만기일 당일부터는 다음 월물."""
    y, m = day.year, day.month
    for _ in range(15):
        if (not quarterly or m % 3 == 0) and second_thursday(y, m) > day:
            return kiwoom_code(prefix, y, m)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    raise ValueError("근월물을 찾지 못함")


def master_rows():
    import requests
    r = requests.get(MASTER_URL, timeout=30)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    text = z.read(z.namelist()[0]).decode("cp949", errors="replace")
    return [line.split("|") for line in text.splitlines() if line.strip()]


def kis_code(rows, kcode):
    """마스터 파일에서 키움식 코드(A056B000)에 맞는 한투 단축코드(A05611)를 찾음 — 표준코드 KR4A056B0006의 'A056B'로 맞춤."""
    for row in rows:
        cells = [c.strip() for c in row[:3]]
        if len(cells) == 3 and cells[2][3:8] == kcode[:5]:
            return cells[1]
    return None


def _ask(client, code, ymd, hour):
    return client._market_rows(PATH, TR, {
        "FID_COND_MRKT_DIV_CODE": "F", "FID_INPUT_ISCD": code, "FID_HOUR_CLS_CODE": "60",
        "FID_PW_DATA_INCU_YN": "Y", "FID_FAKE_TICK_INCU_YN": "N",
        "FID_INPUT_DATE_1": ymd, "FID_INPUT_HOUR_1": hour}, "선물 분봉", key="output2")


def _take(rows, ymd, got):
    """그날 · 처음 보는 분만 got에 넣고 (넣은 수, 받은 첫 시각, 끝 시각)."""
    fresh, seen = 0, []
    for r in rows:
        d, t = str(r.get("stck_bsop_date", "")).strip(), str(r.get("stck_cntg_hour", "")).strip()
        if d != ymd or not re.fullmatch(r"[0-9]{6}", t):
            continue
        seen.append(t)
        if (d, t) not in got:
            got[(d, t)] = r
            fresh += 1
    return fresh, (min(seen) if seen else None), (max(seen) if seen else None)


def _mins(t):
    return int(t[:2]) * 60 + int(t[2:4])


def gaps(times):
    """빈 곳 [(앞 분 HHMMSS, 뒤 분 HHMMSS, 빈 분 수)] — 15:35 ~ 15:44 단일가 시간은 원래 비므로 뺌."""
    out = []
    for a, b in zip(times, times[1:]):
        n = _mins(b) - _mins(a) - 1
        if n > 0 and not (_mins(a) >= 15 * 60 + 34 and _mins(b) <= 15 * 60 + 45):
            out.append((a, b, n))
    return out


def fetch_day(client, code, day, log=print):
    """그날 1분봉(오래된 것부터). 한 번에 백여 줄씩 뒤로 넘기며 받음.
    2026-10-15: 코스피200 선물 두 개만 12:39 ~ 13:07 29분이 빈 채 저장됨(쪽 넘김 중 한 쪽이 빔) →
    쪽마다 받은 시각을 남기고(줄 수 · 시각만), 받은 뒤 빈 곳이 있으면 빈 곳 끝 시각부터 다시 요청해 채움(최대 3번)."""
    ymd = day.strftime("%Y%m%d")
    got = {}
    hour = "160000"
    pages = []
    for _ in range(12):
        fresh, lo, hi = _take(_ask(client, code, ymd, hour), ymd, got)
        pages.append(f"{hour[:4]}→{lo and lo[:4]}~{hi and hi[:4]}({fresh})")
        if not fresh:
            break
        earliest = min(t for (d, t) in got)
        if earliest <= "084500":
            break
        hh = datetime.strptime(earliest, "%H%M%S") - timedelta(minutes=1)
        hour = hh.strftime("%H%M%S")
    log(f"   {code} {ymd} 쪽: " + " · ".join(pages))
    for _ in range(3):
        holes = gaps(sorted(t for (d, t) in got))
        if not holes:
            break
        added = 0
        for a, b, n in holes:
            ask = (datetime.strptime(b, "%H%M%S") - timedelta(minutes=1)).strftime("%H%M%S")
            fresh, lo, hi = _take(_ask(client, code, ymd, ask), ymd, got)
            added += fresh
            log(f"   {code} {ymd} 빈 곳 {a[:4]}~{b[:4]}({n}분) 다시 요청 {ask[:4]} → {lo and lo[:4]}~{hi and hi[:4]} 새로 {fresh}줄")
        if not added:
            break
    left = gaps(sorted(t for (d, t) in got))
    if left:
        log(f"   {code} {ymd} ⚠️ 남은 빈 곳: " + ", ".join(f"{a[:4]}~{b[:4]}({n}분)" for a, b, n in left))
    return [got[k] for k in sorted(got)]


def to_line(r, kcode):
    d, t = r["stck_bsop_date"], r["stck_cntg_hour"]
    num = lambda k: str(float(r[k])).rstrip("0").rstrip(".") if r.get(k) not in (None, "") else ""
    return [f"{d[:4]}-{d[4:6]}-{d[6:]} {t[:2]}:{t[2:4]}:{t[4:]}", kcode,
            num("futs_oprc"), num("futs_hgpr"), num("futs_lwpr"), num("futs_prpr"), str(int(float(r.get("cntg_vol") or 0)))]


def append(path, lines):
    """같은 날 줄이 이미 있으면 그날 것을 바꿔 씀(다시 돌려도 겹치지 않게)."""
    days = {l[0][:10] for l in lines}
    old = []
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as f:
            old = [r for r in csv.reader(f)][1:]
    keep = [r for r in old if r and r[0][:10] not in days]
    allr = sorted(keep + lines, key=lambda r: r[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEAD)
        w.writerows(allr)
    return len(allr)


def probe():
    from broker_kis import market
    rows = master_rows()
    kinds = {}
    for r in rows:
        kinds[r[0].strip()] = kinds.get(r[0].strip(), 0) + 1
    print("마스터 줄 수", len(rows), "· 칸 수", sorted({len(r) for r in rows}), "· 상품종류별", kinds)
    shown = 0
    for r in rows:
        name = r[3] if len(r) > 3 else ""
        if r[0].strip() in ("1", "3", "B") and shown < 40:
            print("  선물줄", [c.strip() for c in r])
            shown += 1
    today = datetime.now(KST).date()
    client = market()
    for prod, (_, prefix, quarterly) in PRODUCTS.items():
        kcode = front_code(prefix, today, quarterly)
        code = kis_code(rows, kcode)
        print(prod, "키움식", kcode, "→ 한투", code)
        for c in [x for x in (code,) if x]:
            for day in (today, today - timedelta(days=1)):
                try:
                    got = fetch_day(client, c, day)
                except Exception as e:
                    print("   ", c, day, "실패", type(e).__name__, str(e)[:80])
                    continue
                span = (got[0]["stck_cntg_hour"], got[-1]["stck_cntg_hour"]) if got else None
                print("   ", c, day, "줄", len(got), "시각", span, "칸", sorted(got[0].keys()) if got else [])


def collect(day):
    from broker_kis import market
    rows = master_rows()
    client = market()
    bad = 0
    for prod, (fname, prefix, quarterly) in PRODUCTS.items():
        kcode = front_code(prefix, day, quarterly)
        code = kis_code(rows, kcode) or kcode
        got = fetch_day(client, code, day)
        if not got:
            print(prod, kcode, day, "자료 없음(휴일이거나 아직 안 나옴) — 저장 안 함")
            bad += 1
            continue
        n = append(OUT / fname, [to_line(r, kcode) for r in got])
        print(prod, kcode, day, "줄", len(got), got[0]["stck_cntg_hour"], "~", got[-1]["stck_cntg_hour"], "· 파일 전체", n)
    return 0 if bad < len(PRODUCTS) else 3


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    mode = sys.argv[1] if len(sys.argv) > 1 else "collect"
    if mode == "probe":
        probe()
    else:
        d = datetime.strptime(sys.argv[2], "%Y%m%d").date() if len(sys.argv) > 2 else datetime.now(KST).date()
        sys.exit(collect(d))
