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
check("9 다시 맞춤 조건에 drift(몫 차 > band)가 들어 있음 · 판정은 전날 특징(feat.get(p))으로", "or drift:" in src and "targets(s_prev, cfg, feat.get(p))" in src)
# 실행기
check("10 1단계 격자 = 상한 9 × 목표 흔들림 7 = 63 · 출발 판정기 = 0048 최종", len(RR.CAPS) * len(RR.VTS) == 63 and all(RR.START[k] == F48[k] for k in F48 if k != "up_lev"))
check("11 down_inv를 바꾸면 하락 1일봉 몫도 같이 맞춤(0 → 1.0 · 0.3 → 0.5)", RR.change(RR.START, "down_inv", 0.3)["down_base"] == 0.5 and RR.change(RR.START, "down_inv", 0.0)["down_base"] == 1.0)
check("12 받아들이기 · 고원은 반올림 전 값", RR.better({"annual_raw": 0.203001, "loss_ok": True}, {"annual_raw": 0.2}) and not RR.better({"annual_raw": 0.203, "loss_ok": True}, {"annual_raw": 0.2}))
print(f"모두 {ok}개 통과")
