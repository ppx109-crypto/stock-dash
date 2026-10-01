"""m15guard.py가 부르는 '한 세계' — 환경(HLAB_CUT · HLAB_POISON)에 따라 잘리거나 더럽혀진 15분봉 · 일봉 자료로 같은 규칙들을 돌려
신호 · 매매 목록을 pickle로 남김. 규칙: 15분봉 0회차(1시간봉 최고 규칙을 옮긴 것) · 엿보기 셋(검사 눈 확인용 · 반드시 걸려야 함)."""
import pickle
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import numpy as np
exec(open("/home/user/stock-dash/research/q_rule.py", encoding="utf-8").read())


def peek_buy(c, b):            # 다음 봉 종가가 1% 넘게 오를 봉에서 삼(한 봉 엿보기)
    m = ctx_now(c, b).copy()
    up = np.r_[b["c"][1:] / b["c"][:-1] - 1 > 0.01, False]
    return m & up


def peek_far(c, b):            # 120봉 뒤가 5% 넘게 높을 봉에서 삼(멀리 엿보기)
    m = ctx_now(c, b).copy()
    far = np.r_[b["c"][120:] / b["c"][:-120] - 1 > 0.05, np.zeros(min(120, len(b["c"])), bool)]
    return m & far[:len(m)]


def peek_sell(c, b, p, k):     # 다음 봉이 내리면 미리 팜(한 봉 엿보기)
    if k + 1 < len(b["c"]) and b["c"][k + 1] < b["c"][k]:
        return "all"
    return exit_rule(c, b, p, k)


RULES = {
    "15분봉 0회차(1시간봉 최고 규칙 옮김)": (SIGS, exit_rule, RANK, stale90),
    "엿보기: 다음 봉 보고 사기": ({c: peek_buy(c, b) for c, b in data.items()}, exit_rule, None, None),
    "엿보기: 120봉 뒤 보고 사기": ({c: peek_far(c, b) for c, b in data.items()}, exit_rule, None, None),
    "엿보기: 다음 봉 보고 팔기": (SIGS, peek_sell, RANK, stale90),
}
out = {"rules": {}, "last": max((b["t"][-1] for b in data.values()), default=""), "dates_bad": 0, "dates_seen": 0}
for name, (sig, ex, rk, st) in RULES.items():
    r = H._one_run(data, sig, ex, size, M.EARLY[0], M.LATE[1], 10, 0, None, rk, H.COST, None, None, st)
    trades = [(t["code"], t["산 때"], t["판 때"], t["칸"], t["손익"]) for t in (r or {}).get("목록", [])]
    out["rules"][name] = {"sigs": {c: [data[c]["t"][k] for k in np.flatnonzero(m)] for c, m in sig.items()}, "trades": trades}
for c, b in data.items():                     # 날짜 짚기: 봉에 붙은 일봉 재료의 날 · 수급 마지막 날이 그 봉의 날보다 앞인가
    for t, x in zip(b["t"], ATT[c]):
        if x:
            out["dates_seen"] += 1
            if x["날"] >= t[:8] or (x.get("수급끝") and x["수급끝"] >= t[:8]):
                out["dates_bad"] += 1
pickle.dump(out, open(sys.argv[1], "wb"))
