"""한국투자증권 장중(시간대별) 자료를 장이 끝난 뒤 그날 것만 모아 쌓기(1시간봉 RL 재료, 조회 전용).

2026-09-30 확인(probe_minute.py kis_intraday): 이 자료들은 **날짜를 넣어도 오늘(가장 최근 장) 것만** 줌 → 과거는 없고,
날마다 장이 끝난 뒤 받아 두어야 쌓임.
- 종목 투자자 추정(장중, HHPTJ04160200): 하루 다섯 번(장중 시간대 1~5)의 외국인 · 기관 추정 순매수 → intraday-data/estimate/{날}.json
- 프로그램매매 종합 시간별(FHPPG04600101, 코스피 · 코스닥): 분마다 차익 · 비차익 · 전체 순매수 · 지수 → intraday-data/program/{날}.json
  (한 번에 30줄 → 시각을 앞으로 옮겨 가며 09시까지)
장이 열린 날인지는 삼성전자 그날 1분봉이 오늘 날짜로 나오는지로 봄(휴일이면 아무것도 저장하지 않음).
키와 응답 본문은 찍지 않고 줄 수 · 종목 수만 찍음.
python collect_kis_intraday.py [종목코드,...]
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis

HOME = Path("intraday-data")
KST = ZoneInfo("Asia/Seoul")
Q = "/uapi/domestic-stock/v1/quotations/"
GAP = float(os.getenv("KIS_CALL_GAP", "0.07"))


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse_estimate(rows):
    """[[시간대, 외국인, 기관, 합], ...] — 시간대 순."""
    out = []
    for r in rows:
        gb = str(r.get("bsop_hour_gb", "")).strip()
        if not gb.isdigit():
            continue
        out.append([int(gb), num(r.get("frgn_fake_ntby_qty")), num(r.get("orgn_fake_ntby_qty")), num(r.get("sum_fake_ntby_qty"))])
    return sorted(out)


def parse_program(rows):
    """[[HHMMSS, 차익 순매수 대금, 비차익 순매수 대금, 전체 순매수 대금, 지수], ...]."""
    out = []
    for r in rows:
        t = str(r.get("bsop_hour", "")).strip()
        if len(t) != 6 or not t.isdigit():
            continue
        out.append([t, num(r.get("arbt_smtn_ntby_tr_pbmn")), num(r.get("nabt_smtn_ntby_tr_pbmn")),
                    num(r.get("whol_smtn_ntby_tr_pbmn")), num(r.get("bstp_nmix_prpr"))])
    return out


# 장 시간이 다른 날(사용자 2026-10-06 "남은것도 확인 후 수정"). 봇들(15분봉 · 1시간봉 · 1일봉 · 빈칸 엔진)은 09:00 ~ 15:30 시각표로만
# 판단해서, 이런 날 그대로 돌면 틀린 봉 · 틀린 시각으로 사고팖 → 그날은 자동 판단을 쉼(자료 수집은 그대로).
# 해마다 거래소 공지를 보고 더함(수능날: 10:00 ~ 16:30 · 새해 첫 거래일: 10:00 열림).
SPECIAL_HOURS = {
    "20261119": "수능날 · 10:00 ~ 16:30",
    "20270104": "새해 첫 거래일 · 10:00 열림",
}


def special_hours(day):
    return SPECIAL_HOURS.get(str(day))


def market_open_today(client, today, bots=True):
    """오늘 장이 열렸나. bots=True(봇이 물을 때)면 장 시간이 다른 날도 '쉼'으로 False."""
    why = special_hours(today) if bots else None
    if why:
        print(f"{today}은 장 시간이 다른 날({why})이라 봇 자동 판단 · 주문을 쉽니다(시각표가 09:00 ~ 15:30 기준).")
        return False
    rows = client._market_rows(Q + "inquire-time-dailychartprice", "FHKST03010230", {
        "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930", "FID_INPUT_HOUR_1": "153000",
        "FID_INPUT_DATE_1": today, "FID_PW_DATA_INCU_YN": "N", "FID_FAKE_TICK_INCU_YN": ""}, "분봉", key="output2")
    return any(str(r.get("stck_bsop_date", "")) == today for r in rows)


def program_day(client, market):
    """그날 분별 프로그램매매. 증권사는 시각 값을 무시하고 마지막 30줄(15:29~15:58)만 줌 · 다음 쪽 표시(tr_cont)가 오면 이어 받음(2026-09-30엔 오지 않음)."""
    got, cont = {}, ""
    for _ in range(40):
        raw, more = client._market_page(Q + "comp-program-trade-today", "FHPPG04600101", {
            "FID_COND_MRKT_DIV_CODE": "J", "FID_MRKT_CLS_CODE": market, "FID_SCTN_CLS_CODE": "", "FID_INPUT_ISCD": "",
            "FID_COND_MRKT_DIV_CODE1": "", "FID_INPUT_HOUR_1": ""}, "프로그램매매 종합", key="output", continuation=cont)
        rows = parse_program(raw)
        time.sleep(GAP)
        new = [r for r in rows if r[0] not in got]
        if not new:
            break
        for r in new:
            got[r[0]] = r
        if not more or min(r[0] for r in rows) <= "090000":
            break
        cont = "N"
    return [got[t] for t in sorted(got)]


def main(codes=None):
    now = datetime.now(KST)
    today = now.strftime("%Y%m%d")
    if now.hour * 100 + now.minute < 1540:
        print("장이 끝나기 전이라 받지 않습니다(15:40 뒤에 돌리세요).")
        return 0
    uni = json.loads(Path("hourly-data/universe.json").read_text(encoding="utf-8"))
    codes = codes or uni["codes"]
    try:
        client = broker_kis.market()
        if not market_open_today(client, today, bots=False):
            print(f"{today}은 장이 열리지 않은 날로 보여 저장하지 않습니다.")
            return 0
    except broker_kis.BrokerError as e:
        print("증권사 연결 · 확인 실패 ·", e)
        return 1
    fails = 0
    est = {}
    for code in codes:
        try:
            rows = client._market_rows(Q + "investor-trend-estimate", "HHPTJ04160200", {"MKSC_SHRN_ISCD": code},
                                       "투자자 추정", key="output2")
            got = parse_estimate(rows)
            if got:
                est[code] = got
        except broker_kis.BrokerError:
            fails += 1
            if fails >= 30:
                print("거절이 많아 멈춥니다.")
                break
        time.sleep(GAP)
    prog = {}
    for name, mk in (("코스피", "K"), ("코스닥", "Q")):
        try:
            prog[name] = program_day(client, mk)
        except broker_kis.BrokerError as e:
            print(f"{name} 프로그램매매 실패 ·", e)
    for sub, body in (("estimate", {"날": today, "rows": est}), ("program", {"날": today, **prog})):
        folder = HOME / sub
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{today}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    print(f"{today} · 투자자 추정 {len(est)}종목(거절 {fails}) · 프로그램 코스피 {len(prog.get('코스피', []))}줄 · 코스닥 {len(prog.get('코스닥', []))}줄")
    return 0


if __name__ == "__main__":
    picked = [c for c in (sys.argv[1].split(",") if len(sys.argv) > 1 else []) if c]
    sys.exit(main(picked or None))
