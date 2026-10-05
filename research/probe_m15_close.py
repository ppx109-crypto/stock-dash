"""10-02 15분봉 마지막 값이 장 마감 단일가(15:30)를 빠뜨린 까닭 찾기(사용자 2026-10-06 "원인파악하고 다시는 이런일 없도록").

주식일별분봉조회(FHKST03010230)를 여러 조건으로 물어 15:17 뒤 1분봉의 시각 · 값 · 거래량만 찍습니다(응답 본문 · 키는 찍지 않음).
견줌: 10-01(맞던 날) vs 10-02(틀린 날), 주식 vs ETF(069500 · 10-02도 맞았음). 조회 전용 · 저장하지 않음.
python research/probe_m15_close.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import broker_kis  # noqa: E402

PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
CODES = os.getenv("PROBE_CODES", "000250,000080,005930,000270,069500").split(",")
DAYS = os.getenv("PROBE_DAYS", "20261001,20261002").split(",")
TRIES = (("153000", "N"), ("153000", "Y"), ("160000", "N"), ("153100", "N"))


def rows(client, code, day, end, past):
    got = client._market_rows(PATH, "FHKST03010230", {
        "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_HOUR_1": end,
        "FID_INPUT_DATE_1": day, "FID_PW_DATA_INCU_YN": past, "FID_FAKE_TICK_INCU_YN": ""}, "분봉", key="output2")
    out = []
    for r in got:
        if str(r.get("stck_bsop_date", "")) != day:
            continue
        t = str(r.get("stck_cntg_hour", ""))
        if t >= "151700":
            out.append((t, r.get("stck_prpr"), r.get("cntg_vol")))
    return sorted(set(out))


def outside(code, days):
    """한투가 아닌 출처(네이버 일봉 · 야후 일봉)의 종가 — 어느 쪽이 진짜 종가인지 가리기용."""
    import re
    import requests
    got = {}
    try:
        txt = requests.get("https://fchart.stock.naver.com/sise.nhn", params={
            "symbol": code, "timeframe": "day", "count": 10, "requestType": 0}, timeout=15).text
        for d, c in re.findall(r'data="(\d{8})\|[^|]*\|[^|]*\|[^|]*\|([^|]*)\|', txt):
            if d in days:
                got[f"네이버 {d}"] = c
    except Exception as e:  # noqa: BLE001
        got["네이버"] = f"못 받음 {type(e).__name__}"
    for sfx in (".KS", ".KQ"):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{code}{sfx}",
                             params={"range": "1mo", "interval": "1d"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).json()
            res = (r.get("chart") or {}).get("result") or []
            if not res:
                continue
            from datetime import datetime, timedelta, timezone
            q = res[0]["indicators"]["quote"][0]
            for t, c in zip(res[0]["timestamp"], q["close"]):
                d = (datetime.fromtimestamp(t, timezone.utc) + timedelta(hours=9)).strftime("%Y%m%d")
                if d in days and c:
                    got[f"야후 {d}"] = round(c, 1)
        except Exception as e:  # noqa: BLE001
            got[f"야후{sfx}"] = f"못 받음 {type(e).__name__}"
    return got


def main():
    for code in CODES:
        print(f"-- {code} 다른 출처 종가: {outside(code, DAYS)}", flush=True)
    client = broker_kis.market()
    # 지금 한투 일봉(기간별시세)은 10-02를 얼마로 주는지 — 시장 구분 J(거래소) · NX(넥스트레이드) · UN(통합)
    for code in CODES:
        line = []
        for mk in ("J", "NX", "UN"):
            try:
                client.authorize()
                _, data = client.request(
                    'GET', '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice',
                    headers={'authorization': 'Bearer ' + client.token, 'appkey': client.key,
                             'appsecret': client.secret, 'tr_id': 'FHKST03010100', 'custtype': 'P'},
                    params={'FID_COND_MRKT_DIV_CODE': mk, 'FID_INPUT_ISCD': code, 'FID_INPUT_DATE_1': min(DAYS),
                            'FID_INPUT_DATE_2': max(DAYS), 'FID_PERIOD_DIV_CODE': 'D', 'FID_ORG_ADJ_PRC': '0'})
                got = {r.get('stck_bsop_date'): r.get('stck_clpr') for r in (data.get('output2') or [])
                       if r.get('stck_bsop_date') in DAYS}
                line.append(f"{mk}={got}")
            except Exception as e:  # noqa: BLE001
                line.append(f"{mk}=못 받음 {type(e).__name__}")
        print(f"-- {code} 지금 한투 일봉: " + " · ".join(line), flush=True)
    closes = {}
    for code in CODES:
        for name in ("price-data", "etf-data"):
            p = Path(name) / f"{code}.json"
            if p.exists():
                closes[code] = dict(map(tuple, json.loads(p.read_text(encoding="utf-8"))["closes"]))
    for code in CODES:
        for day in DAYS:
            print(f"== {code} {day} · 일봉 종가 {closes.get(code, {}).get(day)}", flush=True)
            for end, past in TRIES:
                try:
                    got = rows(client, code, day, end, past)
                except broker_kis.BrokerError as e:
                    print(f"  끝 {end} · 과거포함 {past}: 거절 · {e}")
                    continue
                print(f"  끝 {end} · 과거포함 {past}: 15:17 뒤 {len(got)}줄 · " + " ".join(f"{t}={p}({v})" for t, p, v in got[-6:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
