"""1시간봉(분봉) 과거 자료를 어디서 얼마나 받을 수 있는지 찔러 봅니다(조회 전용, 저장 안 함).

찍는 것은 줄 수 · 칸 이름 · 첫/끝 시각뿐입니다. 키나 응답 본문은 찍지 않습니다.
- kis: 한국투자증권 주식일별분봉조회(FHKST03010230) — 날짜를 거슬러 가며 몇 년 전까지 나오는지
- yahoo: 야후 파이낸스 60분봉(.KS) — 몇 날짜치가 나오는지
"""
import re
import sys

from probe_catalog import show


def kis():
    import broker_kis
    c = broker_kis.market()
    path = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
    days = ("20260925", "20260316", "20260105", "20251201", "20251103", "20251001", "20250930",
            "20250929", "20250926", "20250922", "20250915")
    for day in days:
        for hour in (("153000", "110000") if day == "20260925" else ("153000",)):
            try:
                c.authorize()
                _, data = c.request("GET", path, headers={
                    "authorization": "Bearer " + c.token, "appkey": c.key, "appsecret": c.secret,
                    "tr_id": "FHKST03010230", "custtype": "P"}, params={
                    "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930", "FID_INPUT_HOUR_1": hour,
                    "FID_INPUT_DATE_1": day, "FID_PW_DATA_INCU_YN": "Y", "FID_FAKE_TICK_INCU_YN": ""})
            except broker_kis.BrokerError as e:
                print(f"  분봉 {day} {hour} · 거절 {str(e)[:60]}", flush=True)
                continue
            msg = str(data.get("msg_cd") or "")
            msg = msg if re.fullmatch(r"[A-Z]{2,4}[0-9]{3,6}", msg) else ""
            rows = data.get("output2") or []
            rows = [r for r in rows if isinstance(r, dict)]
            stamps = sorted(f"{r.get('stck_bsop_date', '')} {r.get('stck_cntg_hour', '')}" for r in rows)
            print(f"  분봉 {day} {hour} · rt_cd {data.get('rt_cd')} {msg} · 줄 {len(rows)} · "
                  f"{stamps[0] if stamps else '-'} ~ {stamps[-1] if stamps else '-'}", flush=True)
            if rows and day == "20260925" and hour == "153000":
                show("분봉 칸", rows[:1])


def yahoo():
    import datetime as dt
    import requests
    for sym in ("005930.KS", "000660.KS"):
        for rng in ("730d", "60d"):
            try:
                r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                                 params={"interval": "60m", "range": rng},
                                 headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                res = (r.json().get("chart") or {}).get("result") or []
            except Exception as e:  # 네트워크 · 형식 오류는 이름만
                print(f"  야후 {sym} {rng} · 실패 {type(e).__name__}", flush=True)
                continue
            if not res:
                print(f"  야후 {sym} {rng} · HTTP {r.status_code} · 빈 응답", flush=True)
                continue
            ts = res[0].get("timestamp") or []
            kst = dt.timezone(dt.timedelta(hours=9))
            first = dt.datetime.fromtimestamp(ts[0], kst).strftime("%Y-%m-%d %H:%M") if ts else "-"
            last = dt.datetime.fromtimestamp(ts[-1], kst).strftime("%Y-%m-%d %H:%M") if ts else "-"
            days = len({dt.datetime.fromtimestamp(t, kst).date() for t in ts})
            print(f"  야후 {sym} {rng} · 봉 {len(ts)} · 날 {days} · {first} ~ {last}", flush=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "kis":
        kis()
    elif which == "yahoo":
        yahoo()
    else:
        print("kis 또는 yahoo")
