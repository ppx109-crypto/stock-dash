"""DART · 한국투자증권에서 과거까지 받을 수 있는 자료를 한 번에 찔러 봅니다(조회 전용, 저장하지 않음).

무엇을 줄 수 있는지(줄 수 · 칸 이름 · 가장 옛날과 최근 날짜)만 찍습니다. 응답 값·본문·키는 찍지 않습니다.
python probe_catalog.py dart | kis
"""
import re
import sys

import requests

DATE_KEYS = ("rcept_no", "rcept_dt", "stck_bsop_date", "bsop_date", "deal_date", "record_date", "bass_dt",
             "list_dt", "stlm_dt", "stac_yymm", "stck_bsop_date1", "dt", "trad_dt", "divi_pay_dt", "bgn_de")


def span(rows):
    for k in DATE_KEYS:
        days = sorted(str(r.get(k, ""))[:8] for r in rows if re.fullmatch(r"[0-9]{6,8}.*", str(r.get(k, ""))))
        if days:
            return f"{k} {days[0]}~{days[-1]}"
    return "-"


def show(name, rows, status=""):
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    cols = ", ".join(sorted(rows[0]))[:600] if rows else ""
    print(f"  {name} · {status} · 줄 {len(rows)} · {span(rows)}", flush=True)
    if cols:
        print(f"    칸: {cols}", flush=True)


def dart():
    import os
    key = os.environ.get("DART_CRTFC_KEY", "").strip()
    if not key:
        print("DART 키 없음"); return
    corps = {"삼성전자": "00126380", "SK하이닉스": "00164779", "에코프로": "00536541"}
    wide = {"bgn_de": "20170101", "end_de": "20260929"}
    asks = [
        ("임원·주요주주 소유보고", "elestock.json", {}),
        ("대량보유 상황보고(5%)", "majorstock.json", {}),
        ("자기주식 취득 결정", "tsstkAqDecsn.json", wide),
        ("자기주식 처분 결정", "tsstkDpDecsn.json", wide),
        ("자기주식 신탁 체결", "tsstkAqTrctrCnsDecsn.json", wide),
        ("유상증자 결정", "piicDecsn.json", wide),
        ("무상증자 결정", "fricDecsn.json", wide),
        ("전환사채 발행 결정", "cvbdIsDecsn.json", wide),
        ("신주인수권부사채 발행 결정", "bdwtIsDecsn.json", wide),
        ("교환사채 발행 결정", "exbdIsDecsn.json", wide),
        ("감자 결정", "crDecsn.json", wide),
        ("타법인주식 양수 결정", "otcprStkInvscrInhDecsn.json", wide),
        ("영업양수 결정", "bsnInhDecsn.json", wide),
        ("회사합병 결정", "cmpMgDecsn.json", wide),
        ("소송 등 제기", "lwstLg.json", wide),
        ("배당(2023 사업보고서)", "alotMatter.json", {"bsns_year": "2023", "reprt_code": "11011"}),
        ("배당(2017 사업보고서)", "alotMatter.json", {"bsns_year": "2017", "reprt_code": "11011"}),
        ("최대주주 현황(2023)", "hyslrSttus.json", {"bsns_year": "2023", "reprt_code": "11011"}),
        ("최대주주 변동(2023)", "hyslrChgSttus.json", {"bsns_year": "2023", "reprt_code": "11011"}),
        ("자기주식 취득·처분 현황(2023)", "tesstkAcqsDspsSttus.json", {"bsns_year": "2023", "reprt_code": "11011"}),
        ("주식총수(2023)", "stockTotqySttus.json", {"bsns_year": "2023", "reprt_code": "11011"}),
        ("소액주주(2023)", "mrhlSttus.json", {"bsns_year": "2023", "reprt_code": "11011"}),
        ("주요계정 1분기(2017)", "fnlttSinglAcnt.json", {"bsns_year": "2017", "reprt_code": "11013"}),
        ("주요계정 3분기(2017)", "fnlttSinglAcnt.json", {"bsns_year": "2017", "reprt_code": "11014"}),
        ("주요 재무지표 수익성(2023 1분기)", "fnlttSinglIndx.json", {"bsns_year": "2023", "reprt_code": "11013", "idx_cl_code": "M210000"}),
        ("주요 재무지표 수익성(2017 사업)", "fnlttSinglIndx.json", {"bsns_year": "2017", "reprt_code": "11011", "idx_cl_code": "M210000"}),
        ("공시 목록(2017 한 해)", "list.json", {"bgn_de": "20170101", "end_de": "20171231", "page_count": "100"}),
    ]
    for label, corp in corps.items():
        print("회사", label)
        for name, ep, extra in asks:
            try:
                r = requests.get("https://opendart.fss.or.kr/api/" + ep,
                                 params={"crtfc_key": key, "corp_code": corp, **extra}, timeout=(10, 30))
                data = r.json()
            except (requests.RequestException, ValueError):
                print(f"  {name} · 받지 못함"); continue
            status = str(data.get("status", ""))
            status = status if re.fullmatch(r"[0-9]{3}", status) else "?"
            show(name, data.get("list"), f"status {status}")


def kis():
    import broker_kis
    c = broker_kis.market()

    def ask(name, path, tr, params, key="output"):
        try:
            c.authorize()
            _, data = c.request("GET", path, headers={
                "authorization": "Bearer " + c.token, "appkey": c.key, "appsecret": c.secret,
                "tr_id": tr, "custtype": "P"}, params=params)
        except broker_kis.BrokerError as e:
            print(f"  {name} · 거절 {str(e)[:60]}"); return
        msg = str(data.get("msg_cd") or "")
        msg = msg if re.fullmatch(r"[A-Z]{2,4}[0-9]{3,6}", msg) else ""
        for k in ("output", "output1", "output2"):
            rows = data.get(k)
            if isinstance(rows, dict):
                rows = [rows]
            if rows:
                show(f"{name} [{k}]", rows, f"rt_cd {data.get('rt_cd')} {msg}")
        if not any(data.get(k) for k in ("output", "output1", "output2")):
            print(f"  {name} · rt_cd {data.get('rt_cd')} {msg} · 빈 응답", flush=True)

    Q = "/uapi/domestic-stock/v1/quotations/"
    for code in ("005930",):
        print("종목", code)
        for d in ("20260925", "20210315", "20170315"):
            ask(f"종목별 프로그램매매 일별 {d}", Q + "program-trade-by-stock-daily", "FHPPG04650201",
                {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_DATE_1": d})
        for a, b in (("20260801", "20260925"), ("20210101", "20210331"), ("20170101", "20170331")):
            ask(f"종목별 대차거래 일별 {a}~{b}", Q + "daily-loan-trans", "HHPST074500C0",
                {"MRKT_DIV_CLS_CODE": "3", "MKSC_SHRN_ISCD": code, "START_DATE": a, "END_DATE": b, "CTS": ""})
            ask(f"종목별 일별 매수·매도 체결량 {a}~{b}", Q + "inquire-daily-trade-volume", "FHKST03010800",
                {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_PERIOD_DIV_CODE": "D",
                 "FID_INPUT_DATE_1": a, "FID_INPUT_DATE_2": b})
        ask("종목 추정실적(지금)", Q + "estimate-perform", "HHKST668300C0", {"SHT_CD": code})
        ask("증권사별 투자의견 2017", Q + "invest-opbysec", "FHKST663400C0",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_DIV_CODE": "16634", "FID_INPUT_ISCD": "00017",
             "FID_DIV_CLS_CODE": "0", "FID_INPUT_DATE_1": "20170101", "FID_INPUT_DATE_2": "20171231"})
        ask("시간외 일자별", Q + "inquire-daily-overtimeprice", "FHPST02320000",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code})
        for div in ("0", "1"):
            ask(f"재무비율({'연' if div == '0' else '분기'})", "/uapi/domestic-stock/v1/finance/financial-ratio", "FHKST66430300",
                {"FID_DIV_CLS_CODE": div, "fid_cond_mrkt_div_code": "J", "fid_input_iscd": code})
    print("시장 전체")
    for a, b in (("20260801", "20260925"), ("20170101", "20170331")):
        ask(f"코스피 지수 일별 {a}~{b}", Q + "inquire-daily-indexchartprice", "FHKUP03500100",
            {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": "0001", "FID_INPUT_DATE_1": a, "FID_INPUT_DATE_2": b,
             "FID_PERIOD_DIV_CODE": "D"})
        ask(f"시장별 투자자 일별 {a}~{b}", Q + "inquire-investor-daily-by-market", "FHPTJ04040000",
            {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": "0001", "FID_INPUT_DATE_1": a, "FID_INPUT_ISCD_1": "KSP",
             "FID_INPUT_DATE_2": b, "FID_INPUT_ISCD_2": "0001"})
        ask(f"프로그램매매 종합 일별 {a}~{b}", Q + "comp-program-trade-daily", "FHPPG04600001",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_MRKT_CLS_CODE": "K", "FID_INPUT_DATE_1": a, "FID_INPUT_DATE_2": b})
    for d in ("20260925", "20170315"):
        ask(f"증시자금 종합 {d}", Q + "mktfunds", "FHKST649100C0", {"FID_INPUT_DATE_1": d})
    K = "/uapi/domestic-stock/v1/ksdinfo/"
    for name, ep, tr in (("의무예치(보호예수) 일정", "mand-deposit", "HHKDB669110C0"),
                         ("유상증자 일정", "paidin-capin", "HHKDB669100C0"),
                         ("무상증자 일정", "bonus-issue", "HHKDB669101C0"),
                         ("배당 일정", "dividend", "HHKDB669102C0")):
        for a, b in (("20260101", "20260925"), ("20170101", "20171231")):
            params = {"CTS": "", "F_DT": a, "T_DT": b, "SHT_CD": ""}
            if ep == "paidin-capin":
                params["GB1"] = "1"
            if ep == "bonus-issue" or ep == "dividend":
                params.update({"GB1": "0", "HIGH_GB": ""})
            ask(f"{name} {a}~{b}", K + ep, tr, params)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "dart":
        dart()
    elif which == "kis":
        kis()
