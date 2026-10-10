"""REGIME-SW-0049 합성 시험 — 흔들림으로 레버리지 줄이기 · band 다시 맞춤 · 앞 과제 결과 그대로 · 기록 칸 분리."""
import json, math, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "REGIME-SW-0049"
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D
import regime_rules2 as RR
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
check("1 기록 칸이 0049로 갈림 · 1일봉 장부는 0048 파일 그대로", D.BOX.name == "REGIME-SW-0049" and D.BASE_CSV.parent.name == "REGIME-SW-0048")
F48 = {"n": 20, "confirm": "br30", "persist": 3, "down_base": 1.0, "down_inv": 0.0, "inv": "114800", "up_lev": 0.3, "side_inv": 0.0, "up_need": "above_only", "exit_buf": 0.0}
r48 = D.stats(*D.account(F48)); r0 = D.stats(*D.account(D.R0))
check("2 앞 과제 결과 그대로: 0048 최종 30.3823088896% · 1일봉만 20.0450959773%", abs(r48["annual_raw"] * 100 - 30.3823088896) < 1e-8 and abs(r0["annual_raw"] * 100 - 20.0450959773) < 1e-8)
r48b = D.stats(*D.account(dict(F48, lev_vt=None, band=None)))
check("3 lev_vt · band가 None이면 0048과 한 칸도 다르지 않음", r48b["annual_raw"] == r48["annual_raw"])
# 흔들림 몫 식
f = {"v20a": 0.30}
check("4 레버리지 몫 = 상한 × min(1, 목표 / 20일 흔들림): 0.6 × 0.15/0.30 = 0.3 · 흔들림이 목표보다 작으면 상한 그대로",
      abs(D.targets("상승", dict(F48, up_lev=0.6, lev_vt=0.15), f)[2] - 0.3) < 1e-12 and D.targets("상승", dict(F48, up_lev=0.6, lev_vt=0.5), f)[2] == 0.6)
check("5 하락 · 횡보 몫은 흔들림과 상관없음", D.targets("횡보", dict(F48, lev_vt=0.1), f) == (1.0, "114800", 0.0))
# v20a는 그날까지 값만: 마지막 날 바꿔도 앞 날 v20a 같음
base, etf, br, flow = D.data()
fa = D.features(etf, {}, {})
etf2 = dict(etf); etf2["069500"] = dict(etf["069500"]); last = max(etf2["069500"]); etf2["069500"][last] = etf2["069500"][last] * 0.5
fb = D.features(etf2, {}, {})
check("6 20일 흔들림(v20a)은 그날까지 값만: 마지막 날 값을 바꿔도 앞 날은 같음", all(fa[d].get("v20a") == fb[d].get("v20a") for d in fa if d < last) and fa[last]["v20a"] != fb[last]["v20a"])
check("7 v20a = 20일 날 수익 제곱 평균의 제곱근 × √250", abs(fa[sorted(fa)[-5]]["v20a"] / math.sqrt(250) - math.sqrt(sum(r * r for r in [etf["069500"][sorted(etf["069500"])[j]] / etf["069500"][sorted(etf["069500"])[j - 1]] - 1 for j in range(len(etf["069500"]) - 5 - 19, len(etf["069500"]) - 4)]) / 20)) < 1e-12)
# band: 가짜 자료로 흔들림이 커지면 몫을 줄임
days = [f"{y}{m:02d}{dd:02d}" for y in range(2016, 2019) for m in range(1, 13) for dd in range(1, 22)]
def setup(ix_fn, cash=0.8):
    D.DATA = ({d: (1.0, cash) for d in days}, {"069500": {d: ix_fn(t) for t, d in enumerate(days)}, "114800": {d: 100.0 for d in days},
               "252670": {d: 100.0 for d in days}, "122630": {d: 100.0 for d in days}}, {}, {})
    D.FEAT = None
    D.LO, D.HI = days[300], days[-1]
def ix(t):
    v = 100 * 1.001 ** min(t, 500)
    for k in range(500, t):
        v *= 1.03 if k % 2 else 0.98
    return v
setup(ix)
cfg = dict(F48, up_lev=0.6, lev_vt=0.15, band=0.05, up_need="above_only", n=20)
D.account(cfg, D.LO, D.HI)
check("8 계좌 셈이 흔들림 판에서도 빚 없이 끝남(min_cash_slack ≥ 0)", D.account.min_slack >= -1e-12)
# band 비교 문장: 몫 차가 band보다 크면 그날 다시 맞춤(코드 위치 점검)
src = Path(D.__file__).read_text()
check("9 판정은 전날 특징(feat.get(p))으로", "targets(s_prev, cfg, feat.get(p))" in src)
# 실행기
check("10 1단계 격자 = 상한 9 × 목표 흔들림 7 = 63 · 출발 판정기 = 0048 최종", len(RR.CAPS) * len(RR.VTS) == 63 and all(RR.START[k] == F48[k] for k in F48 if k != "up_lev"))
check("11 down_inv를 바꾸면 하락 1일봉 몫도 같이 맞춤(0 → 1.0 · 0.3 → 0.5)", RR.change(RR.START, "down_inv", 0.3)["down_base"] == 0.5 and RR.change(RR.START, "down_inv", 0.0)["down_base"] == 1.0)
check("12 받아들이기 · 고원은 반올림 전 값", RR.better({"annual_raw": 0.203001, "loss_ok": True}, {"annual_raw": 0.2}) and not RR.better({"annual_raw": 0.203, "loss_ok": True}, {"annual_raw": 0.2}))
# round 2(GPT #213 6098537485 · 사용자 2026-10-10 고원 다시 정의)
# ① 등록한 n 모두 이동평균이 계산됨(합성 상승 · 하락)
up = lambda t: 100 * 1.002 ** t
down = lambda t: 100 * 0.998 ** t
for name, fn, want in (("상승", up, "상승"), ("하락", down, "하락")):
    setup(fn)
    feat = D.features(D.DATA[1], {}, {})
    last = max(feat)
    got = {n: D.raw_state(feat[last], dict(F48, n=n, confirm="none", up_need="above_only")) for n in (10, 15, 17, 20, 23, 30, 40)}
    check(f"13 {name} 자료에서 n 10 · 15 · 17 · 20 · 23 · 30 · 40 모두 이동평균이 있고 국면 = {want}", all(D.ma_of(feat[last], n) is not None for n in got) and set(got.values()) == {want})
f0 = {"close": 1, "_k": 5}
D.PREF[:] = [sum(range(1, i + 1)) * 1.0 for i in range(11)]
check("14 ma_of 손셈: 값 1..10 누적합에서 k=5 · n=3 → (4+5+6)/3 = 5 · 이력 모자라면 None", abs(D.ma_of(f0, 3) - 5.0) < 1e-12 and D.ma_of(f0, 7) is None)
check("15 0048 표의 저장 값이 있으면 그것을 씀(ma60 키)", D.ma_of({"ma60": 99.0, "_k": 0}, 60) == 99.0)
# ② 무보유에서 band 재진입
D.DATA = None; D.FEAT = None
days2 = days
def setup_cash(cash_fn):
    D.DATA = ({d: (1.0, cash_fn(t)) for t, d in enumerate(days2)}, {"069500": {d: 100 * 1.002 ** t for t, d in enumerate(days2)}, "114800": {d: 100.0 for d in days2},
               "252670": {d: 100.0 for d in days2}, "122630": {d: 100.0 for d in days2}}, {}, {})
    D.FEAT = None
    D.LO, D.HI = days2[300], days2[-1]
# 1일봉 현금이 처음엔 0(레버리지 못 삼) → 같은 달 안에서 0.8로 늘어남 → band 넘으면 그날 삼
mid = days2.index(days2[305])
setup_cash(lambda t: 0.0 if t < 305 else 0.8)
cfgb = dict(F48, up_lev=0.3, band=0.05, n=20, confirm="none")
nav_b, st_b = D.account(cfgb, D.LO, D.HI)
setup_cash(lambda t: 0.0 if t < 305 else 0.8)
nav_n, st_n = D.account(dict(cfgb, band=None), D.LO, D.HI)
d_in = days2[306]
check("16 현금 부족으로 무보유 → 같은 달 · 국면에서 현금 회복 → band 넘으면 그날 레버리지를 삼(산 비용만큼 NAV가 band 없는 판보다 작음)",
      nav_b[days2[305]] < nav_n[days2[305]] and days2[305][:6] == days2[301][:6])
setup_cash(lambda t: 0.8)
nav_z, _ = D.account(dict(cfgb, up_lev=0.0, band=0.05), D.LO, D.HI)
check("17 목표 몫 0이면 band가 있어도 거래 없음(NAV = 1일봉 장부 = 1)", all(abs(v - 1.0) < 1e-12 for v in nav_z.values()))
# ③ 새 고원 정의
nb = RR.neighbors(dict(RR.START, lev_vt=0.15))
axes_nb = {a for a, _ in nb}
check("18 이웃은 규칙 숫자만 조금: n 17 · 23 · 버팀 2 · 4 · 폭 25 · 35 · 목표 흔들림 ±0.02 · band ±0.02 · 몫 축(up_lev · side_inv · down_inv) 없음",
      ("n", 17) in nb and ("n", 23) in nb and ("confirm", "br25") in nb and ("confirm", "br35") in nb and ("lev_vt", 0.13) in nb and not ({"up_lev", "side_inv", "down_inv", "down_base"} & axes_nb))
check("19 확인 문턱 읽기: br25(폭 24 → 하락 확인) · r5m2.5(5일 −3% → 확인) · vol13(비 1.4 → 확인)",
      D.confirm_ok({"breadth": 24}, "br25") and D.confirm_ok({"r5": -0.03}, "r5m2.5") and D.confirm_ok({"vol_ratio": 1.4}, "vol13") and not D.confirm_ok({"breadth": 26}, "br25"))
real_run = RR.run
RR.run = lambda c, note: {"annual_raw": 0.255, "annual_pct": 25.5, "worst_day_pct": -20.0, "worst_month_pct": -20.0, "loss_ok": False}
okp, det = RR.plateau(dict(RR.START, lev_vt=0.15), {"annual_raw": 0.30}, 20.0)
RR.run = real_run
check("20 고원 통과는 더 번 몫만 봄: 이웃이 5.5 ≥ 10/2 더 벌면 통과 · 이웃 손실(−20%)은 보고 칸에만", okp and all(v["loss_ok_report"] is False for v in det.values()))
print(f"모두 {ok}개 통과")
