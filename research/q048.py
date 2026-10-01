"""15분봉 최종 시험(OOS) — 사용자 허락 2026-10-02 "15m 9월 oos 개봉해보자". 2026-09-01 ~ 09-30(20거래일)을 처음이자 한 번만 엶(M15_OPEN_OOS=1).
시험 규칙은 22회차 최종 후보(연구 중 고정 · 이 결과로 다시 고치지 않음). 견줌: 15분봉 0회차 · 같은 자료 1시간봉 최고 규칙(Q_BARS=1h로 따로).
씨앗 16 · 비용 0.30%(+ 0.5%). 앞 · 뒤 반도 함께 찍어 같은 엔진인지 확인. 신호 하나하나 평균도(9월)."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash")
assert os.environ.get("M15_OPEN_OOS") == "1", "사용자 허락 뒤 한 번만: M15_OPEN_OOS=1"
if os.environ.get("Q_BARS") == "1h":
    exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())
    print(f"== 15분봉 최종 시험 · 견줌: 같은 자료 1시간봉 최고 규칙 ({len(data)}종목) ==", flush=True)
    for cost in (0.3, 0.5):
        res = M.simulate(data, lambda c, b: SIGS[c], exit_rule, size, rank=RANK, stale_of=stale90, seeds=16, cost=cost)
        print(f"  1시간봉 최고 규칙 · 비용 {cost}% " + H.line(res), flush=True)
    print("끝", flush=True)
    sys.exit()
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('\npart = os.environ')[0])
exec(open("/home/user/stock-dash/research/q019.py", encoding="utf-8").read().split('al_cache = ')[0].split('exec(open(')[0])
exec("def solo" + open("/home/user/stock-dash/research/q019.py", encoding="utf-8").read().split("def solo", 1)[1].split("al_cache = ")[0])
PER = M.periods()
print(f"== 15분봉 최종 시험(2026-09) ({len(data)}종목 · 구간 {[p[0] for p in PER]}) ==", flush=True)
FIN = entry3(al_mkt=-0.01)
for tag, fn in (("15분봉 0회차", entry()), ("15분봉 22회차 최종 후보", FIN)):
    for cost in (0.3, 0.5):
        run3(f"{tag} · 비용 {cost}%", fn, cost=cost)
for tag, fn in (("0회차", entry()), ("최종 후보", FIN)):
    L = []
    for c, b in data.items():
        m = fn(c, b)
        for k in np.flatnonzero(m):
            if b["t"][k] >= "202609010000":
                r = solo(c, k)
                if r is not None:
                    L.append(r)
    if L:
        print(f"  9월 신호 하나하나 · {tag}: 평균 {statistics.mean(L):+.2f}% · 가운데 {statistics.median(L):+.2f} · 이김 {sum(x > 0 for x in L) / len(L) * 100:.0f}% ({len(L)}건)", flush=True)
print("끝", flush=True)
