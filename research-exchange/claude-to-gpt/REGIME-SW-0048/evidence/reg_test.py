"""REGIME-SW-0048 합성 시험 — 가짜 자료로 계좌 셈 · 바꿈 시점 · 비용 · 넘침 덜기 · 버팀 · 판정 · 기록."""
import json, re, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/home/user/stock-dash/research")
import regime_dev as D
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
days = []
for y in range(2016, 2019):
    for m in range(1, 13):
        for dd in range(1, 22):
            days.append(f"{y}{m:02d}{dd:02d}")
def setup(ix_fn, base_fn=lambda t: 1.0 * 1.001 ** t, cash_fn=lambda t: 0.5, inv_fn=None, lev_fn=None):
    base = {d: (base_fn(t), cash_fn(t)) for t, d in enumerate(days)}
    ix = {d: ix_fn(t) for t, d in enumerate(days)}
    inv = {d: (inv_fn(t) if inv_fn else 10000 / ix_fn(t)) for t, d in enumerate(days)}
    etf = {"069500": ix, "114800": inv, "252670": inv, "122630": {d: (lev_fn(t) if lev_fn else ix_fn(t) ** 2) for t, d in enumerate(days)}}
    D.DATA = (base, etf, {}, {})
    D.FEAT = None
    D.LO, D.HI = days[260], days[-1]
flat = lambda t: 100.0
setup(flat)
nav, st = D.account(D.R0, D.LO, D.HI)
ds = sorted(nav)
check("1 R0(1일봉만) = 1일봉 장부를 처음 1로 맞춘 것", all(abs(nav[d] - 1.001 ** (days.index(d) - 260)) < 1e-9 for d in ds))
# 하락: 069500이 260일부터 꾸준히 내림 → 60일선 아래 → 하락 판정
drop = lambda t: 100.0 if t < 200 else 100.0 * 0.995 ** (t - 200)
setup(drop, base_fn=lambda t: 1.0, cash_fn=lambda t: 0.0)
cfg = dict(D.R0, down_base=0.0, down_inv=1.0)
nav, st = D.account(cfg, D.LO, D.HI)
ds = sorted(nav)
check("2 하락 판정이면 1일봉을 모두 빼고 인버스 100%(1일봉 장부가 평평해도 NAV가 오름)", nav[ds[-1]] > 1.2 and st[ds[5]] == "하락")
# 바꿈 시점: 첫날(p=ds[0]) 판정 → ds[1] 종가에 바꿈 → ds[1]의 수익은 옛 몫(1일봉=평평)
first = nav[ds[1]]
check("3 판정 다음 날 종가에 바꿈: 바꾼 날 NAV = 1 − 비용(1일봉 줄임 0.30% + 인버스 삼 0.05%)", abs(first - (1 - 0.003 - 0.0005)) < 1e-9)
check("4 바꾼 다음 날부터 인버스 수익을 받음", abs(nav[ds[2]] / nav[ds[1]] - (1 / 0.995)) < 1e-9)
# 넘침 덜기: 상승장 · 레버리지 0.6 · 1일봉 현금이 0.6 → 0.1로 줄면 ETF를 팔아야 함
rise = lambda t: 100.0 * 1.002 ** t
setup(rise, base_fn=lambda t: 1.0, cash_fn=lambda t: 0.6 if t < 300 else 0.1, lev_fn=lambda t: 100.0)
cfg = dict(D.R0, up_lev=0.6, up_need="above_only")
nav, st = D.account(cfg, D.LO, D.HI)
check("5 1일봉 현금이 줄면 넘친 ETF를 그날 팖(덜기 횟수 > 0)", D.account.trims > 0)
check("6 레버리지 값이 평평하면 NAV는 비용만큼만 줄어듦(빚 없음 · 1 이하)", max(nav.values()) <= 1.0 + 1e-12)
# 버팀 날 수
f_down = {"close": 90, "ma60": 100}
f_up = {"close": 110, "ma60": 100, "ma60_20ago": 90}
feat = {f"2020{k:04d}": (f_down if k % 2 else f_up) for k in range(1, 21)}
st1 = D.states(feat, dict(D.R0, persist=1))
st3 = D.states(feat, dict(D.R0, persist=3))
check("7 버팀 1이면 날마다 바뀜 · 버팀 3이면 번갈아 나오는 판정으로는 안 바뀜(처음 '횡보' 그대로)", len(set(st1.values())) == 2 and set(st3.values()) == {"횡보"})
# 판정 조건
f = {"close": 90, "ma60": 100, "breadth": 45, "F20": -1, "I20": 0.5, "vol_ratio": 1.2}
check("8 확인 조건: br40은 폭 45라 하락 아님(횡보) · F20neg는 하락", D.raw_state(f, dict(D.R0, confirm="br40")) == "횡보" and D.raw_state(f, dict(D.R0, confirm="F20neg")) == "하락")
check("9 FI20neg: 외국인 −1 + 기관 0.5 = −0.5 < 0 → 하락 · vol15: 1.2라 아님", D.raw_state(f, dict(D.R0, confirm="FI20neg")) == "하락" and D.raw_state(f, dict(D.R0, confirm="vol15")) == "횡보")
g = {"close": 110, "ma60": 100, "ma60_20ago": 105, "breadth": 55}
check("10 상승 조건: ma_rising(100 < 105라 아님 → 횡보) · above_only(상승) · br50(55 → 상승)",
      D.raw_state(g, dict(D.R0, up_need="ma_rising")) == "횡보" and D.raw_state(g, dict(D.R0, up_need="above_only")) == "상승" and D.raw_state(g, dict(D.R0, up_need="br50")) == "상승")
check("11 이동평균이 아직 없으면 횡보(판정 안 함)", D.raw_state({"close": 1}, D.R0) == "횡보")
# 특징이 그날까지 값만: 마지막 날 값을 바꿔도 그 앞 날 특징은 같음
setup(drop)
fa = D.features(*[D.DATA[1], {}, {}])
etf2 = dict(D.DATA[1]); etf2["069500"] = dict(etf2["069500"]); etf2["069500"][days[-1]] = 1.0
fb = D.features(etf2, {}, {})
check("12 마지막 날 값을 바꿔도 그 앞 날 특징은 한 칸도 안 바뀜", all(fa[d] == fb[d] for d in days[:-1]) and fa[days[-1]] != fb[days[-1]])
# stats: 세 장 · 반
navs = {d: 1.0 for d in ["20170102", "20170103", "20180102", "20180103", "20220103", "20220104", "20230102", "20230103"]}
navs["20180103"] = 0.9
r = D.stats(navs, {d: "횡보" for d in navs})
check("13 세 장 성적표: 2018(하락 해) 하루 −10%가 하락 칸에 · 손실 한도 안", r["by_kind"]["하락"]["worst_day_pct"] == -10.0 and r["loss_ok"])
# 기록: STARTED 먼저 · 실패도 기록 · 상한
tmp = Path(tempfile.mkdtemp()); D.EVALS = tmp / "e.jsonl"
real = D.account
def boom(*a, **k):
    raise RuntimeError("시험 실패")
D.account = boom
try:
    D.evaluate(D.R0, "시험")
except RuntimeError:
    pass
recs = [json.loads(l) for l in D.EVALS.read_text().splitlines()]
check("14 셈 전에 STARTED · 실패하면 FAILED 기록", [x["status"] for x in recs] == ["STARTED", "FAILED"])
D.account = real
D.EVALS.write_text("".join(json.dumps({"status": "STARTED"}) + "\n" for _ in range(300)))
try:
    D.evaluate(D.R0, "넘침"); capped = False
except SystemExit as e:
    capped = "상한" in str(e)
check("15 STARTED 300개면 더 못 셈", capped)
src = Path(D.__file__).read_text()
check("16 바꿈은 전날 판정(st.get(p))으로 · 오늘 판정(st[d])으로 오늘 바꾸지 않음", "s_prev = st.get(p" in src and "st.get(d" not in src and re.search(r"(?<![a-z])st\[d\]", src) is None)
print(f"모두 {ok}개 통과")
