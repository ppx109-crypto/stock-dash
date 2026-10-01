"""15분봉 51회차(T4 · 세 갈래 성적표 ③) — 같은 후보(다음 날 봉에 붙은 일봉 재료로 문이 열린 종목 · 날)를
① 전날 종가에 사기 ② 그날 1시간봉 EMA 정배열 된 정시(없으면 12:00) ③ 그날 15분봉 최종 후보 신호(15분봉 정배열 · 없으면 11:00 · +2% · 시장 −1% 거르기)
로 사고, 같은 15분봉 파는 규칙(exit_rule)으로 신호 하나하나 손익(비용 0.30%). 한투 15분봉 1년 · 두 반."""
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('\npart = os.environ')[0])
exec("def solo" + open("/home/user/stock-dash/research/q019.py", encoding="utf-8").read().split("def solo", 1)[1].split("al_cache = ")[0])
import m15lab as M2
HD = M2.to_hours({c: b for c, b in data.items()})
HIDX = {c: {t: i for i, t in enumerate(b["t"])} for c, b in data.items()}
FIN = {c: FINsig for c, FINsig in ((c, entry3(al_mkt=-0.01)(c, b)) for c, b in data.items())}


def solo_at(c, i, price):
    b = data[c]
    p = {"price": price, "i": i, "칸": 4, "처음칸": 4, "peak": price, "now": i, "code": c}
    left, got = 1.0, 0.0
    for j in range(i, len(b["t"]) - 1):
        p["peak"] = max(p["peak"], b["c"][j]); p["now"] = j
        n = exit_rule(c, b, p, j)
        if not n:
            continue
        part = left if n == "all" else min(left, n / 4)
        got += part * (b["o"][j + 1] / price - 1) * 100
        left -= part; p["칸"] = max(1, round(left * 4))
        if left <= 1e-9:
            break
    if left > 1e-9:
        got += left * (b["c"][-1] / price - 1) * 100
    return got - H.COST


rows = []
for c, b in data.items():
    t = b["t"]
    hb = HD.get(c)
    hs = H.states(c + "_h", hb, "A")["정배열"] == 1 if hb else None
    hcross = {hb["t"][k] for k in range(1, len(hb["t"])) if hs[k] and not hs[k - 1]} if hb else set()
    first_of = {}
    for k, s in enumerate(t):
        first_of.setdefault(s[:8], k)
    for d1, k0 in first_of.items():
        if k0 == 0 or not ("202509170000" <= t[k0] < "202609010000"):
            continue
        x = ATT[c][k0]
        if not (x and ok(x) and IN[c][k0]):
            continue
        r1 = solo_at(c, k0, b["c"][k0 - 1])
        # ② 1시간봉: 그날 정시 봉이 정배열 된 1시간봉이면 다음 정시 시가 · 없으면 12:00
        hh_buy = None
        for hh in ("0900", "1000", "1100", "1200", "1300"):
            if d1 + hh[:2] + "00" in hcross:
                hh_buy = f"{int(hh[:2]) + 1:02d}00"
                break
        hh_buy = hh_buy or "1200"
        i2 = HIDX[c].get(d1 + hh_buy)
        r2 = solo_at(c, i2, b["o"][i2]) if i2 is not None else None
        ks = [k for k in range(k0, min(len(t), k0 + 26)) if t[k][:8] == d1 and FIN[c][k]]
        r3 = solo_at(c, ks[0] + 1, b["o"][ks[0] + 1]) if ks and ks[0] + 1 < len(t) else None
        rows.append(("앞" if t[k0] < "202604010000" else "뒤", r1, r2, r3))
print(f"== 15분봉 51회차(T4 ③): 같은 후보, 사는 때 셋 · 같은 15분봉 파는 규칙 (후보 {len(rows)}건) ==", flush=True)
for side in ("앞", "뒤", "모두"):
    R = [r for r in rows if side == "모두" or r[0] == side]
    for i, name in ((1, "전날 종가"), (2, "1시간봉 정시"), (3, "15분봉 후보 신호")):
        v = [r[i] for r in R if r[i] is not None]
        if v:
            print(f"  {side} {name}: 평균 {statistics.mean(v):+.2f} · 가운데 {statistics.median(v):+.2f} · 이김 {sum(x > 0 for x in v) / len(v) * 100:.0f}% ({len(v)}건)", flush=True)
print("끝", flush=True)
