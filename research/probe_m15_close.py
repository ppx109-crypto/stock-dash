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


def main():
    client = broker_kis.market()
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
