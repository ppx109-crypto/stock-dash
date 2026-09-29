"""1시간봉 5회차(확인 줄) — 3회차 후보 '1시간봉 A 정배열 된 봉 다음, 그날 없으면 12시 시가'의 고원 · 버팀.
- 그날 없을 때 사는 시각: 11 · 12 · 13 · 14시 시가(신호 봉 10 · 11 · 12 · 13시)
- 정배열 조합: A(5·20·60·120·180봉) · B(5·10·20·60·120·240봉) · 짧은 A(5·20·60봉만 줄 섬)
- 계좌 짜임: 자리 8 · 12칸
파는 법은 일봉 규칙(3회차 기준)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])

def e_combo(set_key="A", fallback="11", short=False):
    def f(c, b):
        s = H.states(c, b, set_key)
        al = (s["배열"] >= 2) if short else (s["정배열"] == 1)
        edge = ctx_now(c, b) & al & ~np.r_[False, al[:-1]]
        nn = ctx_now(c, b) & hour_is(b, fallback)
        days = [t[:8] for t in b["t"]]
        seen = set(); m = np.zeros(len(b["t"]), bool)
        for k in range(len(m)):
            if (edge[k] or nn[k]) and days[k] not in seen:
                m[k] = True; seen.add(days[k])
        return m
    return f

print("== 1시간봉 5회차 (확인: 사는 때 후보의 고원 · 버팀) ==", flush=True)
for tag, e, kw in (("후보: A 정배열, 없으면 12시", e_combo("A", "11"), {}),
                   ("A 정배열, 없으면 11시", e_combo("A", "10"), {}),
                   ("A 정배열, 없으면 13시", e_combo("A", "12"), {}),
                   ("A 정배열, 없으면 14시", e_combo("A", "13"), {}),
                   ("B 정배열, 없으면 12시", e_combo("B", "11"), {}),
                   ("짧은 A(5>20>60봉), 없으면 12시", e_combo("A", "11", short=True), {}),
                   ("아침 시가 · 자리 8", e_morning, {"slots": 8}),
                   ("후보 · 자리 8", e_combo("A", "11"), {"slots": 8}),
                   ("아침 시가 · 자리 12", e_morning, {"slots": 12}),
                   ("후보 · 자리 12", e_combo("A", "11"), {"slots": 12})):
    res = H.simulate(data, e, exit_daily, size, rank=rank, **kw)
    print(f"  {tag:30s} " + H.line(res), flush=True)
print("끝", flush=True)
