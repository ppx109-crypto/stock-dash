"""한투 모의투자 연결 점검(사용자 요청 2026-10-01 '확인하고 테스트해줘').

  python paper_check.py check   — 토큰 · 잔고 조회만(주문 없음)
  python paper_check.py order   — 위 점검 뒤 모의투자 계좌에서 1주 시장가 매수 → 체결 확인 → 1주 시장가 매도(거래 ID 확인용)

주문은 paper_trade.PaperBroker로만 넣습니다(모의투자 주소가 아니면 거부 · 실전 키와 같으면 거부).
계좌번호 · 키 · 증권사 응답 본문은 찍지 않습니다. 공개 저장소의 작업 기록에 남기 때문입니다.
"""
import sys
import time

import broker_kis
import paper_trade

TEST_CODE = "010140"        # 시험 주문 종목(시총 100위 안 · 1주 값이 작은 편). 환경에 따라 바꿀 수 있게 인자로도 받음


def why_refused(broker):
    """잔고 거절 문구를 정해진 갈래로만 옮김(문구 자체는 찍지 않음)."""
    if not broker.token:
        return "토큰을 못 받아 잔고까지 가지 못함"
    try:
        _, data = broker.request("GET", "/uapi/domestic-stock/v1/trading/inquire-balance", headers={
            "authorization": "Bearer " + broker.token, "appkey": broker.key, "appsecret": broker.secret,
            "tr_id": "VTTC8434R", "custtype": "P"},
            params={"CANO": broker.cano, "ACNT_PRDT_CD": broker.product, "AFHR_FLPR_YN": "N", "OFL_YN": "",
                    "INQR_DVSN": "02", "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N",
                    "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""})
    except broker_kis.BrokerError:
        return "다시 물어보기도 실패"
    said = str(data.get("msg1") or "").upper()
    for key, text in (("ACNO", "계좌번호가 이 앱 키에 등록된 계좌와 다름(또는 없는 계좌)"),
                      ("PRDT", "상품코드(뒤 2자리)가 다름"), ("CANO", "계좌번호 형식이 다름"),
                      ("모의", "모의투자 쪽 설정 문제"), ("권한", "API 권한 문제")):
        if key in said:
            return text
    return "알 수 없는 갈래(문구 길이 %d)" % len(said)


def main(mode="check", code=TEST_CODE):
    ok, why = paper_trade.enabled()
    print("주문 켜짐:", "예" if ok else f"아니오 · {why}")
    import os
    real = os.getenv("KIS_APP_KEY", "").strip()
    paper = os.getenv("KIS_PAPER_APP_KEY", "").strip()
    print("앱 키:", "❌ 실전 키와 같음" if paper and paper == real else ("✅ 실전 키와 다름" if paper else "❌ 없음"))
    print("앱 시크릿:", "✅ 있음" if os.getenv("KIS_PAPER_APP_SECRET", "").strip() else "❌ 없음")
    try:
        paper_trade.account_parts(os.getenv("KIS_PAPER_ACCOUNT", ""))
        print("계좌번호: ✅ 읽음 · 앞자리 " + str(len(paper_trade.account_parts(os.getenv("KIS_PAPER_ACCOUNT", ""))[0])) + "자리 + 상품코드 2자리")
    except broker_kis.BrokerError as e:
        print("계좌번호: ❌", e)
    try:
        broker = paper_trade.PaperBroker()
    except broker_kis.BrokerError as e:
        print("❌ 모의투자 설정 ·", e)
        return 1
    print("주소: 모의투자 서버" if broker.base == paper_trade.PAPER_BASE else "❌ 모의투자 주소가 아님")
    try:
        broker.authorize()
        print("✅ 토큰 받음")
        bal = broker.balance()
    except broker_kis.BrokerError as e:
        print("❌ 연결 · 잔고 조회 실패 ·", e)
        print("까닭 짐작:", why_refused(broker))
        return 1
    cash = bal.get("cash") or 0
    print(f"✅ 잔고 조회 · 예수금 약 {cash / 1e4:,.0f}만 원 · 보유 {len(bal['positions'])}종목 · 평가 약 {bal['value'] / 1e4:,.0f}만 원")
    # 현금 세 가지(금액만): 오늘 예수금 · D+2 예수금(주문 몫 셈에 씀) · 총평가 — 사고판 날 서로 어떻게 다른지 확인용
    fmt = lambda v: "없음" if v is None else f"{v:,.0f}원"      # 1주 사고팔기는 수수료 몇백 원만 달라져 원 단위로(2026-10-07)
    print(f"ℹ️ 오늘 예수금 {fmt(bal.get('cash_today'))} · D+2 예수금 {fmt(bal.get('cash_d2'))} · 총평가 {fmt(bal.get('eval_total'))}")
    can = broker.buyable(code)            # 시장가로 지금 살 수 있는 수량(주문 전 수량 맞추기 · 2026-10-06)
    print(f"{'✅' if can is not None else '❌'} 시장가 매수가능 조회 ({code}) · " + (f"{can:,}주" if can is not None else "답을 못 받음(주문은 원래 수량대로 나감)"))
    if mode != "order":
        return 0

    before = {p["code"]: int(p["quantity"]) for p in bal["positions"]}.get(code, 0)
    try:
        no = broker.order(code, "buy", 1)
        print(f"✅ 1주 시장가 매수 접수 ({code}) · 주문 번호 {'있음' if no else '없음'}")
    except broker_kis.BrokerError as e:
        print("❌ 매수 주문 실패 ·", e)
        return 1
    held = before
    for _ in range(10):
        time.sleep(3)
        try:
            held = {p["code"]: int(p["quantity"]) for p in broker.balance()["positions"]}.get(code, 0)
        except broker_kis.BrokerError as e:
            print("잔고 다시 조회 실패 ·", e)
            continue
        if held > before:
            break
    print(f"{'✅' if held > before else '⚠️'} 매수 체결 확인 · 보유 {before}주 → {held}주")
    if held <= before:
        print("체결이 아직 안 보여 매도는 넣지 않았습니다(장 시간인지 확인).")
        return 1
    try:                                   # 산 뒤(팔기 전) 현금 — D+2는 산 값만큼 줄고 오늘 예수금은 그대로여야 함
        b1 = broker.balance()
        print(f"ℹ️ 산 뒤 · 오늘 예수금 {fmt(b1.get('cash_today'))} · D+2 예수금 {fmt(b1.get('cash_d2'))} · 총평가 {fmt(b1.get('eval_total'))}")
    except broker_kis.BrokerError:
        pass
    try:
        no = broker.order(code, "sell", 1)
        print(f"✅ 1주 시장가 매도 접수 ({code}) · 주문 번호 {'있음' if no else '없음'}")
    except broker_kis.BrokerError as e:
        print("❌ 매도 주문 실패 ·", e)
        return 1
    after = held
    for _ in range(10):
        time.sleep(3)
        try:
            after = {p["code"]: int(p["quantity"]) for p in broker.balance()["positions"]}.get(code, 0)
        except broker_kis.BrokerError:
            continue
        if after < held:
            break
    print(f"{'✅' if after < held else '⚠️'} 매도 체결 확인 · 보유 {held}주 → {after}주")
    try:                                   # 사고판 뒤 현금 세 가지가 어떻게 바뀌었나(금액만 · 2026-10-06 확인용)
        b2 = broker.balance()
        print(f"ℹ️ 사고판 뒤 · 오늘 예수금 {fmt(b2.get('cash_today'))} · D+2 예수금 {fmt(b2.get('cash_d2'))} · 총평가 {fmt(b2.get('eval_total'))}")
    except broker_kis.BrokerError:
        pass
    return 0 if after < held else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "check", sys.argv[2] if len(sys.argv) > 2 else TEST_CODE))
