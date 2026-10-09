# 진단(공개): 흔들림 창 첫날 값이 없어 σ를 건너뛴(상한 없음 = 100%) 날 수 — z087(1일봉 단독 ×2, 씨앗 8 · 두 반)
import sys, bisect, math
sys.path.insert(0, "/home/user/stock-dash"); sys.path.insert(0, "/home/user/stock-dash/research")
import z081, z087, nrl
CAL = z087.CAL
for which in ("앞", "뒤"):
    tot_days = skip_first = skip_any = 0
    for g in z081.ledgers(which, z081.holds_b0):
        _, navs = z087.account(g["led"], g["still"], g["since"], g["end"], want_navs=True)
        # 보유 종목 날짜 목록을 매매 줄에서 다시 만듦(산 날 다음 날 ~ 판 날)
        held = {}
        for t in g["led"] + [dict(x, **{"판 날": g["end"]}) for x in g["still"]]:
            i0, i1 = bisect.bisect_right(CAL, t["산 날"]), bisect.bisect_right(CAL, t["판 날"])
            for d in CAL[i0:i1]:
                held.setdefault(d, set()).add(t["code"])
        for d, codes in held.items():
            ci = bisect.bisect_left(CAL, d); win = CAL[ci - 21:ci]
            if len(win) < 21: continue
            tot_days += 1
            first_missing = any(win[0] not in dict.fromkeys(nrl.lanes[c]["날"]) for c in codes)
            skip_first += first_missing
    print(f"[{which}] 보유 있는 날(씨앗 합) {tot_days} · 창 첫날 값 없음으로 σ 건너뛸 수 있던 날 {skip_first}({skip_first / max(tot_days, 1) * 100:.2f}%)", flush=True)
