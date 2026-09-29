"""1시간봉 32회차(탐색 줄) — 시간 손절: N봉 들고도 +X%를 못 가면 판다(새 신호와 상관없이).
29회차 '7봉 · +3% 못 간 매매를 새 신호에 비킴'이 앞 반에서 나았던 까닭이 '자리 바꾸기'인지 '제자리 매매를 일찍 끊기'인지 가름.
판단은 봉 종가(그 봉까지) → 다음 봉 시가. 반익을 이미 한 매매(칸 < 처음칸)는 건드리지 않음.
점검: 바뀐 매매(견줌 목록과 대조) · 반기."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
def exit_time(n, x, only_kind=None):
    def f(c, b, p, k):
        r = exit_daily(c, b, p, k)
        if r: return r
        kind = door(ATT[c][p["i"]]) or "정배열"
        if only_kind and kind != only_kind: return 0
        if p["칸"] == p["처음칸"] and k - p["i"] >= n and (b["c"][k] / p["price"] - 1) * 100 < x:
            return "all"
        return 0
    return f
print("== 1시간봉 32회차 (시간 손절) ==", flush=True)
base = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank)
print(f"  {'지금':22s} " + H.line(base), flush=True)
keyb = {s: {(t["code"], t["산 때"]): t for t in base[s]["목록"] if not t["나눠"]} for s in ("앞", "뒤")}
for kind in (None, "정배열", "추세"):
    for n in (5, 7, 10, 14):
        for x in (0, 3):
            res = H.simulate(data, e_align_or_noon, exit_time(n, x, kind), size, rank=rank)
            chk = []
            for s in ("앞", "뒤"):
                new = {(t["code"], t["산 때"]): t for t in res[s]["목록"] if not t["나눠"]}
                both = [k for k in new if k in keyb[s] and new[k]["판 때"] != keyb[s][k]["판 때"]]
                d = [new[k]["손익"] - keyb[s][k]["손익"] for k in both]
                chk.append(f"{s} 바뀐 {len(d)}건 차이 평균 {np.mean(d) if d else 0:+.2f}%p · 나은 몫 {np.mean([v > 0 for v in d]) * 100 if d else 0:.0f}%")
            tag = f"{kind or '모두'} · {n}봉 · <{x}%"
            print(f"  {tag:22s} " + H.line(res), flush=True)
            print(f"      {' · '.join(chk)} · 반기 앞 {res['앞']['반기']} 뒤 {res['뒤']['반기']}", flush=True)
print("끝", flush=True)
