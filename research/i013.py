"""I 13회차 — 약세장 돌리기(i011)를 1일봉 규칙(새 82)의 쉬는 돈으로 함께 굴림(B · C · C를 2021 ~ 2025 · 2026으로도 나눔).
1일봉 손익 · 비운 몫: i005와 같음(x008_d1.json). 돌리기 몫 = 그날 비운 몫 × 돌리기 수익(켜는 때 = 시장 폭 < 50 등).
환경변수: I_CANDS(쉼표 · 기본 나스닥 · 달러 · 금 · 채권) · I_L(기본 60) · I_TOP(기본 1) · I_GATE(weak · always · ma200)
  · I_W(비운 돈 가운데 넣는 몫 · 기본 1) · I_MA(상품이 그 이평선 위일 때만 · 기본 0 = 안 봄)
  · I_COST(기본 0.002) · I_REB(week · mon · day) · I_GUARD(trend · crash · nas20 — 나스닥 빼는 때)
  · I_DOLLAR=2(원 · 달러 20일 +2% · 코스피 < 20일선인 날은 돌리기 대신 달러만)
  · I_CASH=all · idle(엔진이 안 쓰는 비운 돈을 단기채권 153130에)
  · I_MOOD=80(DART · 한투 시장 분위기 점수 ≥ 값이면 KODEX 200 · 익절 8 손절 3 10일 · 그동안 돌리기 쉼)
  · I_QCR=95(코스닥 인버스 신호에 '코스닥 종목 신용 급증 순위 ≥ 값'을 더함) · I_MOOD5=1(분위기에 흑자전환 물결 더함)
  · I_DHEDGE=0.2(하락 추세면 계좌의 그만큼 달러로 받침 · 1일봉이 들고 있어도)
  · I_DIPGUARD=dollar · trend · deep(급락 되돌림 거르기 · 여럿이면 붙여 씀)
  · I_ENS=1(돌리기 10 · 20 · 40일 섞기) · I_VT=0.10(돌리기 변동성 맞추기 · 연율 목표)
  · I_QINV=free · hedge · tier(코스닥 10일 +10% → 코스닥150 인버스 · 비운 돈 / 계좌 30%)
  · I_DIP=1(시장 폭 < 50 급락 되돌림 I2b가 켜진 날은 그 돈을 급락 되돌림에 쓰고 돌리기는 쉼)."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import i011 as R  # noqa: E402  (불러올 때는 i011 표를 찍지 않음)
import itools as I

SP = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/"
D, n = I.DAYS, len(I.DAYS)
used, d1 = np.zeros(n), np.zeros(n)
LEDGER = os.environ.get("I_LEDGER", "x008_d1.json")   # 1시간봉: x008_h1y3.json(야후 3년)
for code, buy, sell, pnl, slots in json.load(open(SP + LEDGER)):
    a, b = np.searchsorted(D, buy), np.searchsorted(D, sell)
    used[a:b] += slots / 10
    if b < n:
        d1[b] += pnl * slots / 10 / 100
free = np.clip(1 - used, 0, 1)
cands = os.environ.get("I_CANDS", "133690,138230,132030,148070").split(",")
for _c in cands:                     # 9라운드: i011 표에 없는 후보(해외 지수 등)도 받음
    if _c not in R.P:
        R.P[_c] = I.px(_c)
        R.R[_c] = np.nan_to_num(np.concatenate([[0.0], R.P[_c][1:] / R.P[_c][:-1] - 1]))
L, TOP = int(os.environ.get("I_L", "60")), int(os.environ.get("I_TOP", "1"))
gate_weak = R.G.get("시장 폭<50")
# 18라운드 RNA 공통: 코스피200 앞 60일 σ ÷ 그날까지 쌓인 σ 기록 가운데값(그날까지 값만)
_sk60 = I.sigma_n(I.K200, 60)
_srel = np.full(n, 1.0)
for _i in range(250, n):
    _h = _sk60[60:_i + 1]
    _h = _h[np.isfinite(_h)]
    if len(_h) and np.isfinite(_sk60[_i]):
        _srel[_i] = _sk60[_i] / np.median(_h)
if os.environ.get("I_BRRNA") and R.G.get("시장 폭<50") is not None:   # 19라운드 D5: 시장 폭 문턱 RNA
    _b = np.nan_to_num(I.breadth(), nan=100)
    _bm = os.environ["I_BRRNA"]
    if _bm.startswith("q"):           # 시장 폭 자기 기록(그날 앞까지) 아래 q 자리보다 낮으면
        _bth = np.nan_to_num(I.pct_hist(np.where(_b < 100, _b, np.nan), float(_bm[1:])), nan=50)
    else:                             # v{p}: 50 × (σ ÷ 가운데)^p
        _bth = 50 * _srel ** float(_bm[1:])
    R.G["시장 폭<50"] = _b < _bth
    gate_weak = R.G["시장 폭<50"]
prev_used = np.concatenate([[0.0], used[:-1]])
gate = {"weak": R.G.get("시장 폭<50"), "always": R.G["언제나"], "ma200": R.G["코스피<200일선"],
        # 1일봉이 거의 쉴 때만(어제까지 쓴 몫 < 20 · 50%) — 반쯤 쓴 달에 엔진이 깎아 먹음(I17)
        "idle20": prev_used < 0.2, "weakidle20": (R.G.get("시장 폭<50") & (prev_used < 0.2)) if R.G.get("시장 폭<50") is not None else prev_used < 0.2, "weakidle25": R.G.get("시장 폭<50") & (prev_used < 0.25), "weakidle30": R.G.get("시장 폭<50") & (prev_used < 0.3), "weakidle40": R.G.get("시장 폭<50") & (prev_used < 0.4), "weakidle50": R.G.get("시장 폭<50") & (prev_used < 0.5), "idle30": prev_used < 0.3, "idle50": prev_used < 0.5, "idle70": prev_used < 0.7}.get(os.environ.get("I_GATE", "weak"))
if os.environ.get("I_GATE", "").startswith("weakidlev"):     # 18라운드 D12: 켜는 문턱 = 0.2 × (σ ÷ 가운데)^p · 0.1 ~ 0.5
    _pg = os.environ["I_GATE"][9:]
    _pg = -int(_pg[1:]) / 100 if _pg.startswith("m") else int(_pg) / 100
    gate = R.G.get("시장 폭<50") & (prev_used < np.clip(0.2 * _srel ** _pg, 0.1, 0.5))
# 사용자 2026-10-03 "상승장이면 인버스 최소 · 0처럼 유동적으로": 장세 = 어제까지 코스피200이 200일선 위(오름) / 아래
_up = np.concatenate([[False], (np.nan_to_num(R.k > I.ma(R.k, 200), nan=0) > 0)[:-1]])
if os.environ.get("I_GREG") == "up_off":       # 오름 장세면 엔진 쉼
    gate = gate & ~_up
elif os.environ.get("I_GREG") == "down_off":   # 내림 장세면 엔진 쉼
    gate = gate & _up
W, MA_N = float(os.environ.get("I_W", "1")), int(os.environ.get("I_MA", "0"))
COST, REB, GUARD = float(os.environ.get("I_COST", "0.002")), os.environ.get("I_REB", "week"), os.environ.get("I_GUARD", "")
kk = I.K200
m20k, m60k = I.ma(kk, 20), I.ma(kk, 60)
nasp = R.P["133690"]
GUARDS = {
    "": None,
    # 코스피 하락 추세(20일선 < 60일선 · 코스피 < 20일선)면 나스닥 빼고 달러 · 금 · 채권에서만 고름
    "trend": {"133690": np.nan_to_num((kk < m20k) & (m20k < m60k), nan=0) > 0},
    # 코스피 5일 −5% 이면서 나스닥도 20일선 아래면 나스닥 뺌(함께 빠지는 때)
    "crash": {"133690": (np.nan_to_num(I.ret(kk, 5), nan=0) <= -0.05) & (np.nan_to_num(nasp < I.ma(np.nan_to_num(nasp, nan=0), 20), nan=0) > 0)},
    # 나스닥이 20일선 아래면 뺌
    "nas20": {"133690": np.nan_to_num(nasp < I.ma(np.nan_to_num(nasp, nan=0), 20), nan=0) > 0},
}
if os.environ.get("I_ENS"):
    # 2라운드 ②: 여러 기간 섞기 — 10 · 20 · 40일 돌리기 결과를 반의반씩(설정 하나에 기대지 않게)
    rot = np.mean([R.run(gate, R.momentum(_L, TOP, cands, MA_N, GUARDS[GUARD]), cost=COST, reb=REB) for _L in (10, 20, 40)], axis=0) * W
else:
    if os.environ.get("I_LRNA"):                 # 18라운드 D10: 돌리기 기간 = 20 × (가운데 ÷ σ)^p · 10 ~ 60일(거칠면 짧게)
        _pl = float(os.environ["I_LRNA"])
        _Ls = np.clip(np.round(L * _srel ** (-_pl)), 10, 60).astype(int)
        _picks = {}

        def _mom(i):
            f = _picks.setdefault(int(_Ls[i]), R.momentum(int(_Ls[i]), TOP, cands, MA_N, GUARDS[GUARD]))
            return f(i)
        rot = R.run(gate, _mom, cost=COST, reb=REB) * W
    else:
        rot = R.run(gate, R.momentum(L, TOP, cands, MA_N, GUARDS[GUARD]), cost=COST, reb=REB) * W
if os.environ.get("I_VT"):
    # 2라운드 ①: 변동성 맞추기 — 돌리기 수익의 앞 20일 흔들림(연율)이 목표보다 크면 그만큼 몫을 줄임(어제까지 값으로)
    _tv = float(os.environ["I_VT"])
    _vol = np.array([np.std(rot[max(0, i - 20):i]) * np.sqrt(250) if i >= 5 else 0.0 for i in range(n)])
    _sc = np.where(_vol > 0, np.minimum(1.0, _tv / np.maximum(_vol, 1e-9)), 1.0)
    rot = rot * _sc
if os.environ.get("I_DOLLAR"):
    # 하락 추세(원 · 달러 20일 +I_DOLLAR% · 코스피 < 20일선)인 날은 돌리기 대신 달러(138230)만 — 그날 종가 판단 → 다음 날 수익
    dol = R.P["138230"]
    d20 = np.nan_to_num(dol / np.concatenate([np.full(20, np.nan), dol[:-20]]) - 1, nan=0)
    _dth = np.full(n, float(os.environ["I_DOLLAR"]) / 100)
    _drna = os.environ.get("I_DOLRNA", "")          # 17라운드: v{c} = c × 138230 앞 60일 σ × √20 · p{q} = d20 자기 기록 아래 q 자리
    if _drna.startswith("v"):
        _dth = I.sigma_n(dol, 60) * float(_drna[1:]) * np.sqrt(20)
    elif _drna.startswith("p"):
        _dth = I.pct_hist(d20, float(_drna[1:]))
    _kb = np.ones(n)
    if os.environ.get("I_DOLBAND"):                  # 17라운드: 코스피200 < 20일선 × (1 − b × σ60 × √20)
        _kb = 1 - float(os.environ["I_DOLBAND"]) * I.sigma_n(kk, 60) * np.sqrt(20)
    cond = (d20 > np.nan_to_num(_dth, nan=9)) & (np.nan_to_num(kk < m20k * _kb, nan=0) > 0)
    cy = np.concatenate([[False], (cond & gate)[:-1]])     # 켜는 때(gate)가 꺼진 날은 달러도 안 듦
    flip = np.concatenate([[False], cy[1:] != cy[:-1]])
    rot = np.where(cy, R.R["138230"] * W, rot) - flip * COST / 2 * W
if os.environ.get("I_QINV"):
    # 코스닥 과열 뒤 코스닥150 인버스(I20 · I22): 229200 10일 +10% → 251340 · 익절 1.5 · 손절 1.5 · 10일. 1일봉이 비워 둔 돈으로(사는 날 몫 고정).
    # I_QINV=free(비운 돈) · hedge(계좌의 30%를 늘 — 1일봉이 들고 있어도)
    qq = R.P.get("229200") if "229200" in R.P else I.px("229200")
    _qth = np.full(n, float(os.environ.get("I_QTH", "0.10")))   # 8라운드: 운영 15:15 판은 0.095
    if os.environ.get("I_QTHRNA"):   # 19라운드: 한쪽으로만 — max(문턱, c × 229200 σ60 × √10)(거칠 때만 더 엄격)
        _qth = np.fmax(_qth, I.sigma_n(qq, 60) * float(os.environ["I_QTHRNA"]) * np.sqrt(10))
    qsig = np.nan_to_num(I.ret(qq, 10), nan=0) >= _qth
    if os.environ.get("I_PEEK"):      # 점검 A3 '검사 눈': 일부러 내일 값을 보는 판 — 자르기 · 더럽히기 시험에 반드시 걸려야 함
        qsig = qsig | (np.nan_to_num(np.concatenate([qq[1:] / qq[:-1] - 1, [0.0]]), nan=0) < -0.02)
    if os.environ.get("I_QCR"):
        # I49: 또는 코스닥 종목 신용 잔고율 20일 변화가 앞 250일 순위 ≥ I_QCR(코스닥 종목만 · agg2.npz)
        _a2 = np.load("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/agg2.npz")["코스닥 신용 잔고율 20일 변화"]
        _rk = np.full(n, np.nan)
        for _i in range(250, n):
            _h = _a2[_i - 250:_i]
            _h = _h[np.isfinite(_h)]
            if len(_h) > 150 and np.isfinite(_a2[_i]):
                _rk[_i] = (_h < _a2[_i]).mean() * 100
        qsig = qsig | (np.nan_to_num(_rk, nan=-1) >= float(os.environ["I_QCR"]))
    if os.environ.get("I_QREG") == "up_off":       # 오름 장세면 인버스 안 함
        qsig = qsig & ~_up
    elif os.environ.get("I_QREG") == "down_off":   # 내림 장세면 인버스 안 함
        qsig = qsig & _up
    if os.environ.get("I_QEXIT"):        # RNA 2라운드: 익절 · 손절 = c × 코스닥150 앞 60일 σ × √10(산 날 값)
        _sq = I.sigma_n(qq, int(os.environ.get("I_QSIGN", "60"))) * float(os.environ["I_QEXIT"]) * np.sqrt(10)   # 7라운드: σ 기간
        _sq = np.clip(_sq, float(os.environ.get("I_QEXIT_LO", 0)), float(os.environ.get("I_QEXIT_HI", 9)))   # 25라운드: 바닥 · 천장
        _side = os.environ.get("I_QEXIT_SIDE", "both")   # 25라운드: stop(손절만 RNA · 익절 1.5%) · take(익절만 RNA · 손절 1.5%)
        _st = np.full(n, 0.015) if _side == "take" else _sq
        _tk = np.full(n, 0.015) if _side == "stop" else _sq
        qtr, qd = I.sim_var(qsig, "251340", -_st, _tk, 10, cost=COST)
    else:
        qtr, qd = I.sim(qsig, "251340", -0.015, 0.015, 10, cost=COST)
    _cr = I.series("market-data/funds.json", "신용융자잔고")
    credit20 = np.full(n, np.nan)
    credit20[20:] = _cr[20:] / _cr[:-20] - 1
    credit20 = np.nan_to_num(credit20, nan=0)
    qinv = np.zeros(n)
    for a, b, _ in qtr:
        if os.environ["I_QINV"] == "hedge":
            wq = 0.3
        elif os.environ["I_QINV"] == "tier":      # 2단 몫(I27): 신용융자 20일 +5% 이상이면 비운 돈 전부, 아니면 절반
            wq = free[a] * (1.0 if credit20[a] >= 0.05 else 0.5)
        elif os.environ.get("I_QREG") == "up_half":   # 오름 장세면 비운 돈의 절반만
            wq = free[a] * (0.5 if _up[a] else 1.0)
        else:
            wq = free[a]
        qinv[a:b + 1] += qd[a:b + 1] * wq
if os.environ.get("I_CASH"):
    # I36: 엔진이 쓰지 않는 비운 돈은 현금 대신 단기채권(153130 · I_CASH=all: 1일봉이 비운 돈 모두 · idle: 엔진이 켜졌는데 고른 것이 없을 때만)
    bond = np.nan_to_num(np.concatenate([[0], I.px("153130")[1:] / I.px("153130")[:-1] - 1]), nan=0)
prev_free = np.concatenate([[1.0], free[:-1]])
mix = d1 + rot * prev_free     # 어제 비워 둔 몫으로 오늘 수익
if os.environ.get("I_DIP"):
    # 급락 되돌림(I2b · 시장 폭 < 50일 때만)이 켜진 날은 그 돈을 급락 되돌림에 쓰고 돌리기는 쉼(돈이 겹치지 않게)
    _dth2 = np.full(n, float(os.environ.get("I_DIP_TH", "-0.05")))
    if os.environ.get("I_DIPTHRNA"):  # 19라운드: 한쪽으로만 — min(문턱, −c × 코스피200 σ60 × √5)(거칠 때만 더 엄격)
        _dth2 = np.fmin(_dth2, -I.sigma_n(I.K200, 60) * float(os.environ["I_DIPTHRNA"]) * np.sqrt(5))
    sig = (np.nan_to_num(I.ret(I.K200, 5), nan=0) <= _dth2) & gate_weak     # I39: 운영(15:15 판단)은 −4.5%
    if os.environ.get("I_DIPRNA"):       # RNA 2라운드: 5일 하락이 그 지수 자기 기록(그날 앞까지) 아래 q면
        _r5 = I.ret(I.K200, 5)
        _cut = (I.pct_roll(_r5, float(os.environ["I_DIPRNA"]), int(os.environ["I_DIPWIN"])) if os.environ.get("I_DIPWIN")
                else I.pct_hist(_r5, float(os.environ["I_DIPRNA"])))
        sig = np.nan_to_num(_r5 <= _cut, nan=0).astype(bool) & gate_weak
    _dg = os.environ.get("I_DIPGUARD", "")
    if _dg:
        # 3라운드: 급락 되돌림 거르기(크게 빠진 달 손해의 대부분이 여기서 남) — 그날까지 알려진 값만
        _dol = R.P["138230"]
        _d20 = np.nan_to_num(_dol / np.concatenate([np.full(20, np.nan), _dol[:-20]]) - 1, nan=0)
        _m60 = I.ma(I.K200, 60)
        if "dollar" in _dg:      # 원 · 달러가 20일 +2% 넘게 오르는 중이면(외국인 돈이 빠지는 중) 건너뜀
            sig = sig & ~(_d20 > 0.02)
        if "trend" in _dg:       # 20일선 < 60일선(하락 추세 뚜렷)이면 건너뜀
            sig = sig & ~(np.nan_to_num(m20k < _m60, nan=0) > 0)
        if "deep" in _dg:        # 20일 −10% 넘게 빠진 상태면(길게 무너지는 중) 건너뜀
            sig = sig & ~(np.nan_to_num(I.ret(I.K200, 20), nan=0) <= -0.10)
    # 5라운드 ⑥: I_DIPCODE=122630(2배)이면 2배 상품으로 · 손절 · 익절은 I_DIP_ST · I_DIP_TK(기본 −3 · +3%)
    _dc = os.environ.get("I_DIPCODE", "069500")
    if _dc not in I.PX:
        I.px(_dc)
    if os.environ.get("I_DIPTAKE"):      # RNA 5라운드: 익절만 c × σ60 × √20 · 손절은 −3% 그대로
        _tk = I.sigma_n(I.K200, 60) * float(os.environ["I_DIPTAKE"]) * np.sqrt(20)
        _tk = np.clip(_tk, float(os.environ.get("I_DIPTAKE_LO", 0)), float(os.environ.get("I_DIPTAKE_HI", 9)))   # 6라운드: 바닥 · 천장
        tr, dd = I.sim_var(sig, _dc, np.full(n, -0.03), _tk, 20, cost=COST, cool=20)
    elif os.environ.get("I_DIPEXIT"):      # RNA 4라운드: 익절 · 손절 = c × 코스피200 앞 60일 σ × √20(산 날 값)
        _sk = I.sigma_n(I.K200, 60) * float(os.environ["I_DIPEXIT"]) * np.sqrt(20)
        tr, dd = I.sim_var(sig, _dc, -_sk, _sk, 20, cost=COST, cool=20)
    else:
        tr, dd = I.sim(sig, _dc, float(os.environ.get("I_DIP_ST", "-0.03")), float(os.environ.get("I_DIP_TK", "0.03")), 20, cool=20, cost=COST)
    on = np.zeros(n, bool)
    dip = np.zeros(n)
    for a, b, _ in tr:
        on[a + 1:b + 1] = True
        dip[a:b + 1] += dd[a:b + 1] * free[a]
    rot_on = np.where(on, 0.0, rot)
    mix = d1 + rot_on * prev_free + dip
    rot = rot_on
if os.environ.get("I_QINV"):
    _qp = os.environ.get("I_QPRI", "")
    if _qp:
        # 모의투자(현금 계좌)에선 엔진과 인버스가 같은 돈을 겹쳐 못 씀(연구 기본은 겹침): inv = 인버스 든 날 엔진 쉼 · half = 둘 다 반
        _qon = np.zeros(n, bool)
        for a, b, _ in qtr:
            _qon[a + 1:b + 1] = True
        _eng = mix - d1
        if _qp == "inv":
            mix = d1 + np.where(_qon, 0.0, _eng) + qinv
        elif _qp == "half":
            mix = d1 + np.where(_qon, 0.5 * _eng, _eng) + np.where(_qon, 0.5, 1.0) * qinv
        elif _qp == "eng":       # 엔진이 돈을 쓰는 날엔 인버스 안 함
            _busy = np.abs(_eng) > 1e-12
            mix = d1 + _eng + np.where(_busy, 0.0, qinv)
    else:
        mix = mix + qinv
if os.environ.get("I_DHEDGE"):
    # 3라운드: 하락 추세(원 · 달러 20일 +2% · 코스피 < 20일선)인 날은 1일봉이 돈을 쓰고 있어도 계좌의 일부(I_DHEDGE)를 달러선물로 받침
    _hw = float(os.environ["I_DHEDGE"])
    _dl = R.P["138230"]
    _dd = np.nan_to_num(_dl / np.concatenate([np.full(20, np.nan), _dl[:-20]]) - 1, nan=0)
    _c = (_dd > 0.02) & (np.nan_to_num(kk < m20k, nan=0) > 0)
    _cy = np.concatenate([[False], _c[:-1]])
    _fl = np.concatenate([[False], _cy[1:] != _cy[:-1]])
    mix = mix + np.where(_cy, R.R["138230"] * _hw, 0.0) - _fl * COST / 2 * _hw
if os.environ.get("I_MOOD"):
    # I48: DART · 한투 '시장 분위기 점수'(i031 · i032 · 전환사채 · 공급계약 공시 물결 + 목표가 올림 몫 + 대차잔고 반대) ≥ I_MOOD → KODEX 200
    # 익절 8 · 손절 3 · 10일. 엔진이 켜진 날(1일봉 쓴 몫 < 20%) 비운 돈으로. 그동안 돌리기 몫은 쉼(돈 겹치지 않게).
    _A = dict(np.load("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/agg.npz"))

    def _rank(a):
        out = np.full(n, np.nan)
        for i in range(250, n):
            h = a[i - 250:i]
            h = h[np.isfinite(h)]
            if len(h) > 150 and np.isfinite(a[i]):
                out[i] = (h < a[i]).mean() * 100
        return out
    _L = [_rank(_A["DART 전환사채 20일 수"]), _rank(_A["DART 공급계약 20일 수"]), _rank(_A["한투 목표가 올림 몫(20일)"]), 100 - _rank(_A["한투 대차잔고 20일 변화"])]
    if os.environ.get("I_MOOD5"):     # I49: 흑자전환 − 적자전환 물결(DART 분기 실적)도 더함
        _L.append(_rank(np.load("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/agg2.npz")["DART 흑자전환 − 적자전환(60일)"]))
    if os.environ.get("I_MOOD6"):     # 5-①: 임원소유 보고 물결(DART 20일 수 · 하루 밀기 · agg3.npz)도 더함
        _L.append(_rank(np.load("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/agg3.npz")["DART " + os.environ["I_MOOD6"] + " 20일 수"]))
    _R = np.array(_L)
    mood = np.nanmean(_R, axis=0)
    mood[np.isfinite(_R).sum(axis=0) < len(_L) - 1] = np.nan
    msig = (np.nan_to_num(mood, nan=-1) >= float(os.environ["I_MOOD"])) & gate
    mtr, md = I.sim(msig, "069500", -0.03, 0.08, 10, cost=COST)
    mon = np.zeros(n, bool)
    madd = np.zeros(n)
    for a, b, _ in mtr:
        mon[a + 1:b + 1] = True
        madd[a:b + 1] += md[a:b + 1] * free[a]
    mix = mix - np.where(mon, rot * prev_free, 0.0) + madd
if os.environ.get("I_CASH"):
    # 엔진이 그날 돈을 쓰지 않았으면(rot == 0 · 급락 · 코스닥 인버스도 없음) 비운 몫을 단기채권에. 바꿀 때 비용은 아주 작아 뺌(단기채권 호가 차이 ~0.01%).
    idle_cash = (rot == 0) & (np.abs(mix - d1) < 1e-12)
    use = idle_cash if os.environ["I_CASH"] == "all" else idle_cash & np.concatenate([[False], gate[:-1]])
    mix = mix + np.where(use, bond * prev_free, 0.0)
if os.environ.get("I_DUMP"):
    # 자르기 시험용: 날마다 판단 · 손익 배열을 남김(research/lookahead.py가 자른 자료 · 온 자료 결과를 견줌)
    np.savez(os.environ["I_DUMP"], days=np.array(D), d1=d1, mix=mix, rot=rot, used=used,
             dip=(dip if "dip" in dir() else np.zeros(n)), qinv=(qinv if "qinv" in dir() else np.zeros(n)))
print(f"== I 13회차: 1일봉 + 약세장 돌리기({','.join(R.NAME.get(c, c) for c in cands)} · {L}일 · 위 {TOP} · {os.environ.get('I_GATE', 'weak')} · 몫 {W} · 이평 {MA_N}{' · 급락 되돌림 먼저' if os.environ.get('I_DIP') else ''} · 비용 {COST} · 고르는 날 {REB} · 거르기 {GUARD or '없음'} · 하락 추세 달러 {os.environ.get('I_DOLLAR', '안 씀')} · 코스닥 과열 인버스 {os.environ.get('I_QINV', '안 씀')}) ==", flush=True)
for name, lo, hi in (("B", "20170101", "20210101"), ("C", "20210101", "20991231"), ("C1 21~25", "20210101", "20260101"), ("C2 2026", "20260101", "20991231")):
    a, m, c = I.stats(d1, lo, hi), I.stats(rot, lo, hi), I.stats(mix, lo, hi)
    if a is None:          # 자른 자료(I_CUT)엔 그 기간이 없음
        continue
    print(f"  {name:9s} 1일봉만 연 {a[0]:+6.1f} 골 {a[1]:6.1f} | 돌리기만(계좌 전부) 연 {m[0]:+5.1f} 골 {m[1]:6.1f} | 함께 연 {c[0]:+6.1f} 골 {c[1]:6.1f}", flush=True)
print("끝", flush=True)
