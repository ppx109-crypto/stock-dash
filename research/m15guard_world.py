"""m15guard.py가 부르는 '한 세계' — 환경(HLAB_CUT · HLAB_POISON)에 따라 잘리거나 더럽혀진 15분봉 · 일봉 자료로 같은 규칙들을 돌려
신호 · 매매 목록을 pickle로 남김. 규칙: 15분봉 0회차(1시간봉 최고 규칙을 옮긴 것) · 엿보기 셋(검사 눈 확인용 · 반드시 걸려야 함)."""
import os
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


import m15feat as F
MK = F.market(data, IN)          # 2026-10-04: 그 봉에 100위 안인 종목만(운영과 같게 · 미래 참조 없앰)


def final_entry(c, b):
    """15분봉 22회차 최종 후보: 정배열 된 봉 또는 10:45 봉 뒤, 단 그날 +2% 위 · 장중 시장 흐름 −1% 아래면 안 삼(그날 처음 한 번).
    재료는 넘겨받은 봉(b)에서 다시 셈 — 봉마다 더럽히기(4b)에서도 그 봉까지 값만 쓰는지 보려고."""
    dr = np.nan_to_num(F.day_ret(b), nan=0.0)
    mk = np.nan_to_num(np.array([MK.get(t, np.nan) for t in b["t"]], float), nan=0.0)
    ok = ~(dr > 0.02) & ~(mk < -0.01)
    hh = M.hhmm(b)
    cand = (e_align(c, b) & ok) | (ctx_now(c, b) & (hh == "1045") & ok)
    m, seen = np.zeros(len(b["t"]), bool), set()
    for k in np.flatnonzero(cand):
        d = b["t"][k][:8]
        if d not in seen:
            m[k] = True
            seen.add(d)
    return m


FINAL = {c: final_entry(c, b) for c, b in data.items()}
RULES = {
    "15분봉 0회차(1시간봉 최고 규칙 옮김)": (SIGS, exit_rule, RANK, stale90),
    "15분봉 22회차 최종 후보": (FINAL, exit_rule, rank_of(tiers(FINAL)), stale90),
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
# 4b 봉마다 더럽히기(잘리지 않은 온 세계에서만): 종목 60개 × 봉 약 24곳마다 그 봉 **뒤만** 엉뚱하게 바꿔,
# 그 봉의 사는 신호 · (그 봉에 들고 있다고 친 매매의) 파는 판단이 그대로인지. 한 봉만 엿보는 규칙도 잡으려고.
if not os.environ.get("HLAB_CUT") and not os.environ.get("HLAB_POISON"):
    import rna
    rng = np.random.default_rng(7)
    ENTRY = {"15분봉 0회차(1시간봉 최고 규칙 옮김)": (e_align_or_noon, exit_rule), "15분봉 22회차 최종 후보": (final_entry, exit_rule),
             "엿보기: 다음 봉 보고 사기": (peek_buy, exit_rule),
             "엿보기: 120봉 뒤 보고 사기": (peek_far, exit_rule), "엿보기: 다음 봉 보고 팔기": (e_align_or_noon, peek_sell)}
    bar = {name: [0, 0] for name in ENTRY}
    codes = sorted(data)
    for c in [codes[i] for i in rng.choice(len(codes), min(60, len(codes)), replace=False)]:
        b = data[c]
        n = len(b["t"])
        on = np.flatnonzero(ctx_now(c, b))
        picks = list(rng.choice(on, min(12, len(on)), replace=False)) if len(on) else []
        picks += list(rng.integers(200, n - 2, 12)) if n > 210 else []
        for k in picks:
            k = int(k)
            bad = {key: (v.copy() if isinstance(v, np.ndarray) else v) for key, v in b.items()}
            walk = b["c"][k] * np.exp(np.cumsum(rng.normal(0, 0.03, n - k - 1)))
            for key in ("o", "h", "l", "c"):
                bad[key][k + 1:] = walk * (1.02 if key == "h" else 0.98 if key == "l" else 1.0)
            bad["v"][k + 1:] = rng.uniform(0.1, 10, n - k - 1) * max(b["v"][:k + 1].mean(), 1)
            p = {"i": max(0, k - 6), "price": b["c"][max(0, k - 6)], "칸": 2, "처음칸": 2, "peak": max(b["c"][max(0, k - 6):k + 1]),
                 "now": k, "code": c}
            for name, (ent, ex) in ENTRY.items():
                H._ST.pop((c, SPAN), None)
                s1 = bool(ent(c, b)[k])
                H._ST.pop((c, SPAN), None)
                s2 = bool(ent(c, bad)[k])
                H._ST.pop((c, SPAN), None)
                d1, d2 = ex(c, b, dict(p), k), ex(c, bad, dict(p), k)
                bar[name][0] += 1
                bar[name][1] += (s1 != s2) + (d1 != d2)
    out["bar_poison"] = bar
pickle.dump(out, open(sys.argv[1], "wb"))
