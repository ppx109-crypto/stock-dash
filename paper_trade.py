"""한국투자증권 **모의투자** 계좌로 1시간봉 A그룹(연구 90 · 94회차 최종 규칙)을 자동 매수 · 매도(사용자 결정 2026-10-01 '가').

- 주문은 **모의투자 서버(openapivts)에만** 넣습니다. 주문 직전에 주소를 다시 확인하고, 실전 주소면 거부합니다.
- 키 · 계좌는 GitHub Secrets의 KIS_PAPER_APP_KEY · KIS_PAPER_APP_SECRET · KIS_PAPER_ACCOUNT(예: 50123456-01)에만 둡니다.
  실전 키(KIS_APP_KEY)와 따로이며, 어디에도 찍지 않습니다. 증권사 응답 본문도 찍지 않고 정해진 형태의 코드만 씁니다.
- 끄기: 비밀값이 없거나 PAPER_TRADING이 'on'이 아니거나 hourly-live/paper-off 파일이 있으면 주문하지 않습니다.
- hourly_a.fill이 '이 봉 시가에 체결'로 적은 매매(연습 계좌)를 같은 때 시장가 주문으로 따라 넣습니다.
  산 금액 = 모의 계좌 총액(예수금 + 평가) × 칸 / 10, 같은 매매는 두 번 주문하지 않습니다(주문 장부의 열쇠).
"""
import json
import math
import os
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis

KST = ZoneInfo("Asia/Seoul")
PAPER_BASE = "https://openapivts.koreainvestment.com:29443"
ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"
BOOK = Path("hourly-live/paper-orders.json")
OFF = Path("hourly-live/paper-off")
SLOTS = 10
# 모의투자 주문 거래 ID(현금 매수 · 매도). 한투가 바꾸면 환경변수로 덮어씀.
TR_BUY = os.getenv("KIS_PAPER_TR_BUY", "VTTC0012U")
TR_SELL = os.getenv("KIS_PAPER_TR_SELL", "VTTC0011U")


def account_parts(text):
    """계좌번호 → (앞 8자리, 상품코드 2자리). '50123456-01' · '5012345601' · '50123456'(상품코드 01로 봄) ·
    빈칸 · 다른 꼴의 줄표가 섞여도 숫자만 봄. 맞지 않으면 숫자 자리 수만 알려 줌(번호는 찍지 않음)."""
    digits = re.sub(r"[^0-9]", "", str(text or ""))
    if len(digits) == 10:
        return digits[:8], digits[8:]
    if len(digits) == 8:
        return digits, "01"
    raise broker_kis.BrokerError(f"모의투자 계좌번호(KIS_PAPER_ACCOUNT)의 숫자가 {len(digits)}자리입니다. "
                                 "'50123456-01'처럼 8자리-2자리로 넣어 주세요"
                                 "(KIS Developers 표의 7자리 번호는 앞 0을 붙여도 잔고 조회가 거절됨(OPSQ2000) · 모의투자 화면의 계좌번호를 쓰세요).")


class PaperBroker(broker_kis.KIS):
    """모의투자 전용 연결. 실전 키 · 실전 주소는 받지 않습니다."""

    def __init__(self):
        self.key = os.getenv("KIS_PAPER_APP_KEY", "").strip()
        self.secret = os.getenv("KIS_PAPER_APP_SECRET", "").strip()
        missing = [n for n, v in (("KIS_PAPER_APP_KEY", self.key), ("KIS_PAPER_APP_SECRET", self.secret),
                                   ("KIS_PAPER_ACCOUNT", os.getenv("KIS_PAPER_ACCOUNT", "").strip())) if not v]
        if missing:
            raise broker_kis.BrokerError("모의투자 비밀값이 없습니다: " + " · ".join(missing))
        if self.key == os.getenv("KIS_APP_KEY", "").strip():
            raise broker_kis.BrokerError("모의투자 키가 실전 키와 같습니다. 모의투자 앱의 키를 넣어 주세요.")
        self.cano, self.product = account_parts(os.getenv("KIS_PAPER_ACCOUNT", ""))
        self.mode = "demo"
        self.base = PAPER_BASE
        self.token = None
        self.expires = 0
        import threading
        self._gate = threading.Lock()

    # 실전 연결의 토큰 파일과 섞이지 않게 따로 둠
    def _token_path(self):
        return os.getenv("KIS_PAPER_TOKEN_FILE", "").strip()

    def _saved(self):
        path = self._token_path()
        if not path:
            return None
        try:
            kept = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if kept.get("key") != self.key or not kept.get("token") or time.time() >= float(kept.get("expires", 0)):
            return None
        return kept

    def _keep(self):
        path = self._token_path()
        if not path:
            return
        try:
            Path(path).write_text(json.dumps({"key": self.key, "mode": "demo", "token": self.token, "expires": self.expires}),
                                  encoding="utf-8")
            os.chmod(path, 0o600)
        except OSError:
            pass

    @classmethod
    def _wait_turn(cls):
        # 모의투자는 초당 호출 한도가 낮음(약 2번) → 0.6초 간격
        time.sleep(float(os.getenv("KIS_PAPER_CALL_GAP", "0.6")))

    def order(self, code, side, qty):
        """시장가 현금 주문. side = 'buy' | 'sell'. 주문 번호를 돌려줌."""
        if self.base != PAPER_BASE or self.mode != "demo":
            raise broker_kis.BrokerError("모의투자 주소가 아니어서 주문하지 않았습니다.")
        if side not in ("buy", "sell") or not re.fullmatch(r"[0-9A-Z]{6}", str(code)) or int(qty) < 1:
            raise broker_kis.BrokerError("주문 내용이 올바르지 않아 넣지 않았습니다.")
        self.authorize()
        _, data = self.request("POST", ORDER_PATH, headers={
            "authorization": "Bearer " + self.token, "appkey": self.key, "appsecret": self.secret,
            "tr_id": TR_BUY if side == "buy" else TR_SELL, "custtype": "P", "content-type": "application/json; charset=utf-8"},
            json={"CANO": self.cano, "ACNT_PRDT_CD": self.product, "PDNO": str(code), "ORD_DVSN": "01",
                  "ORD_QTY": str(int(qty)), "ORD_UNPR": "0"})
        if str(data.get("rt_cd")) != "0":
            msg = str(data.get("msg_cd") or "").strip()
            msg = msg if re.fullmatch(r"[A-Z0-9]{4,10}", msg) else ""
            raise broker_kis.BrokerError("모의투자 주문이 거절되었습니다" + (f" · {msg}" if msg else "") + ".")
        out = data.get("output") or {}
        no = str(out.get("ODNO") or "").strip()
        return no if re.fullmatch(r"[0-9]{1,12}", no) else ""


def enabled():
    if os.getenv("PAPER_TRADING", "").strip().lower() != "on":
        return False, "PAPER_TRADING이 on이 아니라 모의투자 주문을 넣지 않습니다."
    if OFF.exists():
        return False, "끄기 파일(hourly-live/paper-off)이 있어 모의투자 주문을 넣지 않습니다."
    if not os.getenv("KIS_PAPER_APP_KEY", "").strip():
        return False, "모의투자 키가 아직 없어 주문을 넣지 않습니다."
    return True, ""


def plan_orders(done, state, balance, prices, bar_id):
    """fill이 체결한 매매(done) → 넣을 주문 [(열쇠, 종목, 'buy'|'sell', 수량, 까닭)]. 계산만(주문은 안 넣음).

    살 때: 계좌 총액 × 칸 / 10 ÷ 체결 값(그 봉 시가) 내림 · 현금 안에서.
    팔 때: 연습 계좌에서 그 종목이 다 팔렸으면 모의 잔고 전부, 일부(절반 익절)면 잔고 × 판 칸 / (판 칸 + 남은 칸) 반올림.
    """
    held = {p["code"]: int(p["quantity"]) for p in balance.get("positions", [])}
    cash = float(balance.get("cash") or 0)
    total = cash + float(balance.get("value") or 0)
    left = cash * 0.98                        # 시장가 체결 값이 조금 높을 때를 위한 여유
    out = []
    for x in done:
        key = f"{bar_id}:{x['type']}:{x['code']}:{x.get('decided', '')}"
        if x["type"] == "sell":
            have = held.get(x["code"], 0)
            if have <= 0:
                continue
            remain = (state.get("positions", {}).get(x["code"]) or {}).get("칸", 0)
            qty = have if remain <= 0 else max(1, round(have * x["칸"] / (x["칸"] + remain)))
            out.append((key, x["code"], "sell", min(qty, have), x.get("why", "")))
    for x in done:
        key = f"{bar_id}:{x['type']}:{x['code']}:{x.get('decided', '')}"
        if x["type"] != "buy":
            continue
        price = prices.get(x["code"])
        if not price or price <= 0:
            continue
        money = min(total * x["칸"] / SLOTS, left)
        qty = math.floor(money / price)
        if qty < 1:
            continue
        left -= qty * price
        out.append((key, x["code"], "buy", qty, x.get("kind", "")))
    return out


def execute(done, state, prices, bar_id, broker=None, now=None):
    """체결된 매매를 모의투자 주문으로 넣고 주문 장부에 적음. 디스코드에 보낼 줄들을 돌려줌."""
    ok, why = enabled()
    if not done:
        return []
    if not ok:
        print(why)
        return []
    now = now or datetime.now(KST)
    try:
        broker = broker or PaperBroker()
        balance = broker.balance()
    except broker_kis.BrokerError as e:
        print("모의투자 연결 · 잔고 조회 실패 ·", e)
        return [f"🧪 모의투자 주문 못 넣음 · {e}"]
    book = json.loads(BOOK.read_text(encoding="utf-8")) if BOOK.exists() else {"orders": []}
    seen = {o["key"] for o in book["orders"]}
    names = {p["code"]: p.get("name") for p in state.get("positions", {}).values()}
    lines = []
    planned = plan_orders(done, state, balance, prices, bar_id)
    # 주문을 못 넣는 매매도 알림에 남김(사용자 요청: 진입 · 청산은 모두 알림)
    have = {p["code"] for p in balance.get("positions", []) if int(p.get("quantity") or 0) > 0}
    for x in done:
        if any(code == x["code"] and side == x["type"] for _, code, side, _, _ in planned):
            continue
        name = x.get("name") or names.get(x["code"]) or x["code"]
        if x["type"] == "sell":
            why = "모의 계좌에 그 종목이 없음" if x["code"] not in have else "팔 수량이 0주"
        else:
            why = "시가를 몰라서" if not prices.get(x["code"]) else "살 돈이 모자람(1주 미만)"
        lines.append(f"🧪 모의투자 {'매수' if x['type'] == 'buy' else '매도'} 건너뜀 · {name}({x['code']}) · {why}")
    for key, code, side, qty, why in planned:
        if key in seen:
            continue
        name = names.get(code) or next((x.get("name") for x in done if x["code"] == code), code)
        try:
            no = broker.order(code, side, qty)
            status = "접수"
        except broker_kis.BrokerError as e:
            no, status = "", f"실패 · {e}"
        book["orders"].append({"key": key, "at": now.strftime("%Y-%m-%d %H:%M"), "code": code, "name": name,
                               "side": side, "qty": qty, "status": status, "order_no": no})
        lines.append(f"🧪 모의투자 {'매수' if side == 'buy' else '매도'} · {name}({code}) {qty}주 · 시장가 · {status}")
    book["orders"] = book["orders"][-1000:]
    BOOK.parent.mkdir(parents=True, exist_ok=True)
    BOOK.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
    return lines
