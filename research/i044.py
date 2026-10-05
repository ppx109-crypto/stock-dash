"""통합 매매 규칙 DNA · RNA 시험(사용자 2026-10-03 "DNA인지 RNA인지 테스트 · RNA면 흔들면서 RNA 테스트").
1일봉 · 15분봉 후보의 '조용함'(① 추세 문 조건1) 문턱:
  DNA      = 지금 규칙 — 모든 종목 · 모든 날 변동성을 한 번에 줄 세운 아래 40% 자리(고정 숫자 ≈ 2.15)
  DNA_past = 그 달 앞 자료로만 다시 잰 같은 문턱(dguard 아홉째 겹)
  RNA q    = 그날 시총 100위 안 종목끼리 견준 아래 q(날마다 움직임 · 그날 값만 씀 · 미래 참조 없음)
  RNA_jit  = 날마다 q를 30 ~ 50% 사이에서 무작위로 흔듦(씨앗별)
I_VAR=DNA | DNA_past | RNA30 | RNA35 | RNA40 | RNA45 | RNA50 | JIT0 ~ JIT4 · 결과는 한 줄."""
import os
import random
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash")
import lab
import nrl
import rule

var = os.environ.get("I_VAR", "DNA")
full = rule._calm
by_day = {}
for r in nrl.inside:
    if r.get("변동성") is not None:
        by_day.setdefault(r["date"], []).append(r["변동성"])
by_day = {d: np.sort(np.array(v)) for d, v in by_day.items()}


def cut(d, q):
    v = by_day.get(d)
    return float(v[min(len(v) - 1, int(len(v) * q))]) if v is not None and len(v) >= 20 else full


if var.startswith("SHK"):
    # DNA 흔들기: 고정 숫자 셋을 ±20% 안에서 무작위로 한 번 바꿈(씨앗별) — 추세 기울기 · 60일 오름 · 조용함 자리
    rng = random.Random(100 + int(var[3:]))
    rule.SLOPE = 1.46 * rng.uniform(0.8, 1.2)
    rule.SIXTY = 20.0 * rng.uniform(0.8, 1.2)
    cq = 0.4 * rng.uniform(0.8, 1.2)
    allv = np.sort(np.array([r["변동성"] for r in nrl.inside if r.get("변동성") is not None]))
    full_shk = float(allv[int(len(allv) * cq)])
    edge = lambda d: full_shk
    print(f"  흔든 값: 기울기 {rule.SLOPE:.2f} · 60일 {rule.SIXTY:.1f}% · 조용함 자리 {cq * 100:.0f}%", flush=True)
elif var == "DNA":
    edge = lambda d: full
elif var == "DNA_past":
    edge = lambda d: (nrl.CALM_MONTH or {}).get(d[:6], full)
elif var.startswith("RNA"):
    q = int(var[3:]) / 100
    edge = lambda d: cut(d, q)
elif var[:2] in ("RS", "RX", "HS", "HV", "VS", "VX", "OS", "MS", "CQ", "MV", "OV", "AV", "AH", "AC", "AO", "XV", "YV") or var.startswith("RALL") or var == "BRLAG":
    edge = lambda d: full                      # 아래에서 다시 정함
else:
    rng = random.Random(int(var[3:]))
    qs = {d: rng.uniform(0.30, 0.50) for d in sorted(by_day)}
    edge = lambda d: cut(d, qs.get(d, 0.4))
# 기울기 · 60일도 RNA로: 그날 100위 안끼리 견준 위 q (지금 DNA가 통과시키는 몫 ≈ 기울기 10% · 60일 17% · 조용함 51%)
by_s, by_x = {}, {}
for r in nrl.inside:
    if r.get("추세 기울기") is not None:
        by_s.setdefault(r["date"], []).append(r["추세 기울기"])
    if r.get("60일 전 대비") is not None:
        by_x.setdefault(r["date"], []).append(r["60일 전 대비"])
by_s = {d: np.sort(np.array(v)) for d, v in by_s.items()}
by_x = {d: np.sort(np.array(v)) for d, v in by_x.items()}


def top_cut(table, d, q, dflt):
    v = table.get(d)
    return float(v[min(len(v) - 1, int(len(v) * (1 - q)))]) if v is not None and len(v) >= 20 else dflt


BASE_SLOPE, BASE_SIXTY = rule.SLOPE, rule.SIXTY          # SHK(흔들기)가 바꿨으면 그 값
slope_of, sixty_of = (lambda d: BASE_SLOPE), (lambda d: BASE_SIXTY)
if var.startswith("RS"):
    qs_ = int(var[2:]) / 100
    slope_of = lambda d: top_cut(by_s, d, qs_, 1.46)
    edge = lambda d: full
elif var.startswith("RX"):
    qx_ = int(var[2:]) / 100
    sixty_of = lambda d: top_cut(by_x, d, qx_, 20.0)
    edge = lambda d: full
elif var.startswith("RALL"):
    j = var[4:]
    rng2 = random.Random(200 + int(j[1:])) if j.startswith("J") else None
    k = (lambda: rng2.uniform(0.8, 1.2)) if rng2 else (lambda: 1.0)
    qc, qs2, qx2 = 0.51 * k(), 0.10 * k(), 0.17 * k()
    edge = lambda d: cut(d, qc)
    slope_of = lambda d: top_cut(by_s, d, qs2, 1.46)
    sixty_of = lambda d: top_cut(by_x, d, qx2, 20.0)
    print(f"  RNA 몫: 조용함 아래 {qc * 100:.0f}% · 기울기 위 {qs2 * 100:.0f}% · 60일 위 {qx2 * 100:.0f}%", flush=True)
# RNA 1라운드 설계(사용자 "한 번에 실패라 하지 말고 DNA만큼 연구"):
#  HS{q}F{f}: 기울기 = max(바닥 f, 그날 100위 안 위 q% 자리) — 상대 순위에 약한 장 거르기(바닥)를 남김
#  VS{z}: 기울기 ÷ 변동성 ≥ z/100(종목마다 자기 흔들림에 맞춘 문턱) · VX{z}: 60일 오름 ÷ (변동성 × √60) ≥ z/100
#  HV{q}F{f}Z{z}: HS + VX 함께
row_slope = row_sixty = None
if var.startswith("HS") or var.startswith("HV"):
    import re as _re
    mt = _re.match(r"H[SV](\d+)F(\d+)(?:Z(\d+))?", var)
    qh, fh = int(mt.group(1)) / 100, int(mt.group(2)) / 100
    slope_of = lambda d: max(fh, top_cut(by_s, d, qh, BASE_SLOPE))
    edge = lambda d: full
    if mt.group(3):
        zx = int(mt.group(3)) / 100
        row_sixty = lambda r: zx * (r.get("변동성") or 99) * np.sqrt(60)
if var.startswith("VS"):
    zs = int(var[2:]) / 100
    row_slope = lambda r: zs * (r.get("변동성") or 99)
    edge = lambda d: full
if var.startswith("VX"):
    zx = int(var[2:]) / 100
    row_sixty = lambda r: zx * (r.get("변동성") or 99) * np.sqrt(60)
    edge = lambda d: full
# 4라운드 D2: 기울기 = max(바닥 f, 그 종목 자기 기록(앞 250일 · 그날 제외) 위 q 자리) — OS{q}F{f}
own_cut = {}
if var.startswith("OS"):
    import re as _re2
    mo = _re2.match(r"OS(\d+)F(\d+)", var)
    qo, fo = int(mo.group(1)) / 100, int(mo.group(2)) / 100
    seq = {}
    for r in nrl.inside:
        if r.get("추세 기울기") is not None:
            seq.setdefault(r["code"], []).append((r["date"], r["추세 기울기"]))
    for c_, lst in seq.items():
        lst.sort()
        vals = np.array([v for _, v in lst])
        for i_, (d_, _) in enumerate(lst):
            w_ = vals[max(0, i_ - 250):i_]
            if len(w_) >= 120:
                own_cut[(c_, d_)] = max(fo, float(np.partition(w_, int(len(w_) * (1 - qo)))[int(len(w_) * (1 - qo))]))
    row_slope = lambda r: own_cut.get((r["code"], r["date"]), 99.0)
    edge = lambda d: full
# 5라운드 D2: 시장 대비 기울기 — 종목 기울기 ≥ max(바닥 f, 그날 코스피200 180일선 5일 기울기 + m) · MS{m}F{f}
if var.startswith("MS"):
    import re as _re3
    sys.path.insert(0, "/home/user/stock-dash/research")
    import itools as _I
    ms = _re3.match(r"MS(\d+)F(\d+)", var)
    mm, ff = int(ms.group(1)) / 100, int(ms.group(2)) / 100
    _ma = _I.ma(_I.K200, 180)
    _mk = {d: (_ma[i] / _ma[i - 5] - 1) * 100 for i, d in enumerate(_I.DAYS) if i >= 185 and np.isfinite(_ma[i]) and np.isfinite(_ma[i - 5])}
    slope_of = lambda d: max(ff, _mk.get(d, 0.0) + mm)
    edge = lambda d: full
# 11라운드 D1 조용함 문턱(변동성 = 20일 하루 등락 표준편차 %):
#  CQ{q}C{c}: min(천장 c/100, 그날 100위 안 아래 q% 자리) — 횡단면이되 모두 거칠면 천장이 막음
#  MV{k}[C{c}]: k/100 × 그날 코스피200 20일 하루 등락 표준편차(%) [· 천장 c/100] — 시장 흔들림 대비
#  OV{q}C{c}: 그 종목 자기 기록(앞 250일 · 그날 제외) 아래 q% 자리와 천장 c/100 중 작은 값 — 평소보다 조용할 때
row_calm = None
if var[:2] in ("CQ", "MV", "OV"):
    import re as _re4
    m4 = _re4.match(r"(CQ|MV|OV)(\d+)(?:C(\d+))?", var)
    kk, cap = int(m4.group(2)) / 100, (int(m4.group(3)) / 100 if m4.group(3) else 99.0)
    if m4.group(1) == "CQ":
        edge = lambda d: min(cap, cut(d, kk))
    elif m4.group(1) == "MV":
        sys.path.insert(0, "/home/user/stock-dash/research")
        import itools as _I4
        _k = _I4.K200
        _r = np.concatenate([[np.nan], (_k[1:] / _k[:-1] - 1) * 100])
        _sm = {d: float(np.nanstd(_r[i - 19:i + 1], ddof=1)) for i, d in enumerate(_I4.DAYS) if i >= 20}
        edge = lambda d: min(cap, kk * _sm.get(d, full / kk))
    else:
        _seq = {}
        for r in nrl.inside:
            if r.get("변동성") is not None:
                _seq.setdefault(r["code"], []).append((r["date"], r["변동성"]))
        _own = {}
        for c_, lst in _seq.items():
            lst.sort()
            vals = np.array([v for _, v in lst])
            for i_, (d_, _) in enumerate(lst):
                w_ = vals[max(0, i_ - 250):i_]
                if len(w_) >= 120:
                    _own[(c_, d_)] = min(cap, float(np.partition(w_, int(len(w_) * kk))[int(len(w_) * kk)]))
        row_calm = lambda r: _own.get((r["code"], r["date"]), -1.0)
        edge = lambda d: full
# 13라운드 D4 정배열 띠(3일선이 200일선보다 LO ~ HI% 위 · nrl.aligned · 시장 폭 50 그대로):
#  AV{p}: 띠 × (그 종목 변동성 ÷ 2.15)^(p/100) — 흔들림 맞춤 띠(p 0 = DNA)
#  AC{a}_{b}: 그날 정배열 종목끼리 간격을 줄 세운 a ~ b% 자리 안 — 횡단면 띠
#  AO{a}_{b}: 그 종목 자기 기록(앞 250일 · 그날 제외) 간격의 a ~ b% 자리 안 — 자기 기록 띠
if var[:2] in ("AV", "AH", "AC", "AO"):
    import re as _re5
    _LO, _HI = nrl.LO, nrl.HI
    _base_al = nrl.aligned
    m5 = _re5.match(r"(AV|AH|AC|AO)(\d+)(?:_(\d+))?", var)
    if m5.group(1) in ("AV", "AH"):
        _p, _top_only = int(m5.group(2)) / 100, m5.group(1) == "AH"     # 14라운드 AH: 위 끝(HI)만 흔들림 맞춤

        def _al(r):
            f = nrl.F.form_of(nrl.shape, r)
            g, v = f.get("간격"), r.get("변동성")
            if not f.get("정배열") or g is None or v is None or nrl.BR.get(r["date"], 0) < 50:
                return False
            k = (v / 2.15) ** _p
            return (_LO if _top_only else _LO * k) <= g < _HI * k
    else:
        _a, _b = int(m5.group(2)) / 100, int(m5.group(3)) / 100
        if m5.group(1) == "AC":
            _gd = {}
            for r in nrl.inside:
                f = nrl.F.form_of(nrl.shape, r)
                if f.get("정배열") and f.get("간격") is not None:
                    _gd.setdefault(r["date"], []).append(f["간격"])
            _gd = {d: np.sort(np.array(v)) for d, v in _gd.items()}

            def _al(r):
                f = nrl.F.form_of(nrl.shape, r)
                g = f.get("간격")
                if not f.get("정배열") or g is None or nrl.BR.get(r["date"], 0) < 50:
                    return False
                v = _gd.get(r["date"])
                if v is None or len(v) < 5:
                    return _LO <= g < _HI
                q = np.searchsorted(v, g) / len(v)
                return _a <= q < _b
        else:
            def _al(r):
                f = nrl.F.form_of(nrl.shape, r)
                g = f.get("간격")
                if not f.get("정배열") or g is None or nrl.BR.get(r["date"], 0) < 50:
                    return False
                one, i = nrl.shape[r["code"]]["간격"], r["i"]
                w = one[max(0, i - 250):i]
                w = w[np.isfinite(w)]
                if len(w) < 120:
                    return False
                q = np.searchsorted(np.sort(w), g) / len(w)
                return _a <= q < _b
    nrl.aligned = _al
    edge = lambda d: full
# 점검 A5: 1일봉 후보 ②(정배열)의 시장 폭 ≥ 50을 어제 값으로(I_VAR=BRLAG)
if var == "BRLAG":
    _bd = sorted(nrl.BR)
    nrl.BR = {d: nrl.BR[_bd[i - 1]] for i, d in enumerate(_bd) if i > 0}
    edge = lambda d: full
inner = rule.holds


def holds(r):
    rule._calm, rule.SLOPE, rule.SIXTY = edge(r["date"]), slope_of(r["date"]), sixty_of(r["date"])
    if row_slope:
        rule.SLOPE = row_slope(r)
    if row_sixty:
        rule.SIXTY = row_sixty(r)
    if row_calm:
        rule._calm = row_calm(r)
    try:
        return inner(r)
    finally:
        rule._calm, rule.SLOPE, rule.SIXTY = full, BASE_SLOPE, BASE_SIXTY


if var != "DNA":
    # 추세 문(rule.holds) 안의 문턱만 바꿈 — 사는 조건 전체(nrl.BASE_HOLD = (추세 문 또는 정배열 문) · 수급 · 목표가 거름)와 크기(BASE_SIZE)는 그대로(dguard 아홉째 겹과 같은 방식)
    rule.holds = holds


# 15라운드 D6 ① 추세 팔기(+5% 절반 · +13% 전량 · −5% 손절 · 10일) RNA:
#  XV{p}[A|T|S|D]: k = (산 날 그 종목 변동성 ÷ V0)^(p/100) · V0 = 앞 기간(고르는 기간) 추세 문 통과 날 변동성 가운데값
#  A(기본) 다섯 숫자 모두 × k(기간은 ÷ k) · T 익절(+5 · +13)만 · S 손절만 · D 기간만(10 ÷ k)
EXIT = nrl.BASE_EXIT
if var.startswith("XV"):
    import re as _re6
    m6 = _re6.match(r"XV(\d+)([ATSDWU]?)", var)
    _p6, _w6 = int(m6.group(1)) / 100, m6.group(2) or "A"
    _v0 = float(np.median([r["변동성"] for r in nrl.early if r.get("변동성") is not None and rule.holds(r)]))
    print(f"  V0 = {_v0:.2f}", flush=True)

    def _rule_exit(lane, start, price, step, peak, row=None):
        v = (row or {}).get("변동성") or _v0
        k = (v / _v0) ** _p6
        fi, tk, st, dy = 5.0, 13.0, 5.0, 10
        if _w6 in "AT":
            fi, tk = fi * k, tk * k
        if _w6 in "AS":
            st = st * k
        if _w6 in "AD":
            dy = max(3, round(10 / k))
        if _w6 == "W":                   # 21라운드: 손절만 '넓히기만'(거칠 때만 · 조용해도 5% 아래로 안 좁힘)
            st = st * max(1.0, k)
        if _w6 == "U":                   # 21라운드: 익절만 '넓히기만'
            fi, tk = fi * max(1.0, k), tk * max(1.0, k)
        return nrl.half_rule(first=fi, take=tk, stop=st, days=dy)(lane, start, price, step, peak, row)
    EXIT = lab.exit_per_tier(nrl.tier, {"규칙": _rule_exit, "정배열": nrl.broken})
# 16라운드 D7 ② 정배열 팔기(손절 −10% · 한때 +8% 닿은 뒤 +1% 아래면 팜 · 정배열 깨지면 팜) RNA:
#  YV{p}[A|S|B]: k = (산 날 변동성 ÷ V0)^(p/100) · V0 = 앞 기간 정배열 문 통과 날 변동성 가운데값 · A 모두 × k · S 손절만 · B 본전 지키기(+8 · +1)만
if var.startswith("YV"):
    import re as _re7
    m7 = _re7.match(r"YV(\d+)([ASBW]?)", var)
    _p7, _w7 = int(m7.group(1)) / 100, m7.group(2) or "A"
    _v7 = float(np.median([r["변동성"] for r in nrl.early[::5] if r.get("변동성") is not None and nrl.aligned(r)]))
    print(f"  V0 = {_v7:.2f}", flush=True)

    def _broken(lane, start, price, step, peak, row=None):
        v = (row or {}).get("변동성") or _v7
        k = (v / _v7) ** _p7
        st, hi, lo = 10.0, 8.0, 1.0
        if _w7 in "AS":
            st *= k
        if _w7 in "AB":
            hi, lo = hi * k, lo * k
        if _w7 == "W":                   # 21라운드: 손절만 '넓히기만'
            st *= max(1.0, k)
        spot = start + step
        close = lane["closes"][spot]
        if (close / price - 1) * 100 <= -st:
            return True
        if (peak / price - 1) * 100 >= hi and (close / price - 1) * 100 <= lo:
            return True
        return not nrl.shape[lane["code"]]["정배열"][spot]
    EXIT = lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": _broken})
# ── 손절 줄 줄이기 연구(docs/RL-STOP.md · 2026-10-04): I_SX="설계+설계" · 모두 그날 종가까지 아는 값만 ──
#  BR{깊이}_{몫×100}: 끝난 매매로 센 지갑이 꼭대기에서 깊이% 파이면 자리를 몫만큼만(lab brake)
#  ST{n}_{날}_{쉼}_{손실}: 최근 '날' 안에 '손실'% 넘게 잃고 판 매매 n번 → '쉼'일 새로 안 삼(lab stop_run)
#  CD{날}: 잃고 판 종목은 그 뒤 '날' 동안 다시 안 삼(lab cooldown · 손실만)
#  MK{x}: 코스피200 5일 수익 ≤ −x/10%인 날은 새로 안 삼 · MA{n}: 코스피200 < n일선이면 새로 안 삼
#  GP{y}: 그 종목이 앞 60일(그날 포함) 안에 하루 −y% 넘게 빠진 적 있으면 안 삼 · CH{x}: 산 날 하루 +x% 넘게 올랐으면 안 삼
#  VL{z}: 그 종목 변동성 > z/100이면 안 삼 · SZ{z}: 변동성 > z/100이면 칸 반으로 · PW{n}: 최근 5거래일 새로 담기 n번까지
SX = [x for x in os.environ.get("I_SX", "").split("+") if x]
SX_KW, SX_FILT, SX_SIZE, SX_MX = {}, [], None, None
if SX:
    import re as _rex
    sys.path.insert(0, "/home/user/stock-dash/research")
    import itools as _IX
    _kd = {d: i for i, d in enumerate(_IX.DAYS)}
    _k = _IX.K200
    _k5 = {d: (_k[i] / _k[i - 5] - 1) * 100 for d, i in _kd.items() if i >= 5}
    _kma = {}
    for x in SX:
        m = _rex.match(r"([A-Z]+)([\d_]+)", x)
        key, nums = m.group(1), [int(v) for v in m.group(2).split("_")]
        if key == "BR":
            SX_KW["brake"] = (nums[0], nums[1] / 100)
        elif key == "ST":
            SX_KW["stop_run"] = tuple(nums)
        elif key == "CD":
            SX_KW["cooldown"], SX_KW["cooldown_after"] = nums[0], "손실"
        elif key == "PW":
            SX_KW["per_window"] = (nums[0], 5)
        elif key == "MK":
            _t = nums[0] / 10
            SX_FILT.append(lambda r, _t=_t: _k5.get(r["date"], 0) > -_t)
        elif key == "MA":
            _n = nums[0]; _ma = _IX.ma(_k, _n)
            _above = {d: (np.isfinite(_ma[i]) and _k[i] >= _ma[i]) for d, i in _kd.items()}
            SX_FILT.append(lambda r, _a=_above: _a.get(r["date"], True))
        elif key == "GP":
            _y = nums[0]
            def _gp(r, _y=_y):
                c = nrl.lanes[r["code"]]["closes"]; i = r["i"]
                w = c[max(1, i - 59):i + 1]; p = c[max(0, i - 60):i]
                return not any(b and a and (b / a - 1) * 100 <= -_y for a, b in zip(p, w))
            SX_FILT.append(_gp)
        elif key == "CH":
            _x = nums[0]
            SX_FILT.append(lambda r, _x=_x: not (r["i"] >= 1 and nrl.lanes[r["code"]]["closes"][r["i"] - 1]
                                               and (nrl.lanes[r["code"]]["closes"][r["i"]] / nrl.lanes[r["code"]]["closes"][r["i"] - 1] - 1) * 100 >= _x))
        elif key == "VL":
            _z = nums[0] / 100
            SX_FILT.append(lambda r, _z=_z: (r.get("변동성") or 0) <= _z)
        elif key == "CAP":                                  # 연구자 추가(30회차 · 결과 본 뒤): 함께 쓰는 칸을 n칸까지만
            SX_KW["busy_cap"] = nums[0]
        elif key == "BT":                                   # 연구자 추가: 시장 폭 ≥ b(아주 강한 장 · 앞 기간 손절 무리가 폭 83 ~ 87에서 남)면 새로 안 삼
            _b = nums[0]
            SX_FILT.append(lambda r, _b=_b: (nrl.BR.get(r["date"]) or 0) < _b)
        elif key == "MX":                                   # 연구자 추가: 코스피200이 앞 20일 꼭대기보다 x/10% 넘게 빠진 날 종가에 들고 있는 것 모두 팜
            _x = nums[0] / 10
            _hi20 = {d: max(_k[max(0, i - 19):i + 1]) for d, i in _kd.items()}
            SX_MX = {d for d, i in _kd.items() if (_k[i] / _hi20[d] - 1) * 100 <= -_x}
        elif key == "SR":                                   # 연구자 추가(46회차 · 결과 본 뒤 · 미리 적음): 연속 손절 뒤 쉬지 않고 '쉼' 동안 한 칸씩만
            SX_KW["stop_run"] = (nums[0], nums[1], nums[2], 4, 1)
        elif key == "BD":                                   # 연구자 추가: 시장 폭이 5거래일 전보다 x 넘게 떨어졌으면 새로 안 삼(강한 장이 꺾이는 때)
            _x = nums[0]; _dl = list(_IX.DAYS)
            _bd = {d: (nrl.BR.get(d) is not None and nrl.BR.get(_dl[i - 5]) is not None and nrl.BR[_dl[i - 5]] - nrl.BR[d] >= _x)
                   for d, i in _kd.items() if i >= 5}
            SX_FILT.append(lambda r, _b=_bd: not _b.get(r["date"], False))
        elif key == "KS":                                   # 연구자 추가(50회차 · 미리 적음): −4% 넘는 손절이 난 날 남은 종목 중 −x/10% 넘게 진 것도 함께 팜
            SX_KW["cosell"] = (4, nums[0] / 10)
        elif key == "PK":                                   # 검사 눈(일부러 미래 참조): n일 뒤 종가가 오늘보다 낮으면 안 삼 — s_cut.py가 잡아야 함
            _n = nums[0]
            SX_FILT.append(lambda r, _n=_n: not (r["i"] + _n < len(nrl.lanes[r["code"]]["closes"])
                                               and nrl.lanes[r["code"]]["closes"][r["i"] + _n] < nrl.lanes[r["code"]]["closes"][r["i"]]))
        elif key == "SZ":
            _z = nums[0] / 100
            SX_SIZE = lambda r, _z=_z: max(1, nrl.BASE_SIZE(r) // 2) if (r.get("변동성") or 0) > _z else nrl.BASE_SIZE(r)
    print(f"  손절 줄 설계 {SX} → 엔진 {list(SX_KW)} · 거르기 {len(SX_FILT)}개 · 크기 {'바꿈' if SX_SIZE else '그대로'}", flush=True)
HOLD = nrl.BASE_HOLD if not SX_FILT else (lambda r: nrl.BASE_HOLD(r) and all(f(r) for f in SX_FILT))


def stop_stats(trades, lo, hi):
    """손절 줄 재기: −4% 넘게 잃고 판 매매(손절 비슷) 수 · 10거래일 안 3번 넘게 몰린 무리 수 · 가장 긴 연속 손실(판 날 차례)."""
    import bisect as _bs
    sys.path.insert(0, "/home/user/stock-dash/research")
    import itools as _IT
    days = list(_IT.DAYS)          # 거래일 차례(2026-10-04 고침: 처음엔 '판 날'끼리 셌음)
    sold = sorted((t["판 날"], t["손익"]) for t in trades if lo <= t["판 날"] < hi and not t.get("나눠 팜"))
    stops = [d for d, g in sold if g <= -4]
    pos = [_bs.bisect_left(days, d) for d in stops]
    clusters, j = 0, 0
    while j < len(pos):
        k = j
        while k + 1 < len(pos) and pos[k + 1] - pos[j] < 10:
            k += 1
        if k - j + 1 >= 3:
            clusters += 1; j = k + 1
        else:
            j += 1
    run_ = best = 0
    for d, g in sold:
        run_ = run_ + 1 if g <= 0 else 0
        best = max(best, run_)
    return len(stops), clusters, best


# 1일봉 이익확보 · 고점추격 RNA(docs/RL-PX.md · 2026-10-05): I_PX="설계" · 정배열 매매에만 · 그날 종가와 그날까지 꼭대기 종가로만
#  LDU(10 → 3 · 15 → 5) · LDL(+ 20 → 10 · 30 → 18 · 50 → 32 · 100 → 70) · LF{f}_{s}(꼭대기 이익 s% 뒤 그 f% 아래면 팜) · TR{x}_{s}(꼭대기 이익 s% 뒤 꼭대기보다 x% 빠지면 팜)
#  TB{x}_{s}(큰 이익만 고점추격 · TR과 같은 셈) · PH{x}(처음 +x%에 닿는 날 절반)
#  끝에 V{p}를 붙이면 숫자 × (산 날 변동성 ÷ V0)^(p/100) · V0 = 2017 ~ 20 정배열 후보 변동성 가운데
PX = os.environ.get("I_PX", "")
if PX:
    import re as _rpx
    _mv = _rpx.search(r"V(\d+)$", PX)
    _pp = int(_mv.group(1)) / 100 if _mv else 0.0
    _body = PX[:_mv.start()] if _mv else PX
    _v0 = float(np.median([r["변동성"] for r in nrl.early[::5] if r.get("변동성") is not None and nrl.aligned(r)]))
    _LADDER = {"LDU": [(10, 3), (15, 5)], "LDL": [(10, 3), (15, 5), (20, 10), (30, 18), (50, 32), (100, 70)]}
    _m = _rpx.match(r"(LDU|LDL|LF|TR|TB|PH)(\d*)_?(\d*)", _body)
    _kind, _a, _b = _m.group(1), int(_m.group(2) or 0), int(_m.group(3) or 0)
    print(f"  이익확보 {PX} → {_kind} {_a} {_b} · RNA p {_pp} · V0 {_v0:.2f}", flush=True)
    _base_al = EXIT

    def _px_aligned(lane, start, price, step, peak, row=None):
        spot = start + step
        g = (lane["closes"][spot] / price - 1) * 100
        pg = (peak / price - 1) * 100
        k = (((row or {}).get("변동성") or _v0) / _v0) ** _pp if _pp else 1.0
        if _kind in _LADDER:
            for a, b in _LADDER[_kind]:
                if pg >= a * k and g <= b * k:
                    return True
        elif _kind == "LF":
            if pg >= _b * k and g <= pg * _a / 100:
                return True
        elif _kind in ("TR", "TB"):
            if pg >= _b * k and lane["closes"][spot] <= peak * (1 - _a * k / 100):
                return True
        elif _kind == "PH" and nrl.first_cross(lane, start, price, step, _a * k):
            out = nrl.broken(lane, start, price, step, peak, row)
            return True if out else max(1, nrl.BASE_SIZE(row) // 2)
        return nrl.broken(lane, start, price, step, peak, row)
    EXIT = lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": _px_aligned})

if SX_MX:
    _exit0 = EXIT

    def EXIT(lane, start, price, step, peak, row=None, _e=_exit0):
        day = lane["날"][start + step] if start + step < len(lane["날"]) else ""
        return True if day in SX_MX else _e(lane, start, price, step, peak, row)
# 미래 참조 자르기 · 더럽히기(손절 줄 연구 마지막 회차 · 2026-10-04): I_CUTDAY=YYYYMMDD
#  I_CUTMODE=cut   그날 뒤 종가 · 후보를 처음부터 없앰 / poison  그날 뒤 종가를 씨앗 고정 엉터리 걸음으로(길이 그대로)
#  → 그날까지 판 매매가 바뀌지 않아야 함(research/s_cut.py가 견줌)
_CUTDAY = os.environ.get("I_CUTDAY")
if _CUTDAY:
    import bisect as _bc
    _mode = os.environ.get("I_CUTMODE", "cut")
    _rng = np.random.default_rng(7)
    _sets = [lab.lanes(nrl.prices)] + ([nrl.lanes] if nrl.lanes is not lab.lanes(nrl.prices) else [])   # 엔진 것 · nrl 것 두 벌 모두(캐시에서 읽으면 다른 객체)
    for _ln in (ln for st in _sets for ln in st.values()):
        _kk = _bc.bisect_right(_ln["날"], _CUTDAY)
        if _mode == "cut":
            for _f in ("closes", "날", "중기선", "변동성"):
                _ln[_f] = _ln[_f][:_kk]
        elif _kk < len(_ln["closes"]) and _kk > 0:
            _rng = np.random.default_rng(abs(hash(_ln["code"])) % (2 ** 32))   # 두 벌에 같은 엉터리 값
            _x = _ln["closes"][_kk - 1] or 1.0
            for _j in range(_kk, len(_ln["closes"])):
                _x = _x * float(np.exp(_rng.normal(0, 0.03)))
                _ln["closes"][_j] = _x
    if _mode == "cut":
        nrl.early = [r for r in nrl.early if r["date"] <= _CUTDAY]
        nrl.inside = [r for r in nrl.inside if r["date"] <= _CUTDAY]
    print(f"  자르기 {_mode} {_CUTDAY}", flush=True)
out, LED = [], []
for side, since, pool in (("앞 2017 ~ 2020", rule.SINCE, nrl.early), ("뒤 2021 ~", rule.MID, nrl.inside)):
    g = lab.wobble(pool, nrl.prices, HOLD, EXIT, tries=8, rank=rule.order,
                   slots=nrl.SLOTS, since=since, apart=nrl.kin, realistic=True, cap=130, size=SX_SIZE or nrl.BASE_SIZE, detail=True, **SX_KW)
    if g and os.environ.get("I_DUMP_LEDGER"):      # 계좌 전체(i013) 시험용 매매 목록(x008 꼴 · 씨앗 0)
        LED.extend((t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for t in g["매매목록"]
                   if (side.startswith("앞") and t["산 날"] < rule.MID) or (side.startswith("뒤") and t["산 날"] >= rule.MID))
    if g and side.startswith("앞") and var == "DNA": print("열쇠", sorted(g.keys()), flush=True)
    _ss = ""
    if g and g.get("매매목록"):
        _lo, _hi = (rule.SINCE, rule.MID) if side.startswith("앞") else (rule.MID, "20260101")   # 2026은 잠금(손절 줄 연구 · 마지막에만 엶)
        _n, _c, _b = stop_stats(g["매매목록"], _lo, _hi)
        _ss = f" 손절 {_n} 무리 {_c} 연속 {_b}"
    out.append(f"{side} 연 {g['연수익']:+.1f} 골 {g.get('최대낙폭', g.get('골', float('nan')))} 매매 {g.get('매매', '?')}{_ss}" if g else f"{side} 없음")
if os.environ.get("I_DUMP_LEDGER"):
    import json as _json
    _json.dump(sorted(set(LED), key=lambda x: (x[1], x[0])), open(os.environ["I_DUMP_LEDGER"], "w"))
mid = [cut(d, 0.4) for d in sorted(by_day) if d >= "20170101"]
print(f"[{var}] " + " | ".join(out) + (f" | RNA40 문턱 범위 {min(mid):.2f} ~ {max(mid):.2f} (DNA {full:.2f})" if var == "RNA40" else ""), flush=True)
