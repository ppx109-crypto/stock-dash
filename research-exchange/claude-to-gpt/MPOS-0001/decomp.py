"""MPOS-0001 해부 — MIX-0054 날 손익을 봇별로 나누고 달 · 국면별 표(고르기 없음 · 판정 없음).
덧붙임 기여 = 판 하루 수익 − 바탕 하루 수익(AUDIT-MIX54-0066과 같은 셈). 바탕 봇별 = 바탕 하루 수익을 Z_ATTR 봇별 손익 비율로 나눔."""
import csv, json, os, sys, collections, statistics as S
os.chdir("/home/user/stock-dash"); sys.path.insert(0, "research")
os.environ.setdefault("REG_BOX", "AUDIT-MIX54-0066")
import mix54_run as M, regime_dev as Dv
Dv.BASE_CSV = M.BASES / f"{M.name((0.5, 0.3))}.csv"; Dv.DATA, Dv.FEAT = None, None
navs, nst = Dv.account(dict(Dv.R0, **M.OVERLAYS["L0.4_S0.4"])); base, etf, br, flow = Dv.data(); ds = sorted(navs)
b0 = {d: base[d][0] / base[ds[0]][0] for d in ds}
att = {r["날"]: r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8"))}
BOTS = ["1d", "basket", "engine", "inverse", "park", "15m"]
day = {}
for j in range(1, len(ds)):
    p, d = ds[j - 1], ds[j]
    r = navs[d] / navs[p] - 1; rb = b0[d] / b0[p] - 1
    a = att.get(d); parts = {k: 0.0 for k in BOTS}
    if a and float(a["NAV전"]) > 0:
        raw = {k: float(a[k] or 0) / float(a["NAV전"]) for k in BOTS}; tot = sum(raw.values())
        parts = {k: (raw[k] / tot * rb if abs(tot) > 1e-12 else 0.0) for k in BOTS}
    day[d] = dict(r=r, add=r - rb, **parts, st=nst.get(d, "?"))
mon = collections.defaultdict(lambda: collections.defaultdict(float)); mst = collections.defaultdict(collections.Counter)
for d, v in day.items():
    m = d[:6]; mon[m]["r"] = (1 + mon[m]["r"]) * (1 + v["r"]) - 1
    for k in ["add"] + BOTS: mon[m][k] += v[k]
    mst[m][v["st"]] += 1
full = [m for m in sorted(mon) if "201703" <= m <= "202608"]
loss = [m for m in full if mon[m]["r"] < 0]
print(f"달 {len(full)} · 손실 달 {len(loss)}")
def dom(m): return mst[m].most_common(1)[0][0]
print("국면(그달 날 수 최다)별: 달 수 · 손실 달 · 비율 · 평균 달 수익 · 봇별 평균 기여 %p(덧붙임 1일봉 바구니 엔진 인버스)")
for s in ("상승", "횡보", "하락"):
    ms = [m for m in full if dom(m) == s]; ls = [m for m in ms if m in loss]
    if not ms: continue
    av = lambda k: S.mean(mon[m][k] for m in ms) * 100
    print(f"  {s}: {len(ms)}달 · 손실 {len(ls)} · {len(ls)/len(ms)*100:.0f}% · 평균 {av('r'):+.2f}% · " + " ".join(f"{k} {av(k):+.2f}" for k in ["add", "1d", "basket", "engine", "inverse"]))
print("손실 달마다 가장 크게 끌어내린 봇(기여 가장 낮은 것):", collections.Counter(min(["add", "1d", "basket", "engine", "inverse"], key=lambda k: mon[m][k]) for m in loss))
print("손실 달 · 이익 달 봇별 평균 기여 %p")
for nm, ms in (("손실", loss), ("이익", [m for m in full if m not in loss])):
    print(f"  {nm}: " + " ".join(f"{k} {S.mean(mon[m][k] for m in ms)*100:+.2f}" for k in ["add", "1d", "basket", "engine", "inverse"]))
# 뭉침: 손실 달 안에서 같은 날 둘 이상 봇이 함께 −인 날 몫
def clump(ms):
    dd = [v for d, v in day.items() if d[:6] in ms]
    return sum(1 for v in dd if sum(1 for k in ["add", "1d", "basket"] if v[k] < -0.002) >= 2) / len(dd) * 100
print(f"뭉침(덧붙임 · 1일봉 · 바구니 중 둘 이상이 같은 날 −0.2%p 넘게 −): 손실 달 {clump(set(loss)):.1f}% · 이익 달 {clump(set(full)-set(loss)):.1f}%")
print("손실 달 목록(달 수익 · 국면 · 봇별):")
for m in loss:
    print(f"  {m} {mon[m]['r']*100:+.1f}% {dict(mst[m])} " + " ".join(f"{k}{mon[m][k]*100:+.1f}" for k in ["add", "1d", "basket", "engine", "inverse"]))
json.dump({"day": day, "full": full}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "decomp_out.json"), "w"))
