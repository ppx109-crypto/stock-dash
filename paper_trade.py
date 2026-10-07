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
BOOK = Path("hourly-live/paper-orders.json")              # 1시간봉(1시간봉 규칙) 주문 장부
DAILY_BOOK = Path("daily-live/paper-orders.json")        # 일봉(1일봉 규칙) 주문 장부
M15_BOOK = Path("m15-live/paper-orders.json")            # 15분봉(15분봉 22회차 후보) 주문 장부
IDLE_BOOK = Path("idle-live/paper-orders.json")          # 빈칸 엔진 · 코스닥 과열 인버스 주문 장부(idle_live.py · 2026-10-03)
IDLE_STATE = Path("idle-live/state.json")                # 빈칸 엔진이 들고 있는 것(종류 · 산 값 · 지난 날)
BASKET_BOOK = Path("basket-live/paper-orders.json")      # 사건 바구니 C 주문 장부(basket_live.py · 2026-10-07)
BASKET_STATE = Path("basket-live/state.json")
LABEL = {"1h": "1시간봉 매수 후보", "1d": "1일봉 매수 후보", "15m": "15분봉 매수 후보", "idle": "빈칸 엔진"}
# 모의 계좌 하나를 규칙들이 나눠 씀. 규칙마다 계좌 총액의 그 몫을 제 돈으로 보고 칸을 셈 · 팔 때는 그 규칙이 산 수량(장부의 held)만 팖.
# 2026-10-03 최종 조합(사용자 "최고의 조합 재검토 후 배포"): 1일봉 50 · 15분봉 50 · 1시간봉 0(알림만) + 빈칸 엔진 · 코스닥 과열 인버스는 남는 돈.
#   근거(1년 한투 장부 · 엔진 붙임 · 앞 반 / 뒤 반): 50 · 0 · 50 = +58 · −3.4 / +608 · −8.4 vs 이전 40 · 40 · 20 = +41 · −4.3 / +314 · −8.9
#   (한투 1시간봉은 1년 연 +43 · 골 −12로 약함 · docs/RL-INVERSE-LOG.md '모의투자 최종 조합').
SHARES = {"1h": float(os.getenv("PAPER_SHARE_1H", "0.0")), "1d": float(os.getenv("PAPER_SHARE_1D", "0.5")),
          "15m": float(os.getenv("PAPER_SHARE_15M", "0.5"))}
SHARE = SHARES["1h"]
OFF = Path("hourly-live/paper-off")
SLOTS = 10
# 모의투자 주문 거래 ID(현금 매수 · 매도). 한투가 바꾸면 환경변수로 덮어씀.
TR_BUY = os.getenv("KIS_PAPER_TR_BUY", "VTTC0012U")
TR_SELL = os.getenv("KIS_PAPER_TR_SELL", "VTTC0011U")
# 매수가능조회(시장가로 지금 몇 주까지 살 수 있나) — 시장가 매수는 한투가 상한가 언저리 값으로 돈을 묶어서,
# 계좌 돈에 꽉 맞춘 수량은 거절됨(2026-10-06 빈칸 엔진 인버스 45,539주 · 약 9,700만 원 → 40250000). 주문 전에 물어 수량을 맞춤.
TR_BUYABLE = os.getenv("KIS_PAPER_TR_BUYABLE", "VTTC8908R")
BUYABLE_PATH = "/uapi/domestic-stock/v1/trading/inquire-psbl-order"
# 시장가 매수가 묶는 돈 ÷ 실제 값(확인: 1억 → 251340 2,130원 34,608주 = 1.357배). 자리 내주기를 정할 때 씀.
MKT_MARGIN = float(os.getenv("PAPER_MKT_MARGIN", "1.36"))


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
        try:            # 깨진 파일이면 새로 받음
            if not isinstance(kept, dict) or kept.get("key") != self.key or not kept.get("token") \
                    or time.time() >= float(kept.get("expires", 0)):
                return None
        except (TypeError, ValueError):
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

    def balance(self):
        """모의 계좌 잔고. 'cash'는 D+2 예수금(오늘 사고판 것까지 반영)으로 바꿔 줌 — 오늘 예수금(dnca_tot_amt)은 이틀 뒤에야 바뀌어,
        산 날엔 같은 돈을 두 번 세고(현금 그대로 + 평가에도) 판 날엔 판 돈이 빠졌음(2026-10-06 검토). 받은 값이 없으면 예전 그대로."""
        b = super().balance()
        b["cash_today"] = b.get("cash")
        if b.get("cash_d2") is not None:
            b["cash"] = b["cash_d2"]
        return b

    def buyable(self, code):
        """시장가로 지금 살 수 있는 수량(미수 없이). 물어보지 못하면 None(그때는 원래 수량 그대로 주문)."""
        try:
            self.authorize()
            _, data = self.request("GET", BUYABLE_PATH, headers={
                "authorization": "Bearer " + self.token, "appkey": self.key, "appsecret": self.secret,
                "tr_id": TR_BUYABLE, "custtype": "P"},
                params={"CANO": self.cano, "ACNT_PRDT_CD": self.product, "PDNO": str(code), "ORD_UNPR": "",
                        "ORD_DVSN": "01", "CMA_EVLU_AMT_ICLD_YN": "N", "OVRS_ICLD_YN": "N"})
        except broker_kis.BrokerError:
            return None
        if str(data.get("rt_cd")) != "0":
            return None
        out = data.get("output") or {}
        for k in ("nrcvb_buy_qty", "max_buy_qty"):
            try:
                return max(0, int(float(str(out.get(k)).replace(",", ""))))
            except (TypeError, ValueError):
                continue
        return None

    def order(self, code, side, qty):
        """시장가 현금 주문. side = 'buy' | 'sell'. 주문 번호를 돌려줌.
        살 때는 먼저 매수가능 수량을 물어 그보다 많으면 줄임 — 실제로 넣은 수량은 self.last_qty(부르는 쪽이 장부에 씀)."""
        if self.base != PAPER_BASE or self.mode != "demo":
            raise broker_kis.BrokerError("모의투자 주소가 아니어서 주문하지 않았습니다.")
        if side not in ("buy", "sell") or not re.fullmatch(r"[0-9A-Z]{6}", str(code)) or int(qty) < 1:
            raise broker_kis.BrokerError("주문 내용이 올바르지 않아 넣지 않았습니다.")
        qty = int(qty)
        if side == "buy":
            can = self.buyable(code)
            if can is not None and can < qty:
                if can < 1:
                    raise broker_kis.BrokerError("살 수 있는 수량이 0주라 넣지 않았습니다(시장가 매수가능 조회).")
                qty = can
        self.last_qty = qty
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


def enabled(now=None):
    if os.getenv("PAPER_TRADING", "").strip().lower() != "on":
        return False, "PAPER_TRADING이 on이 아니라 모의투자 주문을 넣지 않습니다."
    start = os.getenv("PAPER_START", "").strip()           # 이 날(YYYYMMDD)부터 주문(사용자 결정 2026-10-01: 내일부터)
    today = (now or datetime.now(KST)).strftime("%Y%m%d")
    if start and today < start:
        return False, f"모의투자는 {start[:4]}-{start[4:6]}-{start[6:]}부터 시작해 오늘은 주문을 넣지 않습니다."
    if OFF.exists():
        return False, "끄기 파일(hourly-live/paper-off)이 있어 모의투자 주문을 넣지 않습니다."
    if not os.getenv("KIS_PAPER_APP_KEY", "").strip():
        return False, "모의투자 키가 아직 없어 주문을 넣지 않습니다."
    return True, ""


def sync_repo():
    """작업이 기다리는 동안(14:40 → 15:10 · 15:20) 다른 작업(장중 상주)이 올린 기록을 받아 맞춤 — 낡은 장부로 판단 · 저장하다
    부딪히지 않게(2026-10-06 감시자 검토). LIVE_GIT_SYNC=1인 작업에서만. 실패하면 합치기를 되돌리고 False."""
    if os.getenv("LIVE_GIT_SYNC") != "1":
        return True
    import subprocess
    for _ in range(2):
        try:                                       # 멈추거나 실패해도 봇은 있는 기록으로 계속(죽지 않게)
            if subprocess.run("git pull -q --rebase origin main", shell=True, timeout=60).returncode == 0:
                return True
        except (subprocess.TimeoutExpired, OSError):
            pass
        try:
            subprocess.run("git rebase --abort", shell=True, stderr=subprocess.DEVNULL, timeout=30)
        except (subprocess.TimeoutExpired, OSError):
            pass
        time.sleep(3)
    print("저장소를 최신으로 맞추지 못함(있는 기록으로 계속)")
    return False


def daily_reserve(day, total, prices, near_files=(Path("m15-live/near-now.json"), Path("hourly-live/near-now.json"))):
    """15:20 1일봉이 살 몫(원) — 빈칸 엔진이 15:10에 비켜 둘 돈(2026-10-06 감시자 검토).
    15:20은 마감 동시호가라 그때 엔진을 팔아도 15:30에야 체결돼 1일봉이 살 돈이 안 풀림 → 엔진이 미리 남겨 둠.
    장중 15분마다 그 시각 값으로 다시 센 '1일봉 후보(지금 값이면)'(near-now.json의 picks_daily · 오늘 것 중 가장 늦은 판정)가
    있으면 후보마다 4칸(1일봉 최대 크기)으로 보고, 1일봉 몫 가운데 아직 안 쓴 만큼까지. 판정은 15:10 전 값만 씀(미래 참조 없음)."""
    try:
        return _daily_reserve(day, total, prices, near_files)
    except Exception as e:                          # 파일 모양이 이상해도 엔진이 하루를 통째로 쉬지 않게(비켜 두기만 못 함)
        print("1일봉 몫 셈 실패 ·", type(e).__name__)
        return 0.0, ""


def _daily_reserve(day, total, prices, near_files):
    got = []
    for f in near_files:
        try:
            body = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        # 오늘 것 · 14:30 뒤 판정만(그 뒤 실행이 다 실패했으면 아침 판정으로 비켜 두지 않게)
        if isinstance(body, dict) and str(body.get("date")) == day and str(body.get("at"))[11:16] >= "14:30":
            got.append(body)
    if not got:
        return 0.0, ""
    last = max(got, key=lambda b: str(b.get("at")))
    picks = [p for p in (last.get("picks_daily") or []) if isinstance(p, dict)]
    if not picks:
        return 0.0, ""
    share = total * SHARES["1d"]
    try:
        book = json.loads(DAILY_BOOK.read_text(encoding="utf-8")) if DAILY_BOOK.exists() else {}
    except (OSError, ValueError):
        book = {}
    held = sum(int(q) * float(prices.get(c) or 0) for c, q in (book.get("held") or {}).items())
    want = min(len(picks) * 4 / SLOTS, 1.0) * share
    reserve = max(0.0, min(want, share - held))
    names = " · ".join(str(p.get("name") or p.get("code")) for p in picks[:3])
    return reserve, f"1일봉 후보({names} · {str(last.get('at'))[11:16]} 판정) 몫 약 {reserve / 1e4:,.0f}만 원을 비켜 둠"


def book_path(strategy="1h"):
    return {"1h": BOOK, "1d": DAILY_BOOK, "15m": M15_BOOK, "idle": IDLE_BOOK}[strategy]


def make_room(broker, balance, need, now):
    """규칙(1일봉 · 1시간봉 · 15분봉)이 살 돈(need)이 현금보다 많으면 남는 돈을 굴리던 것을 팔아 자리를 내줌.
    차례: 빈칸 엔진 것을 모두 → 그래도 모자라면 사건 바구니 것을 오래된 것부터 모자란 만큼(2026-10-07 · 연구 P4b: 규칙 > 바구니 > 엔진).
    '규칙이 안 쓰는 돈'만 굴린다는 연구 규칙(규칙이 먼저)을 실제 계좌에서 지키는 장치(2026-10-03).
    돌려줌: (새 잔고, 알림 줄들). 팔 게 없거나 현금이 넉넉하면 그대로."""
    balance, lines = _give_room(broker, balance, need, now, IDLE_BOOK, IDLE_STATE, "빈칸 엔진", partial=False)
    balance, more = _give_room(broker, balance, need, now, BASKET_BOOK, BASKET_STATE, "사건 바구니", partial=True)
    return balance, lines + more


def _give_room(broker, balance, need, now, book_file, state_file, label, partial):
    cash = float(balance.get("cash") or 0)
    book = json.loads(book_file.read_text(encoding="utf-8")) if book_file.exists() else {"orders": [], "held": {}}
    held = {c: int(q) for c, q in (book.get("held") or {}).items() if int(q) > 0}
    # 시장가 매수는 실제 값의 약 1.36배를 묶으므로 그만큼 있어야 다 삼(2026-10-06 검토 — 예전엔 1배로 봐서 엔진이 안 비키고 규칙 매수가 잘림)
    if need * MKT_MARGIN <= cash * 0.98 or not held:
        return balance, []
    account = {p["code"]: int(p["quantity"]) for p in balance.get("positions", [])}
    price = {p["code"]: float(p.get("price") or 0) for p in balance.get("positions", [])}
    st = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    order = sorted(held, key=lambda c: (str((st.get("positions", {}).get(c) or {}).get("day", "")), c))
    lines, sold, est = [], False, cash
    for code in order:
        if partial and sold and need * MKT_MARGIN <= est * 0.98:
            break
        qty = min(held[code], account.get(code, 0))
        if qty < 1:
            book["held"].pop(code, None)
            continue
        try:
            no = broker.order(code, "sell", qty)
            status = "접수"
            book["held"].pop(code, None)
            sold = True
            est += qty * price.get(code, 0)
        except broker_kis.BrokerError as e:
            no, status = "", f"실패 · {e}"
        book.setdefault("orders", []).append({"key": f"{now.strftime('%Y%m%d%H%M')}:room:{code}", "at": now.strftime("%Y-%m-%d %H:%M"),
                                              "code": code, "side": "sell", "qty": qty, "status": status, "order_no": no,
                                              "why": "규칙이 살 돈이 모자라 자리 내줌"})
        lines.append(f"🧪 모의투자({label}) 매도 · {code} {qty}주 · 규칙에 자리 내줌 · {status}")
    book_file.parent.mkdir(parents=True, exist_ok=True)
    book_file.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
    if sold and state_file.exists():
        for code in list(st.get("positions", {})):
            if code not in book["held"]:
                st["positions"].pop(code)
        state_file.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    if sold:
        time.sleep(float(os.getenv("PAPER_ROOM_WAIT", "2")))
        try:
            balance = broker.balance()
        except broker_kis.BrokerError:
            pass
    return balance, lines


def plan_orders(done, state, balance, prices, bar_id, held=None, share=1.0):
    """fill이 체결한 매매(done) → 넣을 주문 [(열쇠, 종목, 'buy'|'sell', 수량, 까닭)]. 계산만(주문은 안 넣음).

    살 때: 계좌 총액 × 칸 / 10 ÷ 체결 값(그 봉 시가) 내림 · 현금 안에서.
    팔 때: 연습 계좌에서 그 종목이 다 팔렸으면 모의 잔고 전부, 일부(절반 익절)면 잔고 × 판 칸 / (판 칸 + 남은 칸) 반올림.
    """
    account = {p["code"]: int(p["quantity"]) for p in balance.get("positions", [])}
    # 규칙 장부(held)가 있으면 그 규칙이 산 수량까지만 팖(다른 규칙이 같은 종목을 들고 있어도 건드리지 않음)
    held = account if held is None else {c: min(int(q), account.get(c, 0)) for c, q in held.items()}
    cash = float(balance.get("cash") or 0)
    total = (cash + float(balance.get("value") or 0)) * share
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
    # 같은 차례에 먼저 파는 것의 돈도 살 돈에 셈(파는 주문이 먼저 나감 · 2026-10-06 검토). 시장가 체결 값이 조금 높을 때를 위해 98%.
    freed = sum(q * float(prices.get(c) or 0) for _, c, side, q, _ in out if side == "sell")
    left = (cash + freed) * 0.98
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


def execute(done, state, prices, bar_id, broker=None, now=None, strategy="1h"):
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
        return [f"🧪 모의투자({LABEL.get(strategy, strategy)}) 주문 못 넣음 · {e}"]
    path = book_path(strategy)
    tag = LABEL.get(strategy, strategy)
    book = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"orders": []}
    book.setdefault("held", {})
    seen = {o["key"] for o in book["orders"]}
    names = {p["code"]: p.get("name") for p in state.get("positions", {}).values()}
    lines = []
    if strategy in SHARES:               # 규칙이 살 돈이 모자라면 빈칸 엔진이 먼저 자리를 내줌
        total = (float(balance.get("cash") or 0) + float(balance.get("value") or 0)) * SHARES[strategy]
        need = sum(total * x["칸"] / SLOTS for x in done if x["type"] == "buy" and prices.get(x["code"]))
        balance, room = make_room(broker, balance, need, now)
        lines += room
    planned = plan_orders(done, state, balance, prices, bar_id, held=book["held"], share=SHARES[strategy])
    # 주문을 못 넣는 매매도 알림에 남김(사용자 요청: 진입 · 청산은 모두 알림)
    have = {c for c, q in book["held"].items() if q > 0}
    for x in done:
        if any(code == x["code"] and side == x["type"] for _, code, side, _, _ in planned):
            continue
        name = x.get("name") or names.get(x["code"]) or x["code"]
        if x["type"] == "sell":
            why = "이 규칙이 모의 계좌에서 산 수량이 없음" if x["code"] not in have else "팔 수량이 0주"
        else:
            why = "시가를 몰라서" if not prices.get(x["code"]) else "살 돈이 모자람(1주 미만)"
        lines.append(f"🧪 모의투자({tag}) {'매수' if x['type'] == 'buy' else '매도'} 건너뜀 · {name}({x['code']}) · {why}")
    for key, code, side, qty, why in planned:
        if key in seen:
            continue
        name = names.get(code) or next((x.get("name") for x in done if x["code"] == code), code)
        try:
            want = qty
            no = broker.order(code, side, qty)
            qty = int(getattr(broker, "last_qty", qty) or qty)       # 매수가능 수량에 맞춰 줄었으면 그 수량
            status = "접수" if qty == want else f"접수 · {want}주 중 살 수 있는 {qty}주로 줄임"
            book["held"][code] = max(0, book["held"].get(code, 0) + (qty if side == "buy" else -qty))
            if not book["held"][code]:
                del book["held"][code]
        except broker_kis.BrokerError as e:
            no, status = "", f"실패 · {e}"
        book["orders"].append({"key": key, "at": now.strftime("%Y-%m-%d %H:%M"), "code": code, "name": name,
                               "side": side, "qty": qty, "status": status, "order_no": no})
        lines.append(f"🧪 모의투자({tag}) {'매수' if side == 'buy' else '매도'} · {name}({code}) {qty}주 · 시장가 · {status}")
    book["orders"] = book["orders"][-5000:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
    return lines
