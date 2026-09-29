"""한국투자증권 1분봉을 모아 1시간봉 만들기(1시간봉 RL 재료, 조회 전용).

주식일별분봉조회(FHKST03010230)는 **약 1년 전까지** 1분봉을 줍니다(2026-09 확인: 2025-09-17까지). 한 번에 120분이라
하루(09:00~15:30)를 네 번(15:30 · 13:30 · 11:30 · 09:30 끝) 물어 모읍니다. 야후 60분봉과 달리 **마감 동시호가(15:30)까지** 들어 있어
하루 마지막 값이 일봉 종가와 같습니다.

저장: hourly-kis/{종목코드}/{해}.csv — "YYYYMMDDHH,시가,고가,저가,종가,거래량"(HH = 그 시간대가 시작한 시, 09~15 · 15시 봉 = 15:00~15:30).
받은 날은 건너뛰고 빈 날만 묻습니다(끊겨도 이어 받음). 장이 끝난 날만(16시 전이면 오늘은 안 물음).
python collect_kis_hourly.py [종목코드,...]   · 환경변수 KIS_HOURLY_MAX_CALLS(한 번에 부를 최대 수, 기본 40000)
"""
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis
from collect_hourly import merge

HOME = Path("hourly-kis")
PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
ENDS = ("153000", "133000", "113000", "093000")
START = os.getenv("KIS_HOURLY_START", "20250917")
LANES = int(os.getenv("KIS_HOURLY_LANES", "4"))
MAX_CALLS = int(os.getenv("KIS_HOURLY_MAX_CALLS", "40000"))
KST = ZoneInfo("Asia/Seoul")


def bucket(hhmmss):
    """1분봉 시각(그 분이 끝난 시각, 예: 090100 = 09:00~09:01)을 시작 시로. 09:01~10:00 → 9, 15:21~15:30 → 15."""
    h, m = int(hhmmss[:2]), int(hhmmss[2:4])
    total = h * 60 + m - 1
    return total // 60


def to_hours(rows, day):
    """그날 1분봉 줄들 → [(YYYYMMDDHH, o, h, l, c, v)] (시각 순)."""
    mins = []
    for r in rows:
        if str(r.get("stck_bsop_date", "")) != day:
            continue
        t = str(r.get("stck_cntg_hour", ""))
        try:
            o, hi, lo, c = (float(r[k]) for k in ("stck_oprc", "stck_hgpr", "stck_lwpr", "stck_prpr"))
            v = float(r.get("cntg_vol") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if len(t) != 6 or min(o, hi, lo, c) <= 0:
            continue
        mins.append((t, o, hi, lo, c, v))
    mins = sorted(set(mins))
    by = {}
    for t, o, hi, lo, c, v in mins:
        hh = bucket(t)
        if not 9 <= hh <= 15:
            continue
        if hh not in by:
            by[hh] = [o, hi, lo, c, v]
        else:
            x = by[hh]
            x[1] = max(x[1], hi); x[2] = min(x[2], lo); x[3] = c; x[4] += v
    return [(f"{day}{hh:02d}", *[round(x, 2) for x in by[hh][:4]], int(by[hh][4])) for hh in sorted(by)]


def have_days(code):
    folder = HOME / code
    got = set()
    for f in folder.glob("*.csv"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line[:8].isdigit():
                got.add(line[:8])
    return got


def trading_days(today):
    rows = json.loads(Path("price-data/005930.json").read_text(encoding="utf-8"))["closes"]
    return [d for d, _ in rows if START <= d < today]


def fetch_day(client, code, day):
    rows = []
    for end in ENDS:
        rows += broker_kis_rows(client, code, day, end)
    return to_hours(rows, day)


def broker_kis_rows(client, code, day, end):
    return client._market_rows(PATH, "FHKST03010230", {
        "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_HOUR_1": end,
        "FID_INPUT_DATE_1": day, "FID_PW_DATA_INCU_YN": "N", "FID_FAKE_TICK_INCU_YN": ""}, "분봉", key="output2")


def main(codes=None):
    now = datetime.now(KST)
    today = now.strftime("%Y%m%d")
    # 장이 끝난 날만: 16시 뒤면 오늘까지, 그 전이면 어제까지(일봉 표에 오늘이 아직 없으면 오늘은 자연히 빠짐)
    uni = json.loads(Path("hourly-data/universe.json").read_text(encoding="utf-8"))
    codes = codes or (uni["top100"] + [c for c in uni["codes"] if c not in uni["top100"]])
    days = [d for d in trading_days("99999999") if d < today or (d == today and now.hour >= 16)]
    try:
        client = broker_kis.market()
    except broker_kis.BrokerError as e:
        print("증권사 연결을 만들지 못했습니다 ·", e)
        return 1
    calls = [0]
    lock = threading.Lock()
    fails = [0]

    def one(code, day):
        with lock:
            if calls[0] + len(ENDS) > MAX_CALLS or fails[0] >= 30:
                return code, day, None
            calls[0] += len(ENDS)
        try:
            bars = fetch_day(client, code, day)
            with lock:
                fails[0] = 0
            return code, day, bars
        except broker_kis.BrokerError:
            with lock:
                fails[0] += 1
            return code, day, None

    done_codes = 0
    for code in codes:
        need = [d for d in days if d not in have_days(code)]
        if not need:
            done_codes += 1
            continue
        got = []
        with ThreadPoolExecutor(LANES) as pool:
            for fut in as_completed([pool.submit(one, code, d) for d in need]):
                _, day, bars = fut.result()
                if bars:
                    got += bars
        if got:
            merge(HOME / code, got)
        print(f"  {code} · 빈 날 {len(need)} · 받은 봉 {len(got)} · 부른 수 {calls[0]}", flush=True)
        if calls[0] + len(ENDS) > MAX_CALLS:
            print("이번 몫을 다 불렀습니다(다음에 이어 받음).", flush=True)
            return 3
        if fails[0] >= 30:
            print("거절이 이어져 멈춥니다.", flush=True)
            return 2
        done_codes += 1
    print(f"끝 · 다 받은 종목 {done_codes}/{len(codes)} · 부른 수 {calls[0]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1].split(",") if len(sys.argv) > 1 else None))
