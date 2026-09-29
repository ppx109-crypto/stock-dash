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


def kis_hour():
    """한국투자증권에 1시간봉을 바로 주는 조회가 있는지: 간격을 고르는 칸이 있는 조회를 3600초(1시간)로 불러 봄."""
    import broker_kis
    c = broker_kis.market()
    Q = "/uapi/domestic-stock/v1/quotations/"

    def ask(name, path, tr, params, stamp=("stck_bsop_date", "stck_cntg_hour")):
        try:
            c.authorize()
            _, data = c.request("GET", Q + path, headers={
                "authorization": "Bearer " + c.token, "appkey": c.key, "appsecret": c.secret,
                "tr_id": tr, "custtype": "P"}, params=params)
        except broker_kis.BrokerError as e:
            print(f"  {name} · 거절 {str(e)[:60]}", flush=True)
            return
        msg = str(data.get("msg_cd") or "")
        msg = msg if re.fullmatch(r"[A-Z]{2,4}[0-9]{3,6}", msg) else ""
        rows = [r for r in (data.get("output2") or []) if isinstance(r, dict)]
        stamps = sorted(f"{r.get(stamp[0], '')} {r.get(stamp[1], '')}" for r in rows)
        gaps = sorted({s[-6:-2] for s in stamps})[:8]
        print(f"  {name} · rt_cd {data.get('rt_cd')} {msg} · 줄 {len(rows)} · "
              f"{stamps[0] if stamps else '-'} ~ {stamps[-1] if stamps else '-'} · 시분 예 {gaps}", flush=True)
        if rows:
            print(f"    칸: {', '.join(sorted(rows[0]))[:300]}", flush=True)

    # ① 업종(지수) 분봉조회: 간격(초)을 고르는 칸이 있음 — 3600 = 1시간봉
    for iv in ("3600", "60"):
        ask(f"코스피 지수 분봉 간격 {iv}초", "inquire-time-indexchartprice", "FHKUP03500200",
            {"FID_COND_MRKT_DIV_CODE": "U", "FID_ETC_CLS_CODE": "0", "FID_INPUT_ISCD": "0001",
             "FID_INPUT_HOUR_1": iv, "FID_PW_DATA_INCU_YN": "Y"}, stamp=("stck_bsop_date", "stck_cntg_hour"))
    # ② 주식 당일분봉: 과거 포함(Y)으로 몇 날이 오는지
    ask("삼성전자 당일분봉(과거 포함)", "inquire-time-itemchartprice", "FHKST03010200",
        {"FID_ETC_CLS_CODE": "", "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930",
         "FID_INPUT_HOUR_1": "153000", "FID_PW_DATA_INCU_YN": "Y"})
    # ③ 기간별 시세에 시간 단위가 있는지(문서엔 일 · 주 · 월 · 년뿐)
    for div in ("H", "60"):
        ask(f"삼성전자 기간별 시세 구분 {div}", "inquire-daily-itemchartprice", "FHKST03010100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930", "FID_INPUT_DATE_1": "20260901",
             "FID_INPUT_DATE_2": "20260925", "FID_PERIOD_DIV_CODE": div, "FID_ORG_ADJ_PRC": "0"},
            stamp=("stck_bsop_date", "stck_cntg_hour"))
    # ④ 일별분봉의 끝(1분봉을 모아 1시간봉을 만들 수 있는 가장 먼 날)
    path = "inquire-time-dailychartprice"
    for day in ("20250919", "20250918", "20250917", "20250916"):
        ask(f"삼성전자 일별분봉 {day}", path, "FHKST03010230",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930", "FID_INPUT_HOUR_1": "153000",
             "FID_INPUT_DATE_1": day, "FID_PW_DATA_INCU_YN": "Y", "FID_FAKE_TICK_INCU_YN": ""})


def kis_intraday():
    """장중(시간대별) 자료가 과거 날짜로도 나오는지: 줄 수 · 칸 이름 · 시각 · 날짜 범위만 찍음(본문 · 키 안 찍음)."""
    import broker_kis
    c = broker_kis.market()
    Q = "/uapi/domestic-stock/v1/quotations/"

    def ask(name, path, tr, params):
        try:
            c.authorize()
            _, data = c.request("GET", Q + path, headers={
                "authorization": "Bearer " + c.token, "appkey": c.key, "appsecret": c.secret,
                "tr_id": tr, "custtype": "P"}, params=params)
        except broker_kis.BrokerError as e:
            print(f"  {name} · 거절 {str(e)[:60]}", flush=True)
            return
        msg = str(data.get("msg_cd") or "")
        msg = msg if re.fullmatch(r"[A-Z]{2,4}[0-9]{3,6}", msg) else ""
        shown = False
        for key in ("output", "output1", "output2"):
            rows = data.get(key)
            rows = [rows] if isinstance(rows, dict) else (rows or [])
            rows = [r for r in rows if isinstance(r, dict)]
            if not rows:
                continue
            shown = True
            tk = [k for k in rows[0] if "hour" in k or "time" in k or k.endswith("_tm")]
            dk = [k for k in rows[0] if "date" in k or k.endswith("_dt")]
            ts = sorted(str(r.get(tk[0], "")) for r in rows) if tk else []
            ds = sorted(str(r.get(dk[0], "")) for r in rows) if dk else []
            print(f"  {name} [{key}] · rt_cd {data.get('rt_cd')} {msg} · 줄 {len(rows)} · 시각 {ts[0] if ts else '-'}~{ts[-1] if ts else '-'}"
                  f" · 날짜 {ds[0] if ds else '-'}~{ds[-1] if ds else '-'}", flush=True)
            print(f"    칸: {', '.join(sorted(rows[0]))[:400]}", flush=True)
        if not shown:
            print(f"  {name} · rt_cd {data.get('rt_cd')} {msg} · 빈 응답", flush=True)

    code = "005930"
    for day in ("", "20260925", "20260615", "20250915"):
        tag = day or "오늘"
        ask(f"시간대별 체결({tag})", "inquire-time-itemconclusion", "FHPST01060000",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_HOUR_1": "153000",
             **({"FID_INPUT_DATE_1": day} if day else {})})
        ask(f"종목 프로그램매매 체결 시간별({tag})", "program-trade-by-stock", "FHPPG04650100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, **({"FID_INPUT_DATE_1": day} if day else {})})
        ask(f"종목 투자자 추정(장중, {tag})", "investor-trend-estimate", "HHPTJ04160200",
            {"MKSC_SHRN_ISCD": code, **({"FID_INPUT_DATE_1": day} if day else {})})
    ask("시장 투자자 시간별(코스피)", "inquire-investor-time-by-market", "FHPTJ04030000",
        {"FID_INPUT_ISCD": "0001", "FID_INPUT_ISCD_2": "0001"})
    ask("종목 외국계 순매수 추이(장중)", "frgnmem-pchs-trend", "FHKST644400C0",
        {"FID_INPUT_ISCD": code, "FID_INPUT_ISCD_2": "99999", "FID_COND_MRKT_DIV_CODE": "J"})
    ask("프로그램매매 종합 시간별(코스피)", "comp-program-trade-today", "FHPPG04600101",
        {"FID_COND_MRKT_DIV_CODE": "J", "FID_MRKT_CLS_CODE": "K", "FID_SCTN_CLS_CODE": "", "FID_INPUT_ISCD": "",
         "FID_COND_MRKT_DIV_CODE1": "", "FID_INPUT_HOUR_1": ""})
    ask("국내기관 · 외국인 매매 가집계(장중)", "foreign-institution-total", "FHPTJ04400000",
        {"FID_COND_MRKT_DIV_CODE": "V", "FID_COND_SCR_DIV_CODE": "16449", "FID_INPUT_ISCD": "0000",
         "FID_DIV_CLS_CODE": "0", "FID_RANK_SORT_CLS_CODE": "0", "FID_ETC_CLS_CODE": "0"})


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
    elif which == "kis_intraday":
        kis_intraday()
    elif which == "kis_hour":
        kis_hour()
    elif which == "yahoo":
        yahoo()
    else:
        print("kis 또는 yahoo")
