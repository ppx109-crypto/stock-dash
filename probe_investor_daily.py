"""증권사 '종목별 투자자매매동향(일별)'이 과거치와 투신 칸을 주는지 찔러 봅니다.

지금 쌓는 수급(inquire-investor)은 최근 서른 거래일뿐이고 기관이 한 덩어리입니다.
스승님 조건(외국인·투신이 사고 개인이 판다)을 과거로 검증하려면 투신 칸과 긴 기간이
필요합니다. 날짜를 바꿔 가며 물어, 몇 줄이 오는지 · 어떤 칸이 있는지 · 가장 옛날은
언제인지만 찍습니다. 응답 본문을 통째로 찍지 않습니다. 조회 전용이며 주문과 무관합니다.
"""
import re
import sys

import broker_kis

PATH = "/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily"
WANT = ("stck_bsop_date", "stck_clpr", "prsn_ntby_qty", "frgn_ntby_qty", "orgn_ntby_qty", "ivtr_ntby_qty",
        "pe_fund_ntby_vol", "fund_ntby_qty")


def ask(client, code, day):
    client.authorize()
    _, data = client.request(
        "GET", PATH,
        headers={"authorization": "Bearer " + client.token, "appkey": client.key,
                 "appsecret": client.secret, "tr_id": "FHPTJ04160001", "custtype": "P"},
        params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_DATE_1": day,
                "FID_ORG_ADJ_PRC": "", "FID_ETC_CLS_CODE": ""})
    code_ok = str(data.get("rt_cd"))
    msg = str(data.get("msg_cd") or "")
    msg = msg if re.fullmatch(r"[A-Z]{2,4}[0-9]{3,6}", msg) else ""
    rows = data.get("output2") or []
    if isinstance(rows, dict):
        rows = [rows]
    days = sorted(str(r.get("stck_bsop_date", "")) for r in rows if isinstance(r, dict))
    print(f"  물은 날 {day} · rt_cd {code_ok} {msg} · 줄 {len(rows)} · "
          f"{days[0] if days else '-'} ~ {days[-1] if days else '-'}")
    if rows and isinstance(rows[0], dict):
        keys = sorted(rows[0])
        # 칸 이름만 찍습니다(값은 찍지 않음). 순매수 칸 · 금액 칸을 잘리지 않게 따로.
        print("    순매수 칸:", ", ".join(k for k in keys if "ntby" in k))
        print("    그 밖 칸:", ", ".join(k for k in keys if "ntby" not in k))
        filled = sum(1 for r in rows if isinstance(r, dict) and str(r.get("frgn_ntby_qty") or "").strip() not in ("", "0"))
        print(f"    외국인 칸이 비지 않은 줄 {filled}/{len(rows)}")


def main():
    code = sys.argv[1] if len(sys.argv) > 1 and re.fullmatch(r"[0-9]{6}", sys.argv[1]) else "005930"
    client = broker_kis.market()
    print("종목", code)
    for day in ("20260925", "20150630", "20120629", "20100630", "20080630", "20050630", "20020628", "20000630", "19970630"):
        try:
            ask(client, code, day)
        except broker_kis.BrokerError as error:
            print(f"  물은 날 {day} · 거절: {str(error)[:80]}")


if __name__ == "__main__":
    main()
