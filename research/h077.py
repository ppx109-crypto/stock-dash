"""1시간봉 77회차 — 사용자 "같은 기간이 아니어도 연 기준으로": 일봉 최고 규칙(47회차)과 1시간봉 최고 규칙의 해마다 연수익(복리 없는 한 해 몫)을 같은 해끼리 나란히.
인자 'hour' = 1시간봉 쪽(해마다 따로 계좌 · 씨앗 16 가운데) · 'day' = 일봉 쪽(nrl.run years=True의 '해마다')."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
if sys.argv[1] == "hour":
    import hlab as H
    exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
    def e_dil(c, b):
        m = np.asarray(e_align_or_noon(c, b), bool).copy(); n = len(b["t"])
        for k in np.flatnonzero(m):
            x = ATT[c][k + 1] if k + 1 < n else ATT[c][k]
            if x and x["희석20"]: m[k] = False
        return m
    P = (("2023(10~12월)", ("2023100100", "2024010100")), ("2024", ("2024010100", "2025010100")),
         ("2025", ("2025010100", "2026010100")), ("2026(1~9월)", ("2026010100", H.HOLDOUT)))
    print("== 1시간봉 77회차 (해마다 연수익 · 1시간봉) ==", flush=True)
    for tag, e, st in (("일봉 진입(1시간봉 모의 · 다음 날 09시)", e_morning, None), ("1시간봉 최고", e_align_or_noon, stale90), ("1시간봉 최고 + 희석 거르기", e_dil, stale90)):
        res = H.simulate(data, e, make_exit(), size, rank=rank, stale_of=st, seeds=16, periods=P)
        print(f"  {tag:30s} " + " · ".join(f"{k} 연 {r['연']}(골 {r['골']})" if r else f"{k} -" for k, r in res.items()), flush=True)
else:
    import nrl
    print("== 1시간봉 77회차 (해마다 연수익 · 일봉 최고 규칙) ==", flush=True)
    nrl.run("일봉 최고 규칙(47회차)", years=True)
print("끝", flush=True)
