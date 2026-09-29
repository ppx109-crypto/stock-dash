"""hguard.py가 부르는 '한 세계' 실행 — 환경(HLAB_CUT · HLAB_POISON)에 따라 잘리거나 더럽혀진 자료로 같은 규칙들을 돌려
신호 · 매매 목록을 pickle로 남김. 규칙: 지금 1시간봉 규칙 · 자리 바꾸기 후보 · 짧은 판 B · 엿보기(일부러 미래를 보는 규칙 = 검사 눈 확인용)."""
import os, sys, pickle
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h021.py", encoding="utf-8").read().split('print("== 1시간봉 21회차')[0])

def stale(n, x):
    return lambda p: (p["now"] - p["i"] >= n) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < x
def e_peek(c, b):          # 일부러 다음 봉 종가를 봄(미래 참조) — 검사가 이것을 잡아야 함
    m = e_align_or_noon(c, b).copy()
    nxt = np.r_[b["c"][1:], b["c"][-1]]
    return m | (ctx_now(c, b) & (nxt > b["c"] * 1.02))
RULES = {
    "지금": dict(entry=e_align_or_noon, exit_rule=exit_daily, size=size, rank=rank),
    "자리 바꾸기": dict(entry=e_align_or_noon, exit_rule=exit_daily, size=size, rank=rank, stale_of=stale(7, 4)),
    "짧은 판 B": dict(entry=entry(), exit_rule=exit_trail, size=four, rank=rank, take_of=take_half, stop_of=stop5),
    "엿보기(검사 눈)": dict(entry=e_peek, exit_rule=exit_daily, size=size, rank=rank),
}
out = {"max_bar": max(b["t"][-1] for b in data.values()), "max_rank_day": max(ranks), "rules": {}, "dates": []}
# 날짜 짚기: 봉마다 붙은 일봉 재료의 날 · 수급 마지막 날이 그 봉의 날보다 앞인가
bad = 0
for c in data:
    for k in range(0, len(data[c]["t"]), 7):
        x = ATT[c][k]; day = data[c]["t"][k][:8]
        if x and (x["날"] >= day or (x["수급끝"] and x["수급끝"] >= day)):
            bad += 1
            if len(out["dates"]) < 5: out["dates"].append((c, data[c]["t"][k], x["날"], x["수급끝"]))
out["dates_bad"] = bad
for name, kw in RULES.items():
    e = kw.pop("entry")
    sigs = {c: [t for t, v in zip(b["t"], np.asarray(e(c, b), bool)) if v] for c, b in data.items()}
    res = H.simulate(data, e, periods=(("전체", ("2023100100", H.HOLDOUT)),), seeds=1, **kw)
    L = res["전체"]["목록"] if res["전체"] else []
    out["rules"][name] = {"sigs": sigs, "trades": [(t["code"], t["산 때"], t["판 때"], t["칸"], t["손익"]) for t in L]}
pickle.dump(out, open(sys.argv[1], "wb"))
print("세계 끝", os.environ.get("HLAB_CUT"), os.environ.get("HLAB_POISON"), {k: len(v["trades"]) for k, v in out["rules"].items()}, flush=True)
