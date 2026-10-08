"""COST-REPLAY-0001 비용 모듈 연구 복사본 — research/perf2.py 비용 함수만 옮겨 날짜 · 상품 · 시장 세금 계약으로 바꿈.
운영 · 기존 import 경로는 그대로(이 파일은 결과 폴더 안에서만 씀). 표준 라이브러리만.

- old_*: perf2.py 그대로(연도표 + 그 밖의 해 0.0015 기본값). 재현 대조용.
- sell_tax_rate: 날짜 구간 계약. 모르는 상품 · 시장 · 기간은 UnknownTax(자동 기본값 없음).
- 수수료 0.015% · 미끄러짐 0.05% · 충격 0.10 × √(주문 ÷ 앞 20일 평균 거래대금)은 검증 전 가정값(바꾸지 않음).
"""
import json
import math
import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(os.environ.get("COST_REPLAY_ROOT", Path(__file__).resolve().parents[3]))
FEE = 0.00015
SLIP = 0.0005
IMPACT_K = 0.10
SCALES = {"BASE": 1.0, "STRESS": 1.5, "EXTREME": 2.0}   # 기존 계약 재현용. 세금 배율은 가상 스트레스


class UnknownTax(ValueError):
    """과세 계약이 증명되지 않은 상품 · 시장 · 기간."""


# 일반 KOSDAQ 주식 · 일반 시장매도(TASK 고정 · 시행령 제29788 · 31290 · 33209 · 36001호)
KOSDAQ_STOCK = (("20170101", "20190602", 0.0030), ("20190603", "20201231", 0.0025), ("20210101", "20221231", 0.0023),
                ("20230101", "20231231", 0.0020), ("20240101", "20241231", 0.0018), ("20250101", "20251231", 0.0015),
                ("20260101", "20261008", 0.0020))
# 일반 KOSPI 주식: 2026 합계만 근거(한국투자증권 현재 표 0.05% + 농특세 0.15%). 나머지 기간은 UNKNOWN
KOSPI_STOCK = (("20260101", "20261008", 0.0020),)
# 명시적 가정 시나리오: KOSPI 거래세(시행령 개정이유) + 농특세 0.0015 가정 — 공식 사실 아님
KOSPI_STT = (("20170101", "20190602", 0.0015), ("20190603", "20201231", 0.0010), ("20210101", "20221231", 0.0008),
             ("20230101", "20231231", 0.0005), ("20240101", "20241231", 0.0003), ("20250101", "20251231", 0.0),
             ("20260101", "20261008", 0.0005))
FARM_ASSUMED = 0.0015
SCENARIOS = ("STRICT", "S_KOSPI_FARM015")


def _day(d):
    s = str(d).replace("-", "")
    if len(s) != 8 or not s.isdigit():
        raise UnknownTax(f"날짜 형식: {d!r}")
    return s


def _lookup(table, day):
    for lo, hi, r in table:
        if lo <= day <= hi:
            return r
    return None


def sell_tax_rate(day, instrument_type, market, scenario="STRICT"):
    """매도금액 대비 세율. 매수에는 쓰지 않음(buy_tax_rate = 0)."""
    day = _day(day)
    if scenario not in SCENARIOS:
        raise UnknownTax(f"시나리오: {scenario!r}")
    if instrument_type != "STOCK":
        raise UnknownTax(f"상품 {instrument_type!r}: 이 표 적용 금지(ETF · ETN · 인버스 · 기타)")
    if market == "KOSDAQ":
        r = _lookup(KOSDAQ_STOCK, day)
    elif market == "KOSPI":
        r = _lookup(KOSPI_STOCK, day)
        if r is None and scenario == "S_KOSPI_FARM015":
            stt = _lookup(KOSPI_STT, day)
            r = None if stt is None else stt + FARM_ASSUMED
    else:
        raise UnknownTax(f"시장 {market!r}")
    if r is None:
        raise UnknownTax(f"{market} {day} 계약 없음({scenario})")
    return r


def buy_tax_rate(day, instrument_type, market):
    _day(day)
    return 0.0


def sell_tax_amount(quantity, price, day, instrument_type, market, scenario="STRICT"):
    """체결 1건의 매도 세금(원, 소수 그대로 · 원 미만 처리 규칙은 검증하지 못함)."""
    if quantity <= 0 or price <= 0:
        raise ValueError("수량 · 가격은 양수")
    return quantity * price * sell_tax_rate(day, instrument_type, market, scenario)


# ── perf2.py 그대로 옮긴 부분(old) ──
OLD_TAX = {2017: .0025, 2018: .0025, 2019: .0025, 2020: .0025, 2021: .0025, 2022: .0025, 2023: .0020, 2024: .0018}


def old_tax(day):
    return OLD_TAX.get(int(str(day)[:4]), .0015)


@lru_cache(maxsize=None)
def adv_series(code):
    """앞 20일 평균 거래대금(원) — 그날은 빼고 전날까지. perf2.adv_series와 같은 계산(pandas 없이)."""
    p = ROOT / "volume-data" / f"{code}.json"
    if not p.exists():
        return ()
    rows = json.loads(p.read_text(encoding="utf-8")).get("날") or []
    d = {}
    for r in rows:
        if len(r) > 2 and r[2]:
            d[str(r[0])] = float(r[2])
    keys = sorted(d)
    vals = [d[k] for k in keys]
    out = []
    for i, k in enumerate(keys):
        # rolling(20, min_periods=10).mean().shift(1): i번째 값 = i-1까지 최근 20개(10개 이상)
        w = vals[max(0, i - 20):i]
        v = sum(w) / len(w) if i >= 1 and len(w) >= 10 else math.nan
        out.append((k, v))
    return tuple(out)


def impact(code, day, notional):
    a = adv_series(code)
    day = str(day)
    v = math.nan
    if a:
        m = dict(a)
        v = m.get(day, math.nan) if day in m else math.nan
        if not (v == v) or v <= 0:
            prev = [x for k, x in a if k <= day]
            v = prev[-1] if prev else math.nan
    if not (v == v) or v <= 0:
        return 0.002 if IMPACT_K else 0.0
    return IMPACT_K * math.sqrt(notional / v)


def old_side_costs(code, buy_day, sell_day, notional, scale=1.0):
    b = FEE + SLIP + impact(code, buy_day, notional)
    s = FEE + SLIP + old_tax(sell_day) + impact(code, sell_day, notional)
    return b * scale, s * scale


def corrected_side_costs(code, buy_day, sell_day, notional, market, scale=1.0, instrument_type="STOCK", scenario="STRICT"):
    """old와 모두 같고 매도 세금만 계약값. 세금도 scale을 곱함(기존 계약 재현 · 가상 스트레스)."""
    b = FEE + SLIP + buy_tax_rate(buy_day, instrument_type, market) + impact(code, buy_day, notional)
    s = FEE + SLIP + sell_tax_rate(sell_day, instrument_type, market, scenario) + impact(code, sell_day, notional)
    return b * scale, s * scale


def recost_row(pnl_pct_engine, cb, cs):
    """RULES-0002 z058.recost와 같은 식: 엔진 왕복 0.25%를 되돌린 비용 전 손익에 새 비용을 뺌(%)."""
    g = (1 + pnl_pct_engine / 100) / (1 - 0.0025) - 1
    return ((1 + g) * (1 - cb) * (1 - cs) - 1) * 100
