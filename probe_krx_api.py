"""KRX 공식 Open API(인증키)로 과거 날짜를 물어 무엇이 오는지 찔러 봅니다(조회 전용 · 저장 안 함 · 사용자 제안 2026-10-02).

목적: 코스닥 연구의 '지금 상장된 종목만' 치우침을 없애기 — 날짜 하나를 물으면 그날 상장돼 있던 모든 종목(뒤에 폐지된 종목 포함)의
종가 · 거래량 · 거래대금 · 시가총액 · 상장주식수가 오는지, 몇 년 전까지 오는지.
찍는 것: 서비스별 성공/실패(HTTP 코드 · 줄 수) · 칸 이름 · 그날 종목 수. 값과 키는 찍지 않습니다.
키: 환경 변수 KRX_AUTH_KEY(GitHub Secrets). 서비스마다 KRX Open API 사이트에서 '이용 신청' 승인이 따로 필요합니다.
"""
import os
import sys
import time

import requests

BASE = "https://data-dbg.krx.co.kr/svc/apis"
SERVICES = {
    "sto/stk_bydd_trd": "유가증권 일별매매정보",
    "sto/ksq_bydd_trd": "코스닥 일별매매정보",
    "sto/stk_isu_base_info": "유가증권 종목기본정보",
    "sto/ksq_isu_base_info": "코스닥 종목기본정보",
    "idx/kosdaq_dd_trd": "코스닥 지수 일별",
    "idx/kospi_dd_trd": "코스피 지수 일별",
}
DAYS = ("20260930", "20240603", "20210104", "20170102", "20150102", "20120102", "20100104")


def ask(path, day, key):
    time.sleep(0.2)
    try:
        r = requests.get(f"{BASE}/{path}", headers={"AUTH_KEY": key}, params={"basDd": day}, timeout=(10, 30))
    except requests.RequestException as e:
        return f"연결 실패({type(e).__name__})", []
    if r.status_code != 200:
        return f"HTTP {r.status_code}", []
    try:
        rows = r.json().get("OutBlock_1")
    except ValueError:
        return "응답 형식 아님", []
    return ("성공" if isinstance(rows, list) else "칸 없음"), (rows if isinstance(rows, list) else [])


def main():
    key = os.environ.get("KRX_AUTH_KEY", "").strip()
    if not key:
        print("KRX_AUTH_KEY가 없습니다. GitHub 저장소 Settings → Secrets → Actions에 넣어 주세요.")
        return 1
    for path, name in SERVICES.items():
        print(f"== {name} ({path}) ==", flush=True)
        for day in DAYS:
            status, rows = ask(path, day, key)
            cols = ", ".join(sorted(rows[0]))[:400] if rows else ""
            print(f"  {day}: {status} · 줄 {len(rows)}" + (f" · 칸: {cols}" if cols and day == DAYS[0] else ""), flush=True)
            if status.startswith("HTTP 4"):
                break
    # 폐지 종목이 들어 있나: 2017-01-02 코스닥 목록에 있으나 2026-09-30 목록에 없는 코드 수
    _, old = ask("sto/ksq_bydd_trd", "20170102", key)
    _, new = ask("sto/ksq_bydd_trd", "20260930", key)
    a = {str(r.get("ISU_SRT_CD", "")).zfill(6) for r in old}
    b = {str(r.get("ISU_SRT_CD", "")).zfill(6) for r in new}
    if a and b:
        print(f"\n코스닥 2017-01-02 종목 {len(a)} · 2026-09-30 종목 {len(b)} · 2017엔 있고 지금은 없는(폐지 · 이전) {len(a - b)}", flush=True)
    print("끝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
