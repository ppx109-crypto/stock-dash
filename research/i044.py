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
elif var[:2] in ("RS", "RX", "HS", "HV", "VS", "VX", "OS", "MS", "CQ", "MV", "OV", "AV", "AH", "AC", "AO", "XV", "YV") or var.startswith("RALL"):
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
    m6 = _re6.match(r"XV(\d+)([ATSD]?)", var)
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
        return nrl.half_rule(first=fi, take=tk, stop=st, days=dy)(lane, start, price, step, peak, row)
    EXIT = lab.exit_per_tier(nrl.tier, {"규칙": _rule_exit, "정배열": nrl.broken})
# 16라운드 D7 ② 정배열 팔기(손절 −10% · 한때 +8% 닿은 뒤 +1% 아래면 팜 · 정배열 깨지면 팜) RNA:
#  YV{p}[A|S|B]: k = (산 날 변동성 ÷ V0)^(p/100) · V0 = 앞 기간 정배열 문 통과 날 변동성 가운데값 · A 모두 × k · S 손절만 · B 본전 지키기(+8 · +1)만
if var.startswith("YV"):
    import re as _re7
    m7 = _re7.match(r"YV(\d+)([ASB]?)", var)
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
        spot = start + step
        close = lane["closes"][spot]
        if (close / price - 1) * 100 <= -st:
            return True
        if (peak / price - 1) * 100 >= hi and (close / price - 1) * 100 <= lo:
            return True
        return not nrl.shape[lane["code"]]["정배열"][spot]
    EXIT = lab.exit_per_tier(nrl.tier, {"규칙": nrl.RULE_EXIT, "정배열": _broken})
out, LED = [], []
for side, since, pool in (("앞 2017 ~ 2020", rule.SINCE, nrl.early), ("뒤 2021 ~", rule.MID, nrl.inside)):
    g = lab.wobble(pool, nrl.prices, nrl.BASE_HOLD, EXIT, tries=8, rank=rule.order,
                   slots=nrl.SLOTS, since=since, apart=nrl.kin, realistic=True, cap=130, size=nrl.BASE_SIZE, detail=True)
    if g and os.environ.get("I_DUMP_LEDGER"):      # 계좌 전체(i013) 시험용 매매 목록(x008 꼴 · 씨앗 0)
        LED.extend((t["code"], t["산 날"], t["판 날"], t["손익"], t.get("자리") or 1) for t in g["매매목록"]
                   if (side.startswith("앞") and t["산 날"] < rule.MID) or (side.startswith("뒤") and t["산 날"] >= rule.MID))
    if g and side.startswith("앞") and var == "DNA": print("열쇠", sorted(g.keys()), flush=True)
    out.append(f"{side} 연 {g['연수익']:+.1f} 골 {g.get('최대낙폭', g.get('골', float('nan')))} 매매 {g.get('매매', '?')}" if g else f"{side} 없음")
if os.environ.get("I_DUMP_LEDGER"):
    import json as _json
    _json.dump(sorted(set(LED), key=lambda x: (x[1], x[0])), open(os.environ["I_DUMP_LEDGER"], "w"))
mid = [cut(d, 0.4) for d in sorted(by_day) if d >= "20170101"]
print(f"[{var}] " + " | ".join(out) + (f" | RNA40 문턱 범위 {min(mid):.2f} ~ {max(mid):.2f} (DNA {full:.2f})" if var == "RNA40" else ""), flush=True)
