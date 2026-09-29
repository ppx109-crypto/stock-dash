"""증권사 목표가(투자의견)를 과거까지 주는지 찔러 봅니다(조회 전용, 저장하지 않음).

국내주식 종목투자의견(FHKST663300C0)을 해마다 기간을 바꿔 물어 몇 줄이 오는지 · 가장 옛날은 언제인지만 찍습니다.
응답 본문은 찍지 않습니다(msg_cd는 모양을 확인한 것만).
"""
import re
import sys

import broker_kis

SPANS = (("20260101", "20260925"), ("20240101", "20241231"), ("20210101", "20211231"),
         ("20190101", "20191231"), ("20170101", "20171231"))


def ask(client, code, a, b):
    client.authorize()
    _, data = client.request("GET", "/uapi/domestic-stock/v1/quotations/invest-opinion", headers={
        "authorization": "Bearer " + client.token, "appkey": client.key, "appsecret": client.secret,
        "tr_id": "FHKST663300C0", "custtype": "P"},
        params={"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_DIV_CODE": "16633", "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": a, "FID_INPUT_DATE_2": b})
    msg = str(data.get("msg_cd") or "")
    msg = msg if re.fullmatch(r"[A-Z]{2,4}[0-9]{3,6}", msg) else ""
    rows = data.get("output")
    if isinstance(rows, dict):
        rows = [rows]
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    days = sorted(str(r.get("stck_bsop_date", "")) for r in rows if re.fullmatch(r"[0-9]{8}", str(r.get("stck_bsop_date", ""))))
    print(f"  {a}~{b} · rt_cd {data.get('rt_cd')} {msg} · 줄 {len(rows)} · "
          f"{days[0] if days else '-'} ~ {days[-1] if days else '-'}", flush=True)


def main():
    codes = [c for c in sys.argv[1:] if re.fullmatch(r"[0-9]{6}", c)] or ["005930", "000660"]
    client = broker_kis.market()
    for code in codes:
        print("종목", code)
        for a, b in SPANS:
            try:
                ask(client, code, a, b)
            except broker_kis.BrokerError as error:
                print(f"  {a}~{b} · 거절: {str(error)[:60]}")


if __name__ == "__main__":
    main()
