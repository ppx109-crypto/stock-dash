"""연구용 ETF 일봉 시가 · 고가 · 저가 · 종가 + 분배금 일정을 한국투자증권에서 받습니다(조회 전용 · 주문과 무관).
C5-ETF 오버나이트(GPT #166 6092707290) 사전등록 전 자료 — 수익은 셈하지 않고 칸 · 결손 · 해시만 봅니다.

- 일봉: 국내주식기간별시세(FHKST03010100 · inquire-daily-itemchartprice · 일 단위) 140일씩 거슬러 받음.
  FID_ORG_ADJ_PRC 0(수정) · 1(원주가) 두 가지를 따로 받아 둘이 같은지 봄.
- 분배금: 예탁원정보 배당일정(HHKDB669102C0 · ksdinfo/dividend) 해마다 · 연속 조회(CTS).
- 저장: etf-ohlc/{코드}.json — 뽑은 칸만(응답 본문 · 키는 저장 · 출력하지 않음).
python collect_etf_ohlc.py [코드 ...]   (기본 069500)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis

OUT = Path(os.getenv("OHLC_OUT", "etf-ohlc"))
SINCE = os.getenv("OHLC_SINCE", "20020101")
KST = ZoneInfo("Asia/Seoul")


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def call(c, path, tr, params, extra=None):
    c.authorize()
    h = {"authorization": "Bearer " + c.token, "appkey": c.key, "appsecret": c.secret, "tr_id": tr, "custtype": "P"}
    if extra:
        h.update(extra)
    _, data = c.request("GET", path, headers=h, params=params)
    return data


def daily(c, code, adj):
    """(날, 시가, 고가, 저가, 종가, 거래량, 거래대금) 목록 · 오래된 날 먼저 · 호출 기록."""
    first = datetime.strptime(SINCE, "%Y%m%d").date()
    cursor = datetime.now(KST).date()
    got, calls = {}, []
    for _ in range(400):
        begin = max(first, cursor - timedelta(days=140))
        p = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_DATE_1": begin.strftime("%Y%m%d"),
             "FID_INPUT_DATE_2": cursor.strftime("%Y%m%d"), "FID_PERIOD_DIV_CODE": "D", "FID_ORG_ADJ_PRC": adj}
        data = call(c, "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", "FHKST03010100", p)
        rows = data.get("output2") or []
        rows = [rows] if isinstance(rows, dict) else rows
        keep = []
        for r in rows:
            d = str(r.get("stck_bsop_date", "")).strip()
            cl = num(r.get("stck_clpr"))
            if re.fullmatch(r"[0-9]{8}", d) and cl and cl > 0:
                keep.append((d, num(r.get("stck_oprc")), num(r.get("stck_hgpr")), num(r.get("stck_lwpr")), cl,
                             num(r.get("acml_vol")), num(r.get("acml_tr_pbmn"))))
        calls.append([p["FID_INPUT_DATE_1"], p["FID_INPUT_DATE_2"], str(data.get("rt_cd")), len(keep)])
        if not keep:
            break
        before = len(got)
        got.update({k[0]: k for k in keep})
        oldest = min(k[0] for k in keep)
        o = date(int(oldest[:4]), int(oldest[4:6]), int(oldest[6:]))
        if o <= first or len(got) == before:
            break
        cursor = o - timedelta(days=1)
        time.sleep(0.2)
    return [list(got[d]) for d in sorted(got)], calls


def dividends(c, code):
    """해마다 배당일정(분배금) — 뽑은 칸만. 칸 이름 목록도 돌려줌(값 아님)."""
    out, cols, calls = [], set(), []
    this = datetime.now(KST).year
    for y in range(int(SINCE[:4]), this + 1):
        cts = ""
        for _ in range(20):
            p = {"CTS": cts, "GB1": "0", "F_DT": f"{y}0101", "T_DT": f"{y}1231", "SHT_CD": code, "HIGH_GB": ""}
            data = call(c, "/uapi/domestic-stock/v1/ksdinfo/dividend", "HHKDB669102C0", p, {"tr_cont": "N" if cts else ""})
            rows = data.get("output1") or data.get("output") or []
            rows = [rows] if isinstance(rows, dict) else rows
            n = 0
            for r in rows:
                cols |= set(r)
                if str(r.get("sht_cd", "")).strip() not in (code, "A" + code):
                    continue
                n += 1
                out.append({"record_date": str(r.get("record_date", "")).strip(), "per_share_cash": num(r.get("per_sto_divi_amt")),
                            "pay_date": str(r.get("divi_pay_dt", "")).strip(), "kind": str(r.get("divi_kind", "")).strip()})
            calls.append([y, str(data.get("rt_cd")), len(rows), n])
            nxt = str(data.get("ctx_area_nk100") or data.get("CTS") or "").strip()
            if not nxt or nxt == cts or not rows:
                break
            cts = nxt
            time.sleep(0.2)
        time.sleep(0.2)
    uniq = {json.dumps(x, sort_keys=True): x for x in out}
    return sorted(uniq.values(), key=lambda x: x["record_date"]), sorted(cols), calls


def main(codes):
    c = broker_kis.market()
    OUT.mkdir(exist_ok=True)
    if os.getenv("OHLC_NAMES_ONLY") == "1":
        # 종목 이름만 확인(조회 1번씩 · 저장은 이름 · 코드만)
        names = {}
        for code in codes:
            try:
                names[code] = c.quote(code).get("name") or ""
            except broker_kis.BrokerError as e:
                names[code] = f"조회 실패 {str(e)[:30]}"
            time.sleep(0.3)
        (OUT / "_names.json").write_text(json.dumps(names, ensure_ascii=False, indent=1), encoding="utf-8")
        print(names)
        return 0
    for code in codes:
        adj, calls_a = daily(c, code, "0")
        raw, calls_r = daily(c, code, "1")
        dist, cols, calls_d = dividends(c, code)
        same = sum(1 for a, b in zip(adj, raw) if a[:5] == b[:5])
        body = {"code": code, "fetched_kst": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
                "source": {"daily": "KIS FHKST03010100 inquire-daily-itemchartprice FID_PERIOD_DIV_CODE=D",
                           "dividend": "KIS HHKDB669102C0 ksdinfo/dividend GB1=0 연도별"},
                "columns": ["날", "시가", "고가", "저가", "종가", "거래량", "거래대금"],
                "adjusted": adj, "raw": raw, "dividends": dist, "dividend_columns": cols,
                "calls": {"adjusted": calls_a, "raw": calls_r, "dividend": calls_d}}
        (OUT / f"{code}.json").write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        print(f"{code}: 수정 {len(adj)}일({adj[0][0] if adj else '-'} ~ {adj[-1][0] if adj else '-'}) · 원주가 {len(raw)}일 · "
              f"앞 다섯 칸 같은 날 {same} · 시가 빈칸 {sum(1 for r in adj if not r[1])} · 분배금 {len(dist)}건 · 배당 칸 {len(cols)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["069500"]))
