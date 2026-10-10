"""SIG-MAP-0045 합성 시험 — 작은 가짜 스냅샷으로 셈 · 판정 · 잠금 · 영수증을 확인."""
import json, os, pickle, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/home/user/stock-dash/research")
import sig_map as G
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)

tmp = Path(tempfile.mkdtemp())
days = [f"2010{m:02d}{d:02d}" for m in range(1, 13) for d in range(1, 29)][:300]
codes = [f"{k:06d}" for k in range(60)]
prices, rows, flow = {}, [], {}
for n, c in enumerate(codes):
    xs = [100 * (1 + 0.001 * n) ** t for t in range(len(days))]          # 번호가 클수록 꾸준히 더 오름
    prices[c] = {"name": c, "rows": list(zip(days, xs))}
    fd = days[:]
    acc = {k: [0.0] for k in G.json.loads('["개인","외국인","기관","투신","연기금","사모"]')}
    okc = [0]
    for t in range(len(fd)):
        for k in acc:
            v = {"외국인": n, "투신": 1.0, "개인": -n}.get(k, 0.0)
            acc[k].append(acc[k][-1] + v)
        okc.append(okc[-1] + 1)
    flow[c] = (fd, acc, okc)
for i, d in enumerate(days):
    if i >= 120:
        for c in codes:
            rows.append({"code": c, "date": d, "i": i, "price": prices[c]["rows"][i][1], "거래대금20": 1e6})
ix = {d: 100.0 * (1.001 ** i) for i, d in enumerate(days)}
snap = {"from": days[0], "cut": days[-1], "prices": prices, "rows": rows, "br": {}, "flow": flow, "ix": ix}
p = tmp / "s.pkl"
p.write_bytes(pickle.dumps(snap))
res = G.spreads((str(p), days[0], days[-1]))
check("1 오름이 큰 종목이 앞날도 더 오름 → S1 벌어짐 > 0", all(v > 0 for v, _ in res["S1_MOM20"].values()))
check("2 단기 되돌림 S2는 반대 → 벌어짐 < 0", all(v < 0 for v, _ in res["S2_REV5"].values()))
check("3 수급 S5(외국인 = 번호) → 벌어짐 > 0", all(v > 0 for v, _ in res["S5_FLOW_FT10"].values()))
check("4 개인 반대 S6(개인 = −번호) → 벌어짐 > 0", all(v > 0 for v, _ in res["S6_RETAIL_CONTRA10"].values()))
check("5 국면: 069500 60일 +6%대 → 오름", {ph for _, ph in res["S1_MOM20"].values()} == {"오름"})
check("6 S7: 모두 정배열이면 0점 무리 < 5 → 날 없음", len(res["S7_EMA_ALIGN"]) == 0)
last = max(res["S1_MOM20"])
check("7 끝 10 + 1거래일은 앞날 값 없어 빠짐", days.index(last) == len(days) - 12)
# flow_val 손셈
s, lanes, ixd = G.load(str(p))
r = [x for x in rows if x["code"] == codes[3] and x["date"] == days[200]][0]
want = sum((3 + 1.0) * lanes[codes[3]]["x"][j] for j in range(191, 201)) / 1e6
check("8 flow_val = 10일 (외국인+투신) 수량 × 그날 종가 / 20일 평균 거래대금", abs(G.flow_val(s, lanes[codes[3]], r, ("외국인", "투신"), 1) - want) < 1e-9)
# 판정
def fake(vals_by_year, ph="횡보"):
    return {f"{y}0601": (v, ph) for y, v in vals_by_year.items()}
yrs = [str(y) for y in range(2006, 2022)]
base = {k: fake({y: 0.01 for y in yrs}) for k in G.SIGS}
for k in G.SIGS:
    base[k].update({f"{y}0602": (0.01, "오름") for y in yrs}); base[k].update({f"{y}0603": (0.01, "내림") for y in yrs})
t, pick = G.map_table(base)
check("9 모두 +면 STABLE · S5 · S6은 고르지 않음 · 같으면 표 앞 신호(S1)", all(t[k]["STABLE"] for k in G.SIGS) and pick == "S1_MOM20")
b2 = dict(base); b2["S1_MOM20"] = {d: ((-0.01 if d[:4] in yrs[:5] else 0.01), ph) for d, (v, ph) in base["S1_MOM20"].items()}
t, pick = G.map_table(b2)
check("10 11/16해만 + → STABLE 아님(조건 ①)", not t["S1_MOM20"]["STABLE"] and t["S1_MOM20"]["years_pos"] == "11/16" and pick == "S2_REV5")
b3 = dict(base); b3["S2_REV5"] = {d: ((-0.05 if ph == "내림" else 0.01), ph) for d, (v, ph) in base["S2_REV5"].items()}
t, _ = G.map_table(b3)
check("11 내림 국면 평균 − → STABLE 아님(조건 ②)", not t["S2_REV5"]["c2_all_phases_pos"] and not t["S2_REV5"]["STABLE"])
b4 = dict(base); b4["S3_HIGH120"] = {d: ((-0.02 if d < "20140101" else 0.03), ph) for d, (v, ph) in base["S3_HIGH120"].items()}
t, _ = G.map_table(b4)
check("12 앞 시대 평균 − → STABLE 아님(조건 ③)", not t["S3_HIGH120"]["c3_both_eras_pos"])
b5 = {k: {d: (-0.01, ph) for d, (v, ph) in base[k].items()} for k in G.SIGS}
b5["S5_FLOW_FT10"] = base["S5_FLOW_FT10"]
t, pick = G.map_table(b5)
check("13 STABLE이 수급 S5뿐이면 고를 것 없음", t["S5_FLOW_FT10"]["STABLE"] and pick is None)
b6 = dict(base); b6["S4_LOWVOL60"] = {d: (0.05, ph) for d, (v, ph) in base["S4_LOWVOL60"].items()}
t, pick = G.map_table(b6)
check("14 두 시대 작은 쪽이 가장 큰 신호를 고름", pick == "S4_LOWVOL60")
# 잠금 · 영수증
G.LOCK = tmp / "lock.json"; G.RECEIPT = tmp / "rc.json"
G.LOCK.write_text(json.dumps({"research/sig_map.py": "다름"}))
try:
    G.run_t(); bad = False
except SystemExit as e:
    bad = "잠금이 다름" in str(e)
check("15 잠금이 다르면 셈 전에 멈춤 · 영수증 없음", bad and not G.RECEIPT.exists())
G.RECEIPT.write_text("{}")
try:
    fd = os.open(str(G.RECEIPT), os.O_CREAT | os.O_EXCL | os.O_WRONLY); again = True
except FileExistsError:
    again = False
check("16 영수증은 O_EXCL — 이미 있으면 다시 못 만듦", not again)
src = Path(G.__file__).read_text()
check("17 지도 셈(M_PARTS)에 시험 스냅샷 경로 없음", "sig-t" not in json.dumps(G.M_PARTS) and G.T_PART[0] == "/tmp/sig-t.pkl")
check("18 T 기간 · 지도 기간 겹치지 않음", G.M_PARTS[-1][2] < G.T_PART[1])
# round 2(GPT #202 6096764654): 순서 시험 — 영수증이 어떤 성과 셈보다 먼저
G.LOCK = tmp / "lock2.json"; G.LOCK.write_text(json.dumps(G.lock_body()))
calls = []
real_merge = G.merge
def spy(parts, only=None):
    calls.append(G.RECEIPT.exists())
    raise RuntimeError("셈 멈춤(시험)")
G.merge = spy
G.RECEIPT = tmp / "rc_exist.json"; G.RECEIPT.write_text("{}")
try:
    G.run_t(); why = ""
except SystemExit as e:
    why = str(e)
check("19 영수증이 이미 있으면 merge · map_table 전에 멈춤", "영수증이 이미 있음" in why and calls == [])
G.RECEIPT = tmp / "rc_new.json"
try:
    G.run_t()
except RuntimeError:
    pass
rc = json.loads(G.RECEIPT.read_text())
check("20 새 영수증은 M 셈(merge) 첫 호출 때 이미 있음 · pick 칸은 null", calls == [True] and rc["status"] == "STARTED" and rc["pick"] is None)
sys.argv = ["sig_map.py"]
try:
    G.main(); why = ""
except SystemExit as e:
    why = str(e)
check("21 깃발 없이(또는 --map) 돌리면 성과 셈 없이 거부", "영수증 없는 성과 셈은 없음" in why and calls == [True])
G.merge = real_merge
check("22 통과 이름은 재사용 구간 한정 · 독립 확인 칸 고정", "STABLE_IN_REUSED_T" in src or "STABLE_IN_REUSED_T" in Path(G.__file__).read_text())
src2 = Path(G.__file__).read_text()
check("23 옛 이름 STABLE_SIGNAL_CONFIRMED 없음 · independent_validation WAITING_DATA 있음", "STABLE_SIGNAL_CONFIRMED" not in src2 and '"independent_validation": "WAITING_DATA"' in src2)
print(f"모두 {ok}개 통과")
