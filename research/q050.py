"""15분봉 47회차(세 갈래 공통 실험 · 15분봉) — 후보 문의 수급 조건을 바꾼 판(research/flowvar.py). 기준 = 22회차 후보(보류 중이지만 15분봉 갈래의 최고). 161종목 · 씨앗 16 · 두 반."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
exec(open("/home/user/stock-dash/research/q023.py", encoding="utf-8").read().split('\npart = os.environ')[0])
import flowvar as FV


def entry_k(kind):
    def f(c, b):
        ctx = np.array([bool(x) and door(x) is not None and FV.teach(c, x["날"], kind) for x in ATT[c]]) & IN[c]
        s = H.states(c, b, SPAN)["정배열"] == 1
        al = ctx & s & ~np.r_[False, s[:-1]]
        dr, mk = nan0(DR[c]), nan0(MKT[c])
        good = ~(dr > 0.02) & ~(mk < -0.01)
        nn = ctx & (HH[c] == "1045") & good
        al &= good
        m, seen = np.zeros(len(al), bool), set()
        for k in np.flatnonzero(al | nn):
            if DAY[c][k] not in seen:
                m[k] = True
                seen.add(DAY[c][k])
        return m
    return f


names = list(FV.KINDS)
pick = names[:3] if os.environ.get("Q_PART", "1") == "1" else names[3:]
print(f"== 15분봉 47회차: 수급 조건 바꾼 판 ({os.environ.get('Q_PART', '1')}) ==", flush=True)
for k in pick:
    run3(k, entry_k(k))
print("끝", flush=True)
