"""MPOS-0017 round 2(GPT #442 고칠 것): 주차를 엔진(z100 바탕)이 아니라 **덧붙임 계좌의 최종 잔여 현금**에만 붙임.
regime_dev.account 소스를 그대로 가져와 세 곳만 덧댐(텍스트 치환 · 각 1번 · 원판 재현 assert):
① 날 수익 단계: 전날 끝 주차액 P × (153130 오늘 종가 / 전날 종가 − 1)을 현금에 더함(두 날 모두 153130 값이 있을 때만 · 없으면 0 · 셈).
② round 2(GPT #442): 날 수익 때 주차 평가액도 갱신(가격 변동은 거래 아님) · 원판 '1일봉 줄여 빚 0' 단계 **앞에서** 주차를 맞춤:
   목표 = 비용 뒤 남는 잔여 현금(slack = 현금 + 1일봉 몫 × 바탕 현금 비중) · 실제 사고판 금액 × 0.065%만 비용 · 비용이 잔여를 넘으면 원판 빚 0 단계가 메움 ·
   날 끝 slack 점검(비용 뒤) + 주차액 ≤ 최종 잔여 점검. 첫 날 주차 0 · 마지막 날은 평가액(정리 비용 없음).
③ MODE: OFF(원판과 NAV가 날마다 같아야 함) · PARK · ZERO(153130 수익 0 · 비용만 · 기전 대조) · 독 시험(POISON 날 뒤 153130 값 × 0.9)."""
import inspect
import json
import sys
from pathlib import Path

M12 = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/r8/research-exchange/claude-to-gpt/MPOS-0012")
sys.path.insert(0, str(M12))
import mpos12 as M  # noqa: E402

Dv = M.Dv
BOND_PATH = M.TREE / "etf-data/153130.json"
ETF_SIDE = 0.00065
S = {"mode": "OFF", "poison": "", "P": 0.0, "gain": 0.0, "cost": 0.0, "traded": 0.0, "over": -1e9, "miss": 0, "days": 0, "bond": {}}


def _bond():
    b = {d: float(x) for d, x in json.load(open(BOND_PATH))["closes"]}
    return b


def park_gain(p, d):
    """날 수익: 전날 끝 주차 평가액 P에 153130 그날 수익을 붙임 → 현금(주차 포함)에 더하고 P도 평가값으로 갱신(거래 아님 · 비용 없음)."""
    if S["mode"] == "OFF":
        return 0.0
    S["days"] += 1
    b = S["bond"]
    if p not in b or d not in b:
        S["miss"] += 1
        return 0.0
    bp, bd = b[p], b[d]
    if S["poison"] and d > S["poison"]:
        bd *= 0.9
        if p > S["poison"]:
            bp *= 0.9
    r = 0.0 if S["mode"] == "ZERO" else bd / bp - 1
    g = S["P"] * r
    S["P"] += g
    S["gain"] += g
    return g


def park_trade(slack_pre):
    """주차 맞춤(GPT #442 round 2): 목표 T = 비용 뒤 남는 잔여액(T + 비용 ≤ slack · 실제 사고판 금액 |T − P_평가|에만 비용).
    사기: T = (slack + f·P)/(1 + f) · 팔기: T = (slack − f·P)/(1 − f) · 0 아래면 T = 0(전액 해제 · 비용이 잔여를 넘으면 원판의 '1일봉 줄여 빚 0' 단계가 메움).
    돌려줌: 비용(현금에서 뺌)."""
    if S["mode"] == "OFF":
        return 0.0
    f, P = ETF_SIDE, S["P"]
    slack_pre = max(0.0, slack_pre)
    if slack_pre >= P:
        T = (slack_pre + f * P) / (1 + f)
    else:
        T = max(0.0, (slack_pre - f * P) / (1 - f))
    c = abs(T - P) * f
    S["traded"] += abs(T - P)
    S["cost"] += c
    S["P"] = T
    return c


def park_check(slack_post):
    """날 끝 점검: 주차액 ≤ 비용 뒤 최종 잔여(slack) · 넘친 최대값 기록."""
    if S["mode"] != "OFF":
        S["over"] = max(S["over"], S["P"] - slack_post)


SRC = inspect.getsource(Dv.account)
PATCH = [
    ("        A = vb + ve + cash\n        # 바꿈", "        cash += park_gain(p, d)\n        A = vb + ve + cash\n        # 바꿈"),
    ("        if cash < -vb * base[d][1] - 1e-12:\n            # ETF를 다 팔아도 모자람",
     "        cash -= park_trade(cash + vb * base[d][1])            # 주차 맞춤 비용을 빚 없음 단계 앞에서 뺌\n        if cash < -vb * base[d][1] - 1e-12:\n            # ETF를 다 팔아도 모자람"),
    ("        slack[0] = min(slack[0], cash + vb * base[d][1])      # 빚 없음 점검: 늘 ≥ 0이어야 함\n",
     "        slack[0] = min(slack[0], cash + vb * base[d][1])      # 빚 없음 점검: 늘 ≥ 0이어야 함\n        park_check(cash + vb * base[d][1])\n"),
    ("def account(cfg, lo=LO, hi=HI):", "def account_park(cfg, lo=LO, hi=HI):"),
]
src = SRC
for a, b in PATCH:
    assert src.count(a) == 1, a[:60]
    src = src.replace(a, b)
ns = Dv.__dict__
ns["park_gain"], ns["park_trade"], ns["park_check"] = park_gain, park_trade, park_check
exec(compile(src, "account_park", "exec"), ns)


def run_park(base_csv, mode, poison=""):
    S.update(mode=mode, poison=poison, P=0.0, gain=0.0, cost=0.0, traded=0.0, over=-1e9, miss=0, days=0, bond=_bond())
    Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(base_csv), None, None
    navs, _ = ns["account_park"](M.CFG)
    info = {k: S[k] for k in ("gain", "cost", "traded", "over", "miss", "days")}
    info["base_trims"] = Dv.account.base_trims
    info["min_slack"] = Dv.account.min_slack            # 덧댄 소스도 원판 이름(account)에 점검값을 적음
    return navs, info
