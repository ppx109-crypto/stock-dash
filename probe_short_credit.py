"""증권사가 공매도·신용잔고를 과거까지 주는지 찔러 봅니다(조회 전용, 저장하지 않음).

국내주식 공매도 일별추이(FHPST04830000)와 신용잔고 일별추이(FHPST04760000)를 날짜를 바꿔 가며 물어
몇 줄이 오는지 · 어떤 칸이 있는지 · 가장 옛날은 언제인지만 찍습니다. 응답 본문을 통째로 찍지 않습니다.
"""
import re
import sys

import broker_kis

ASKS = {
    "공매도": ("/uapi/domestic-stock/v1/quotations/daily-short-sale", "FHPST04830000",
             lambda code, a, b: {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code,
                                 "FID_INPUT_DATE_1": a, "FID_INPUT_DATE_2": b}),
    "신용잔고": ("/uapi/domestic-stock/v1/quotations/daily-credit-balance", "FHPST04760000",
             lambda code, a, b: {"fid_cond_mrkt_div_code": "J", "fid_cond_scr_div_code": "20476",
                                 "fid_input_iscd": code, "fid_input_date_1": b}),
}


def ask(client, name, code, a, b):
    path, tr, params = ASKS[name]
    client.authorize()
    _, data = client.request("GET", path, headers={
        "authorization": "Bearer " + client.token, "appkey": client.key, "appsecret": client.secret,
        "tr_id": tr, "custtype": "P"}, params=params(code, a, b))
    msg = str(data.get("msg_cd") or "")
    msg = msg if re.fullmatch(r"[A-Z]{2,4}[0-9]{3,6}", msg) else ""
    rows = data.get("output2") if data.get("output2") is not None else data.get("output")
    if isinstance(rows, dict):
        rows = [rows]
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    key = next((k for k in ("stck_bsop_date", "deal_date", "bsop_date") if rows and k in rows[0]), None)
    days = sorted(str(r.get(key, "")) for r in rows) if key else []
    print(f"  {name} {a}~{b} · rt_cd {data.get('rt_cd')} {msg} · 줄 {len(rows)} · "
          f"{days[0] if days else '-'} ~ {days[-1] if days else '-'}")
    if rows:
        print("    칸:", ", ".join(sorted(rows[0]))[:900])
        print("    첫 줄:", {k: rows[0][k] for k in sorted(rows[0])[:40]})


def main():
    code = sys.argv[1] if len(sys.argv) > 1 and re.fullmatch(r"[0-9]{6}", sys.argv[1]) else "005930"
    client = broker_kis.market()
    print("종목", code)
    for name in ASKS:
        for a, b in (("20260801", "20260925"), ("20250101", "20250331"), ("20210101", "20210331"),
                     ("20170101", "20170331")):
            try:
                ask(client, name, code, a, b)
            except broker_kis.BrokerError as error:
                print(f"  {name} {a}~{b} · 거절: {str(error)[:80]}")


if __name__ == "__main__":
    main()
