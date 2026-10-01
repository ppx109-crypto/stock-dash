"""1시간봉 106회차(세 갈래 공통 실험 · 1시간봉) — 후보 문의 수급 조건을 바꾼 판(research/flowvar.py). 기준 = 94회차. 야후 1시간봉 2023-10 ~ 2026-09 · 씨앗 16."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
import flowvar as FV


def entry_k(kind):
    def f(c, b):
        ctx = np.array([bool(x) and door(x) is not None and FV.teach(c, x["날"], kind) for x in ATT[c]]) & IN[c]
        s = H.states(c, b, "A")["정배열"] == 1
        al = ctx & s & ~np.r_[False, s[:-1]]
        nn = ctx & hour_is(b, "11")
        days = [t[:8] for t in b["t"]]
        seen, m = set(), np.zeros(len(b["t"]), bool)
        for k in np.flatnonzero(al | nn):
            if days[k] not in seen:
                m[k] = True
                seen.add(days[k])
        return m
    return f


names = list(FV.KINDS)
pick = names[:3] if os.environ.get("Q_PART", "1") == "1" else names[3:]
print(f"== 1시간봉 106회차: 수급 조건 바꾼 판 ({os.environ.get('Q_PART', '1')}) ==", flush=True)
for k in pick:
    run(k, entry_k(k))
print("끝", flush=True)
