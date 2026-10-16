"""손익 귀속 진단(GPT #451 1순위 · 보고만 · 규칙 안 바꿈): MIX-0054 기준(BASE = REPRO_G 바탕 + 덧붙임)의 날마다 NAV 변화를
바탕(1일봉 · 바구니 · 엔진 묶음) · 레버리지 ETF · 인버스 ETF · 맞춤 비용 · 덧붙임 넘침 정리로 나눔. regime_dev.account 원문을 그대로 쓰고
더하기 줄만 끼움(셈 순서 · 값은 같아야 함 → 끝 NAV가 원 함수와 같은지 확인). 달마다 합 = 그달 NAV 변화 ÷ 달 초 NAV."""
import inspect, json, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos21")
sys.argv = ["x"]
import mpos21 as P
Dv = P.Dv
src = inspect.getsource(Dv._RAW.__globals__["account"]) if False else inspect.getsource(Dv.account)
rep = [
 ("def account(cfg, lo=LO, hi=HI):", "def account_attr(cfg, lo=LO, hi=HI):\n    ATT = {}"),
 ("        vb *= base[d][0] / base[p][0]\n", "        _a = ATT.setdefault(d, {'바탕': 0.0, '레버리지': 0.0, '인버스': 0.0, '비용': 0.0, '정리 비용': 0.0, 'A0': vb + ve + cash})\n        _a['바탕'] += vb * (base[d][0] / base[p][0] - 1)\n        vb *= base[d][0] / base[p][0]\n"),
 ("            ve *= etf[code][d] / etf[code][p]\n", "            _a['레버리지' if code == '122630' else '인버스'] += ve * (etf[code][d] / etf[code][p] - 1)\n            ve *= etf[code][d] / etf[code][p]\n"),
 ("            A -= cost\n", "            A -= cost\n            _a['비용'] -= cost\n"),
 ("            cash += cut * (1 - COST_ETF)\n", "            cash += cut * (1 - COST_ETF)\n            _a['정리 비용'] -= cut * COST_ETF\n"),
 ("            cash += x * (1 - COST_BASE_DOWN)\n", "            cash += x * (1 - COST_BASE_DOWN)\n            _a['정리 비용'] -= x * COST_BASE_DOWN\n"),
 ("    return navs, nst", "    return navs, nst, ATT"),
]
for a, b in rep:
    assert src.count(a) == 1, a
    src = src.replace(a, b)
exec(compile(src, "account_attr", "exec"), Dv.__dict__)
f = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos21/base_BASE.csv"
from pathlib import Path
Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(f), None, None
navs, nst, att = Dv.account_attr(dict(P.M.CFG))
Dv.DATA, Dv.FEAT = None, None
ref = P.acct(f)
assert navs == ref, "원 함수와 NAV가 다름"
ds = sorted(navs)
mon = {}
for d in ds[1:]:
    m = d[:6]
    x = mon.setdefault(m, {"달초": None, "바탕": 0.0, "레버리지": 0.0, "인버스": 0.0, "비용": 0.0, "정리 비용": 0.0, "국면 날": {}})
    a = att[d]
    if x["달초"] is None:
        x["달초"] = a["A0"]
    for k in ("바탕", "레버리지", "인버스", "비용", "정리 비용"):
        x[k] += a[k]
    x["국면 날"][nst[d]] = x["국면 날"].get(nst[d], 0) + 1
full = P.M.mstats(navs)["달"]
out = {}
for m, x in mon.items():
    if not ("201703" <= m <= "202608"):
        continue
    parts = {k: x[k] / x["달초"] * 100 for k in ("바탕", "레버리지", "인버스", "비용", "정리 비용")}
    out[m] = {"달 수익 %": full[m] * 100, **{k: round(v, 3) for k, v in parts.items()}, "국면 날": x["국면 날"]}
json.dump(out, open("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/attr/attr.json", "w"), ensure_ascii=False, indent=1)
loss = [m for m in out if out[m]["달 수익 %"] < 0]
def tag(m):
    o = out[m]
    nb = o["달 수익 %"] - o["바탕"]       # 덧붙임 몫(레버리지 + 인버스 + 비용) — 달 초 기준 단순 합이라 복리 차이 조금 있음
    return "바탕만으로도 손실" if o["바탕"] < 0 and nb >= 0 else "덧붙임 때문에 손실(바탕은 +)" if o["바탕"] >= 0 else "둘 다 −"
cnt = {}
for m in loss:
    cnt[tag(m)] = cnt.get(tag(m), 0) + 1
print("손실 달", len(loss), cnt)
for k in ("레버리지", "인버스", "비용", "바탕"):
    print(k, "손실 달 합 %", round(sum(out[m][k] for m in loss), 2), "전체 합 %", round(sum(out[m][k] for m in out), 2))
for m in ("202603", "202607"):
    print(m, out[m])
print("덧붙임 때문에 손실(바탕은 +) 달:", [m for m in loss if tag(m).startswith("덧붙임")])
