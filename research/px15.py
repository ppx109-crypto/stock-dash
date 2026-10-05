"""15분봉 이익확보 · 고점추격 RNA(docs/RL-PX15.md) — 15분봉 22회차(q027) 정배열 매매 팔기에 설계를 얹어 씨앗 16 가운데로 잼.
쓰는 법: python research/px15.py "" LDU "TR10_20" …  · PX15_SHOW_TEST=1이면 뒤 반(시험)도 보임 · 9월은 잠금 · PX15_YAHOO=1이면 1시간봉으로 옮긴 야후 판(2023-10 ~)으로.
설계: LDU · LDL(사다리) · LF{f}_{s}(꼭대기 이익 s% 뒤 그 f% 아래면 팖) · TR{x}_{s} · TB{x}_{s}(꼭대기 이익 s% 뒤 꼭대기보다 x% 빠지면) · PH{x}(처음 +x%에 절반) ·
      끝에 V{p} = 숫자 × (산 봉 앞 60봉 흔들림 ÷ V0)^(p/100) · V0 = 앞 반 신호 봉 흔들림 가운데. 판단은 그 봉 종가 · 꼭대기(그 봉까지) → 다음 봉 시가."""
import os
import re
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
os.chdir("/home/user/stock-dash")
if os.environ.get("PX15_YAHOO") == "1":       # 독립 확인: 15분봇 규칙을 1시간봉으로 옮긴 판(야후 2023-10 ~ · research/m15y.py) · 두 기간 모두 보임
    os.environ["M15Y_SRC"] = "yahoo"
    exec(open("/home/user/stock-dash/research/m15y.py", encoding="utf-8").read().split("res16 = M.simulate(")[0])
    os.environ["PX15_SHOW_TEST"] = "1"
else:
    exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
SHOW = os.environ.get("PX15_SHOW_TEST") == "1"
BASE_EXIT = exit_rule
LADDER = {"LDU": [(10, 3), (15, 5)], "LDL": [(10, 3), (15, 5), (20, 10), (30, 18), (50, 32), (100, 70)]}


def vol_at(c, i):
    x = data[c]["c"][max(0, i - 60):i + 1]
    return float(np.std(np.diff(np.log(x)))) if len(x) > 10 else np.nan


_lo, _hi = M.PERIODS[0][1]
V0 = float(np.nanmedian([vol_at(c, k) for c in SGF for k in np.flatnonzero(SGF[c]) if _lo <= data[c]["t"][k] < _hi]))


def make(px):
    if not px:
        return BASE_EXIT
    mv = re.search(r"V(\d+)$", px)
    pp = int(mv.group(1)) / 100 if mv else 0.0
    body = px[:mv.start()] if mv else px
    m = re.match(r"(LDU|LDL|LF|TR|TB|PH)(\d*)_?(\d*)", body)
    kind, a, b2 = m.group(1), int(m.group(2) or 0), int(m.group(3) or 0)

    def ex(c, b, p, k):
        if (door(ATT[c][p["i"]]) or "정배열") == "정배열":
            now = (b["c"][k] / p["price"] - 1) * 100
            pg = (p["peak"] / p["price"] - 1) * 100
            kk = (vol_at(c, p["i"]) / V0) ** pp if pp else 1.0
            kk = kk if kk == kk else 1.0
            if kind in LADDER:
                if any(pg >= x * kk and now <= y * kk for x, y in LADDER[kind]):
                    return "all"
            elif kind == "LF":
                if pg >= b2 * kk and now <= pg * a / 100:
                    return "all"
            elif kind in ("TR", "TB"):
                if pg >= b2 * kk and b["c"][k] <= p["peak"] * (1 - a * kk / 100):
                    return "all"
            elif kind == "PH" and not p.get("반팜") and now >= a * kk:
                out = BASE_EXIT(c, b, p, k)
                if out:
                    return out
                if p["칸"] >= 2:
                    p["반팜"] = True
                    return max(1, p["칸"] // 2)
        return BASE_EXIT(c, b, p, k)
    return ex


for px in (sys.argv[1:] or [""]):
    res = M.simulate(data, lambda c, b: SGF[c], make(px), size, rank=RKF, stale_of=stale90, seeds=16, cost=H.COST)
    if os.environ.get("PX15_DUMP"):                # 자르기 · 더럽히기 시험용: 씨앗 1 매매 목록
        import json as _js
        r1 = M.simulate(data, lambda c, b: SGF[c], make(px), size, rank=RKF, stale_of=stale90, seeds=1, cost=H.COST)
        _js.dump([(t["code"], t["산 때"], t["판 때"], t["손익"]) for s_ in r1 if r1[s_] for t in r1[s_]["목록"]], open(os.environ["PX15_DUMP"], "w"))
    names = list(res)[:2] if SHOW else list(res)[:1]
    print(f"{px or '바탕':10s} | " + " | ".join(f"{n} 매매 {res[n]['매매']} 연 {res[n]['연']}({res[n]['폭']}) 골 {res[n]['골']} 큰2건뺌 {res[n]['큰2건뺌']}" for n in names if res.get(n)), flush=True)
