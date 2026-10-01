"""15분봉 30회차 — 봉 값 잡음 세계(1시간봉 39 · 50회차 방식): 시가 · 종가에 잡음(09:00 칸 0.8% · 그 밖 0.3%, 고가 · 저가 안으로)을 넣은
세계 4개에서 0회차 · 최종 후보를 다시 셈(재료 · 이동평균 · 장중 시장 흐름도 그 세계 값으로). 씨앗 4. 161종목.
최종 후보가 잡음 세계에서도 0회차보다 두 반 모두 나으면 '값 흔들림에 버팀'."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('\npart = os.environ')[0])
REAL = data


def noisy(seed):
    rng = np.random.default_rng(seed)
    out = {}
    for c, b in REAL.items():
        n = len(b["t"])
        first = HH[c] == "0900"
        o = b["o"] * np.exp(rng.normal(0, np.where(first, 0.008, 0.003), n))
        cc = b["c"] * np.exp(rng.normal(0, 0.003, n))
        out[c] = {"t": b["t"], "o": np.clip(o, b["l"], b["h"]), "c": np.clip(cc, b["l"], b["h"]), "h": b["h"], "l": b["l"], "v": b["v"]}
    return out


print(f"== 15분봉 30회차: 봉 값 잡음 세계 ({len(REAL)}종목) ==", flush=True)
rows = []
for w in range(1, 5):
    D = noisy(w)
    data = D
    H._ST.clear()
    DR = {c: F.day_ret(b) for c, b in D.items()}
    MK = F.market(D)
    MKT = {c: np.array([MK.get(t, np.nan) for t in b["t"]]) for c, b in D.items()}
    got = []
    for tag, fn in (("0회차", entry()), ("최종 후보", entry3(al_mkt=-0.01))):
        sg = {c: np.asarray(fn(c, b), bool) for c, b in D.items()}
        res = M.simulate(D, lambda c, b, sg=sg: sg[c], exit_rule, size, rank=rank_plus(tiers(sg)), stale_of=stale90, seeds=4)
        got.append((res["앞"]["연"], res["뒤"]["연"], res["앞"]["골"], res["뒤"]["골"]))
    rows.append(got)
    print(f"  잡음 세계 {w}: 0회차 앞 {got[0][0]} · 뒤 {got[0][1]}  |  최종 후보 앞 {got[1][0]} · 뒤 {got[1][1]} (골 {got[1][2]} · {got[1][3]})", flush=True)
win = sum(1 for g in rows if g[1][0] > g[0][0] and g[1][1] > g[0][1])
print(f"  최종 후보가 두 반 모두 나은 세계 {win} / {len(rows)}", flush=True)
print("끝", flush=True)
