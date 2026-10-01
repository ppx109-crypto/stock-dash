"""15분봉 1회차 — 사는 때(0회차: 15분 EMA 정배열 된 봉 다음 시가, 없으면 11:45 봉 뒤 12:00).
바꿔 보는 것(docs/DATA-AUDIT-15M.md 4절 ②): 장 시작 직후 신호 거르기 · 정오 대신 다른 마감 시각 · 장중 재료로 거르기
(같은 시각 거래량 배수 · 오늘 평균값 위 · 시가 갭 · 161종목 장중 시장 흐름 — m15feat, 신호 봉이 닫힌 때까지 값만).
같은 시각 후보 순서는 판마다 그 판의 신호로 다시 셈. 씨앗 16 · 두 반 · 비용 0.30%(연구값).
실행: python3 research/q002.py   (M15_HOME으로 다른 자료 폴더)
"""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
import m15feat as F

HH = {c: M.hhmm(b) for c, b in data.items()}
DAY = {c: np.array([t[:8] for t in b["t"]]) for c, b in data.items()}
RV = {c: F.relvol(b) for c, b in data.items()}
VW = {c: F.vwap_dev(b) for c, b in data.items()}
GP = {c: F.gap(b) for c, b in data.items()}
MK = F.market(data)
MKT = {c: np.array([MK.get(t, np.nan) for t in b["t"]]) for c, b in data.items()}
SLOTS = [f"{9 + m // 60:02d}{m % 60:02d}" for m in range(0, 26 * 15, 15)]


def entry(skip=0, noon=NOON, cond=None):
    """그날 처음 한 번: (정배열 된 봉 · 첫 skip칸 뺌 · cond 참) 또는 noon 봉(noon=None이면 정오 사기 없음)."""
    def f(c, b):
        al = e_align(c, b)
        if skip:
            al &= ~np.isin(HH[c], SLOTS[:skip])
        if cond is not None:
            al &= cond(c)
        nn = ctx_now(c, b) & (HH[c] == noon) if noon else np.zeros(len(al), bool)
        m, seen = np.zeros(len(al), bool), set()
        for k in np.flatnonzero(al | nn):
            if DAY[c][k] not in seen:
                m[k] = True
                seen.add(DAY[c][k])
        return m
    return f


def run(tag, fn, cost=H.COST):
    sigs = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    rk = rank_of(tiers(sigs))
    res = M.simulate(data, lambda c, b: sigs[c], exit_rule, size, rank=rk, stale_of=stale90, seeds=16, cost=cost)
    print(f"  {tag:34s} 신호 {sum(int(v.sum()) for v in sigs.values()):5d} " + H.line(res), flush=True)
    return res


nan_ok = lambda v, test: np.where(np.isnan(v), False, test(np.nan_to_num(v)))
print("== 15분봉 1회차: 사는 때 (보유는 15분봉 수 — 4로 나누면 시간) ==", flush=True)
run("0회차 그대로", entry())
for s in (1, 2, 4):
    run(f"장 시작 {s * 15}분 신호 거르기", entry(skip=s))
for nn in ("1045", "1245", "1345", None):
    run(f"정오 대신 {'없음' if nn is None else nn + ' 봉 뒤'}", entry(noon=nn))
run("거래량 배수 ≥ 1.5", entry(cond=lambda c: nan_ok(RV[c], lambda v: v >= 1.5)))
run("거래량 배수 ≥ 1.0", entry(cond=lambda c: nan_ok(RV[c], lambda v: v >= 1.0)))
run("오늘 평균값 위", entry(cond=lambda c: nan_ok(VW[c], lambda v: v > 0)))
run("시가 갭 +3% 미만", entry(cond=lambda c: ~nan_ok(GP[c], lambda v: v >= 0.03)))
run("장중 시장 흐름 −0.5% 위", entry(cond=lambda c: ~nan_ok(MKT[c], lambda v: v <= -0.005)))
print("끝", flush=True)
